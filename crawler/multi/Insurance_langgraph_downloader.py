#!/usr/bin/env python3
"""
자가 치유(Self-Healing) 보험 약관 PDF 다운로더 어플리케이션
(LangGraph + LangChain TavilySearch + 선택적 LLM 진단 + Playwright + Requests)

핵심 자가 치유 루프:
  collect(수집) -> verify(검증) -> [실패/0건 시] heal(진단·복구) -> collect(재시도) -> next
- 치유 전략:
  1) 브라우저 세션/페이지 상태 리셋 및 공시실 메인 경유 복구
  2) TavilySearch(TAVILY_API_KEY)로 최신 공시실/판매중지 URL 동적 재탐색
  3) LLM(OPENAI_API_KEY 또는 GOOGLE_API_KEY, 선택) + 범용 DOM 휴리스틱으로 약관 링크/메뉴 자동 탐색
- 치유 이력은 <output>/healing_report.json 에 기록됩니다.
"""
# 실행문장
# cd /data/vm_project/crawler/multi
# /data/vm_project/venv/bin/python Insurance_langgraph_downloader.py --target samsungfire,db --output ./output --limit 3 --max-heal 2 --use-tavily
from __future__ import annotations

import argparse
import json
import os
import re
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Literal, TypedDict
from urllib.parse import quote, urljoin

import requests
from langchain_tavily import TavilySearch
from self_healer import SelfHealer
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph
from playwright.sync_api import Browser, BrowserContext, Page, Playwright, Route, sync_playwright

EXCLUDE_KEYWORDS = ("사업방법서", "사용방법서", "상품요약서", "요약서", "핵심설명서", "상품설명서", "기초서류")
REQUEST_DELAY_SEC = 1.0


@dataclass(frozen=True)
class InsurerMeta:
    """보험사 식별자, 한글명, 도메인 및 공시실 기본/판매중지 URL 메타데이터."""
    insurer_id: str
    name: str
    domain: str
    sale_url: str
    stop_url: str | None = None


INSURER_REGISTRY: dict[str, InsurerMeta] = {
    "meritz": InsurerMeta(
        insurer_id="meritz",
        name="메리츠화재",
        domain="meritzfire.com",
        sale_url="https://www.meritzfire.com/disclosure/product-announcement/product-list.do#!/",
        stop_url="https://www.meritzfire.com/disclosure/product-announcement/product-list.do#!/02",
    ),
    "kb": InsurerMeta(
        insurer_id="kb",
        name="KB손해보험",
        domain="kbinsure.co.kr",
        sale_url="https://www.kbinsure.co.kr/CG802030001.ec",
    ),
    "aia": InsurerMeta(
        insurer_id="aia",
        name="AIA생명",
        domain="aia.co.kr",
        sale_url="https://mypage.aia.co.kr/AIAHomepage/disclosure/our-products/selling/individual.do",
        stop_url="https://mypage.aia.co.kr/AIAHomepage/disclosure/our-products/stop-selling/individual.do",
    ),
    "axa": InsurerMeta(
        insurer_id="axa",
        name="AXA손해보험",
        domain="axa.co.kr",
        sale_url="https://www.axa.co.kr/AsianPlatformInternet/html/axacms/common/intro/disclosure/insurance/index.html",
        stop_url="https://www.axa.co.kr/AsianPlatformInternet/html/axacms/common/intro/disclosure/insurance/stopsale/index.html",
    ),
    "samsunglife": InsurerMeta(
        insurer_id="samsunglife",
        name="삼성생명",
        domain="samsunglife.com",
        sale_url="https://www.samsunglife.com/individual/products/disclosure/sales/PDO-PRPRI010110M",
    ),
    "samsungfire": InsurerMeta(
        insurer_id="samsungfire",
        name="삼성화재",
        domain="samsungfire.com",
        sale_url="https://www.samsungfire.com/vh/page/VH.HPIF0103.do",
    ),
    "db": InsurerMeta(
        insurer_id="db",
        name="DB손해보험",
        domain="idbins.com",
        sale_url="https://www.idbins.com/FWMAIV1534.do",
    ),
}

ALL_TARGETS = list(INSURER_REGISTRY.keys())


class AppState(TypedDict):
    """LangGraph 보험 약관 수집·자가치유 파이프라인의 전체 상태 정의."""
    targets: list[str]
    target_idx: int
    output_dir: str
    limit: int
    download: bool
    headless: bool
    use_tavily: bool
    max_heal: int

    # 현재 보험사 실행/치유 상태
    attempt: int
    last_items: list[dict[str, Any]]
    last_error: str
    override_urls: dict[str, list[str]]
    click_hints: dict[str, list[str]]
    healing_log: list[dict[str, Any]]
    summary: dict[str, int]
    blocked: bool


class UnifiedSessionHolder:
    """Playwright 브라우저 세션 관리 (장애 시 restart()로 자가 복구)."""

    def __init__(self) -> None:
        self.pw: Playwright | None = None
        self.browser: Browser | None = None
        self.context: BrowserContext | None = None
        self.page: Page | None = None
        self.captured_url: str | None = None
        self.captured_download_path: Path | None = None

    def start(self, headless: bool) -> Page:
        """Playwright Chromium 세션을 시작하고 PDF 요청/응답/팝업/다운로드 감청기를 부착."""
        tmp_root = Path(__file__).resolve().parent / ".tmp"
        tmp_root.mkdir(parents=True, exist_ok=True)
        for env_k in ("TMPDIR", "TEMP", "TMP"):
            os.environ[env_k] = str(tmp_root)

        self.pw = sync_playwright().start()
        self.browser = self.pw.chromium.launch(
            headless=headless,
            args=["--disable-blink-features=AutomationControlled"],
        )
        self.context = self.browser.new_context(
            accept_downloads=True,
            locale="ko-KR",
            viewport={"width": 1280, "height": 800},
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
            ),
        )
        self.context.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined});")
        self.page = self.context.new_page()

        def handle_route(route: Route) -> None:
            # 메리츠 GET 다운로드 가로채기 및 삼성/DB PDF 요청 URL 캡처
            req = route.request
            if "/hp/fileDownload.do" in req.url:
                if req.method == "GET":
                    self.captured_url = req.url
                    route.abort()
                    return
                if req.method == "POST" and req.post_data and "path=" in req.post_data:
                    qs = re.sub(r"(^|&)check=Y(&|$)", r"\1check=N\2", req.post_data)
                    if not self.captured_url:
                        self.captured_url = f"https://www.meritzfire.com/hp/fileDownload.do?{qs}"
            elif any(d in req.url for d in ("samsunglife.com", "samsungfire.com", "idbins.com")) and (
                ".pdf" in req.url.lower() or "download" in req.url.lower() or "filedown" in req.url.lower()
            ):
                self.captured_url = req.url
            route.continue_()

        self.page.route("**/*", handle_route)

        def on_response(resp):
            try:
                ct = (resp.headers.get("content-type") or "").lower()
                cd = (resp.headers.get("content-disposition") or "").lower()
                if "application/pdf" in ct or ".pdf" in cd or ".pdf" in resp.url.lower():
                    self.captured_url = resp.url
            except Exception:
                pass

        self.page.on("response", on_response)

        def on_popup(popup):
            try:
                popup.wait_for_load_state("domcontentloaded", timeout=10000)
                if ".pdf" in popup.url.lower() or "pdf" in popup.url.lower() or "file" in popup.url.lower():
                    self.captured_url = popup.url
                popup.on("response", on_response)
            except Exception:
                pass

        self.context.on("page", on_popup)

        def on_download(dl):
            try:
                self.captured_url = dl.url
                tmp = tmp_root / f"hl_dl_{time.time_ns()}.pdf"
                dl.save_as(str(tmp))
                self.captured_download_path = tmp
            except Exception:
                pass

        self.page.on("download", on_download)
        return self.page

    def restart(self, headless: bool) -> Page:
        """브라우저 세션 장애 시 기존 리소스를 정리하고 새 세션을 시작."""
        self.close()
        return self.start(headless)

    def make_requests_session(self, referer: str) -> requests.Session:
        """현재 Playwright 브라우저의 쿠키와 User-Agent를 승계한 requests.Session 생성."""
        assert self.page is not None
        sess = requests.Session()
        sess.headers.update(
            {
                "User-Agent": self.page.evaluate("() => navigator.userAgent"),
                "Referer": referer,
            }
        )
        for c in self.page.context.cookies():
            sess.cookies.set(c["name"], c["value"], domain=c.get("domain", ""))
        return sess

    def snapshot_dom(self) -> dict[str, Any]:
        """자가 치유 진단용으로 현재 페이지의 URL, iframe 목록, 주요 컨트롤 텍스트를 추출."""
        if not self.page:
            return {}
        try:
            return self.page.evaluate(
                """() => ({
                    url: location.href,
                    title: document.title,
                    tables: document.querySelectorAll('table tbody tr').length,
                    iframes: Array.from(document.querySelectorAll('iframe')).map(f => f.src).filter(Boolean),
                    html_controls: Array.from((document.querySelector('main, #contents, #content, .contents') || document.body).querySelectorAll('a, button, input, select'))
                        .filter(e => e.offsetParent !== null)
                        .map(e => e.outerHTML.replace(/\s+/g, ' ').slice(0, 120))
                        .filter(h => /약관|보험|검색|조회|공시|판매|select/i.test(h))
                        .slice(0, 25)
                })"""
            )
        except Exception:
            return {}

    def close(self) -> None:
        """브라우저 및 Playwright 인스턴스를 안전하게 종료."""
        try:
            if self.browser:
                self.browser.close()
        except Exception:
            pass
        try:
            if self.pw:
                self.pw.stop()
        except Exception:
            pass
        self.browser = None
        self.pw = None
        self.page = None


def clean_filename(name: str) -> str:
    """파일명에 사용할 수 없는 특수문자를 치환하고 길이를 80자로 제한."""
    cleaned = re.sub(r'[\\/:*?"<>|\r\n]+', "_", name)
    return re.sub(r"\s+", " ", cleaned).strip()[:80]


def is_excluded(text: str) -> bool:
    """사업방법서, 상품요약서 등 약관 외 제외 대상 문서 여부를 판별."""
    return any(kw in text for kw in EXCLUDE_KEYWORDS)


def stream_pdf(session: requests.Session, url: str, save_path: Path) -> tuple[bool, int, int]:
    """PDF 시그니처(%PDF)를 검증하면서 스트리밍으로 임시 파일(.part) 저장 후 원자적 교체."""
    with session.get(url, stream=True, timeout=60) as resp:
        status = resp.status_code
        if status != 200:
            return False, status, 0
        tmp_path = save_path.with_suffix(".pdf.part")
        size = 0
        with open(tmp_path, "wb") as f:
            for chunk in resp.iter_content(chunk_size=65536):
                if not chunk:
                    continue
                if size == 0 and chunk[:4] != b"%PDF":
                    f.close()
                    tmp_path.unlink(missing_ok=True)
                    return False, status, 0
                f.write(chunk)
                size += len(chunk)
        if size == 0:
            tmp_path.unlink(missing_ok=True)
            return False, status, 0
        tmp_path.replace(save_path)
        return True, status, size


def tavily_find_urls(meta: InsurerMeta) -> list[str]:
    """TavilySearch로 대상 보험사 도메인 내 최신 공시실/판매중지 URL 후보를 탐색."""
    if not os.getenv("TAVILY_API_KEY"):
        return []
    tool = TavilySearch(max_results=5, topic="general", include_domains=[meta.domain])
    try:
        res = tool.invoke({"query": f"{meta.name} 상품공시실 보험약관 판매중지상품"})
        raw_results = res.get("results", []) if isinstance(res, dict) else []
        urls = [r["url"] for r in raw_results if isinstance(r, dict) and r.get("url")]
        if urls:
            print(f"[Heal:TavilySearch:{meta.insurer_id}] 후보 URL {len(urls)}건 확보")
        return urls
    except Exception as e:
        print(f"[Heal:TavilySearch:{meta.insurer_id}] 검색 생략: {e}")
        return []


# ---------------------------------------------------------------------------
# 단일 범용 자율 수집·자가 치유 크롤러 (보험사별 분기 없이 범용 규칙 + SelfHealer로 해결)
# ---------------------------------------------------------------------------
def run_generic_healing_crawl(
    holder: UnifiedSessionHolder,
    meta: InsurerMeta,
    out_base: Path,
    limit: int,
    download: bool,
    extra_urls: list[str],
    click_hints: list[str],
) -> list[dict[str, Any]]:
    """다단계 메뉴(#depth1->#depth2->#depth3) + 판매중지 탭 + LLM/휴리스틱 힌트를 자율 순회하는 범용 탐색기."""
    assert holder.page is not None
    page = holder.page
    out_dir = out_base / meta.insurer_id
    pdf_dir = out_dir / "pdfs"
    pdf_dir.mkdir(parents=True, exist_ok=True)

    base_urls = [u for u in (meta.sale_url, meta.stop_url) if u]
    candidate_urls = list(dict.fromkeys(base_urls + extra_urls[:2]))
    results: list[dict[str, Any]] = []
    seen: set[str] = set()

    def collect_current_page(sess: requests.Session, status_label: str) -> None:
        btns = []
        for fr in page.frames:
            try:
                f_btns = fr.evaluate(
                    """() => Array.from(document.querySelectorAll('a, button')).map((el, idx) => ({el, idx})).filter(({el}) => el.offsetParent !== null && !el.disabled).map(({el, idx}) => {
                        const td = el.closest('td');
                        const tr = el.closest('tr');
                        const tbl = el.closest('table');
                        let colHdr = '';
                        if (td && tr && tbl) {
                            const ci = Array.from(tr.children).indexOf(td);
                            const ths = tbl.querySelectorAll('thead tr:last-child th, thead th');
                            if (ci >= 0 && ths[ci]) colHdr = (ths[ci].textContent || '').replace(/\s+/g, ' ').trim();
                        }
                        return {
                            idx,
                            text: (el.textContent || el.getAttribute('title') || el.querySelector('img')?.getAttribute('alt') || '').replace(/\s+/g, ' ').trim(),
                            ctx: ((el.closest('td, th, dd, li')?.textContent || '') + ' ' + colHdr).replace(/\s+/g, ' ').trim().slice(0, 80),
                            href: el.getAttribute('href') || '',
                            onclick: el.getAttribute('onclick') || ''
                        };
                    }).filter(x => (x.text.includes('약관') || (x.ctx.includes('약관') && /다운|PDF|보기|열기|파일/i.test(x.text + x.onclick + x.href)) || x.href.toLowerCase().includes('.pdf') || x.onclick.toLowerCase().includes('down') || x.onclick.toLowerCase().includes('pdf'))
                        && !/위치기반|회원가입|이용약관|계약관리|약관찾기|공시실\(약관\)|확인하고 싶어요|사업방법서|상품요약서|상품설명서|acrobat|reader|뷰어|설치/i.test(x.text))"""
                )
                btns.extend([(fr, b) for b in f_btns])
            except Exception:
                pass

        for fr, b in btns:
            if limit > 0 and len(results) >= limit:
                return
            seq = len(results) + 1
            fname = f"{seq:03d}_{clean_filename(b['text'] or f'{meta.insurer_id}_{seq}')}_약관.pdf"
            save_path = pdf_dir / fname
            if download and save_path.exists() and save_path.stat().st_size > 1000:
                results.append({"insurerId": meta.insurer_id, "saleStatus": status_label, "productName": b["text"], "pdfUrl": "cached", "localPath": str(save_path), "bytes": save_path.stat().st_size})
                continue

            dl_url = b["href"] if ".pdf" in b["href"].lower() else ""
            holder.captured_download_path = None
            if not dl_url:
                holder.captured_url = None
                try:
                    fr.locator("a, button").nth(b["idx"]).click(force=True, timeout=5000)
                    for _ in range(16):
                        if holder.captured_url or holder.captured_download_path:
                            break
                        page.wait_for_timeout(250)
                    for extra_p in page.context.pages[1:]:
                        try:
                            extra_p.close()
                        except Exception:
                            pass
                except Exception:
                    pass
                dl_url = holder.captured_url or ""

            if holder.captured_download_path and holder.captured_download_path.exists():
                dl_bytes = holder.captured_download_path.read_bytes()
                if dl_bytes[:4] == b"%PDF":
                    save_path.write_bytes(dl_bytes)
                    holder.captured_download_path.unlink(missing_ok=True)
                    item = {"insurerId": meta.insurer_id, "saleStatus": status_label, "productName": b["text"], "pdfUrl": dl_url or "browser_download", "localPath": str(save_path), "bytes": len(dl_bytes)}
                    print(f"  [{meta.insurer_id}:{status_label}] ({seq}) 저장: {fname} ({len(dl_bytes):,} bytes)")
                    results.append(item)
                    continue
                holder.captured_download_path.unlink(missing_ok=True)

            if dl_url and not dl_url.startswith("http"):
                dl_url = urljoin(f"https://www.{meta.domain}", dl_url)
            if not dl_url or dl_url in seen:
                continue
            seen.add(dl_url)

            item: dict[str, Any] = {"insurerId": meta.insurer_id, "saleStatus": status_label, "productName": b["text"], "pdfUrl": dl_url}
            if download:
                ok, _status, size = stream_pdf(sess, dl_url, save_path)
                if ok:
                    item["localPath"] = str(save_path)
                    item["bytes"] = size
                    print(f"  [{meta.insurer_id}:{status_label}] ({seq}) 저장: {fname} ({size:,} bytes)")
                time.sleep(REQUEST_DELAY_SEC)
            results.append(item)

    for entry_url in candidate_urls:
        try:
            page.goto(entry_url, wait_until="domcontentloaded", timeout=30000)
            page.wait_for_timeout(2000)
            # '전체' 선택 셀렉트가 있으면 자동 선택 후 조회
            sel = page.locator("select:visible").first
            if sel.count() > 0 and sel.locator("option", has_text="전체").count() > 0:
                try:
                    sel.select_option(label="전체")
                    page.wait_for_timeout(1000)
                except Exception:
                    pass
        except Exception:
            continue

        sess = holder.make_requests_session(entry_url)

        # 1) LLM/외부 힌트 먼저 클릭 시도
        for hint in click_hints:
            if limit > 0 and len(results) >= limit:
                break
            if hint.startswith("JS:"):
                try:
                    page.evaluate(hint[3:])
                    page.wait_for_timeout(1500)
                    collect_current_page(sess, "판매중")
                except Exception:
                    pass
            else:
                loc = page.locator("a:visible, button:visible").filter(has_text=hint)
                if loc.count() > 0:
                    try:
                        loc.first.click()
                        page.wait_for_timeout(1500)
                        collect_current_page(sess, "판매중")
                    except Exception:
                        pass

        # 2) 판매중 / 판매중지 탭 및 #depth1 -> #depth2 -> #depth3 다단계 메뉴 자율 탐색
        tabs = [("판매중", "판매상품"), ("판매중지", "판매중지")]
        for status_label, tab_kw in tabs:
            tab_loc = page.locator("a:visible, button:visible").filter(has_text=tab_kw)
            if status_label == "판매중지" and tab_loc.count() > 0:
                try:
                    tab_loc.first.click()
                    page.wait_for_timeout(1500)
                except Exception:
                    pass

            collect_current_page(sess, status_label)
            if limit > 0 and len(results) >= limit:
                break

            # #depth1 이후 #depth2~3 또는 #product_gubun -> #product_list -> #date_list 같은 다단 td 리스트 순회
            d1_sel = "#depth1 a:visible" if page.locator("#depth1 a:visible").count() > 0 else ".step.s1 a:visible"
            d1_cnt = min(page.locator(d1_sel).count(), 3)
            for d1 in range(d1_cnt):
                try:
                    el1 = page.locator(d1_sel).nth(d1)
                    print(f"  [탐색:{meta.insurer_id}] 1단계 클릭: {(el1.inner_text() or '').strip()}")
                    el1.click()
                    page.wait_for_timeout(1200)
                    d2_sel = next((s for s in ("#depth2 a:visible", "#product_gubun a:visible", ".step.s2 a:visible", ".step.s2 button:visible") if page.locator(s).count() > 0), "")
                    if not d2_sel:
                        collect_current_page(sess, status_label)
                        continue
                    d2_cnt = min(page.locator(d2_sel).count(), 2) if d2_sel else 0
                    for d2 in range(d2_cnt):
                        page.locator(d2_sel).nth(d2).click()
                        page.wait_for_timeout(1200)
                        d3_sel = next((s for s in ("#depth3 a:visible", "#product_list a:visible", ".step.s3 a:visible", ".step.s3 button:visible") if page.locator(s).count() > 0), "")
                        if not d3_sel:
                            collect_current_page(sess, status_label)
                            continue
                        d3_cnt = min(page.locator(d3_sel).count(), 3) if d3_sel else 0
                        for d3 in range(d3_cnt):
                            page.locator(d3_sel).nth(d3).click()
                            page.wait_for_timeout(1000)
                            if page.locator("#date_list a:visible").count() > 0:
                                page.locator("#date_list a:visible").first.click()
                                page.wait_for_timeout(1000)
                            collect_current_page(sess, status_label)
                            if limit > 0 and len(results) >= limit:
                                break
                        if limit > 0 and len(results) >= limit:
                            break
                except Exception:
                    pass
                if limit > 0 and len(results) >= limit:
                    break

            # #depth1이 없는 사이트는 범용 상품군 카테고리(개인용/업무용/자동차/장기/일반보험) -> 상품명 순으로 자율 탐색
            if not results:
                for cat_kw in ("개인용", "업무용", "자동차보험", "장기보험", "일반보험", "대면", "건강"):
                    if limit > 0 and len(results) >= limit:
                        break
                    cat_loc = page.locator("a:visible, button:visible").filter(has_text=re.compile(rf"^{cat_kw}$"))
                    if cat_loc.count() == 0:
                        continue
                    try:
                        cat_loc.first.click()
                        page.wait_for_timeout(1200)
                        collect_current_page(sess, status_label)
                        if limit > 0 and len(results) >= limit:
                            break
                        prod_loc = page.locator("a:visible, button:visible").filter(has_text=re.compile(r"보험|플랜|종합"))
                        for pi in range(min(prod_loc.count(), 5)):
                            if limit > 0 and len(results) >= limit:
                                break
                            try:
                                prod_loc.nth(pi).click()
                                page.wait_for_timeout(1000)
                                # Step3(판매기간) 버튼이 있는 UI면 첫 기간 항목까지 클릭 후 수집
                                period_loc = page.locator("a:visible, button:visible, li:visible").filter(has_text=re.compile(r"\d{4}\.\d{2}|~"))
                                if period_loc.count() > 0:
                                    try:
                                        period_loc.first.click()
                                        page.wait_for_timeout(800)
                                    except Exception:
                                        pass
                                collect_current_page(sess, status_label)
                            except Exception:
                                continue
                    except Exception:
                        continue
                if limit > 0 and len(results) >= limit:
                    break

        if results:
            break

    (out_dir / "terms.json").write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    return results


RunnerFn = Callable[[UnifiedSessionHolder, Path, int, bool, list[str], list[str]], list[dict[str, Any]]]
RUNNERS: dict[str, RunnerFn] = {k: (lambda m: (lambda h, o, l, d, e, c: run_generic_healing_crawl(h, m, o, l, d, e, c)))(v) for k, v in INSURER_REGISTRY.items()}


# ---------------------------------------------------------------------------
# Self-Healing LangGraph StateGraph (collect -> verify -> heal -> retry)
# ---------------------------------------------------------------------------
def build_self_healing_graph(holder: UnifiedSessionHolder):
    """수집(collect) -> 치유(heal) -> 다음 대상(advance) -> 요약(finalize) 상태 그래프 구성."""
    def init_node(state: AppState) -> dict[str, Any]:
        """브라우저를 시작하고 옵션에 따라 Tavily 사전 URL 탐색을 수행."""
        holder.start(headless=state["headless"])
        override_urls: dict[str, list[str]] = {}
        if state["use_tavily"]:
            for t in state["targets"]:
                override_urls[t] = tavily_find_urls(INSURER_REGISTRY[t])
        return {"target_idx": 0, "attempt": 0, "override_urls": override_urls, "click_hints": {}, "healing_log": [], "summary": {}}

    def collect_node(state: AppState) -> dict[str, Any]:
        """현재 대상 보험사의 전용 어댑터 또는 범용 탐색기를 실행해 약관 수집."""
        insurer_id = state["targets"][state["target_idx"]]
        meta = INSURER_REGISTRY[insurer_id]
        extra = state["override_urls"].get(insurer_id, [])
        hints = state["click_hints"].get(insurer_id, [])
        print(f"\n[{insurer_id}] 수집 실행 (시도 {state['attempt'] + 1}/{state['max_heal'] + 1})")

        try:
            if state["attempt"] == 0:
                items = RUNNERS[insurer_id](holder, Path(state["output_dir"]), state["limit"], state["download"], extra, hints)
            else:
                # SelfHealer가 디스크의 본 소스를 자동 패치한 경우 최신 모듈을 동적 재로드해 반영
                active_runners = RUNNERS
                if any("소스 자동 패치 저장 완료" in str(a) for log_e in state["healing_log"] for a in log_e.get("actions", [])):
                    mod = SelfHealer.reload_module(__file__, "_healed_downloader")
                    if mod is not None:
                        active_runners = getattr(mod, "RUNNERS", RUNNERS)
                # 단일 범용 수집기(active_runners) 1회 실행으로 중복 탐색 방지
                items = active_runners[insurer_id](holder, Path(state["output_dir"]), state["limit"], state["download"], extra, hints)
            return {"last_items": items, "last_error": ""}
        except Exception as e:
            msg = str(e)
            if "차단" in msg:
                return {"blocked": True, "last_error": msg, "last_items": []}
            return {"last_items": [], "last_error": msg}

    def heal_node(state: AppState) -> dict[str, Any]:
        """수집 실패 또는 0건 시 DOM 스냅샷과 SelfHealer로 원인 진단 후 URL/클릭 힌트 보강."""
        insurer_id = state["targets"][state["target_idx"]]
        meta = INSURER_REGISTRY[insurer_id]
        next_attempt = state["attempt"] + 1
        print(f"[Self-Heal:{insurer_id}] self_healer 모듈로 복구 중 (치유 #{next_attempt})")

        if holder.page and meta.sale_url not in (holder.page.url or ""):
            try:
                holder.page.goto(meta.sale_url, wait_until="domcontentloaded", timeout=20000)
                holder.page.wait_for_timeout(1500)
            except Exception:
                pass
        dom_snap = holder.snapshot_dom()
        holder.restart(headless=state["headless"])

        healer = SelfHealer(max_heal=state["max_heal"], use_tavily=state["use_tavily"])
        err_obj = RuntimeError(
            f"{state['last_error'] or '0건 수집'} | DOM={json.dumps(dom_snap, ensure_ascii=False)[:2500]}"
        )
        rec = healer.heal_exception(err_obj, script_path=__file__, goal=f"{meta.name}({meta.domain}) 약관 PDF 수집")

        override_urls = dict(state["override_urls"])
        click_hints = dict(state["click_hints"])
        new_urls = tavily_find_urls(meta) + [u for u in rec.get("tavily_urls", []) if meta.domain in u]
        if rec.get("new_url") and meta.domain in rec["new_url"]:
            new_urls.insert(0, rec["new_url"])
        if new_urls:
            override_urls[insurer_id] = list(dict.fromkeys(override_urls.get(insurer_id, []) + new_urls))
        new_hints = list(rec.get("click_texts") or []) + [f"JS:{js}" for js in (rec.get("js_actions") or []) if js]
        if new_hints:
            click_hints[insurer_id] = list(dict.fromkeys(click_hints.get(insurer_id, []) + new_hints))

        healing_log = list(state["healing_log"])
        healing_log.append(
            {
                "insurer": insurer_id,
                "attempt": next_attempt,
                "reason": state["last_error"] or "empty_results",
                "actions": rec.get("actions", []),
                "new_urls": new_urls,
                "click_hints": click_hints.get(insurer_id, []),
            }
        )
        print(f"  [Self-Heal:{insurer_id}] 조치={rec.get('actions', [])}, 힌트={click_hints.get(insurer_id, [])}")
        return {"attempt": next_attempt, "override_urls": override_urls, "click_hints": click_hints, "healing_log": healing_log}

    def advance_node(state: AppState) -> dict[str, Any]:
        """현재 보험사 수집 건수를 요약에 기록하고 다음 보험사 인덱스로 이동."""
        insurer_id = state["targets"][state["target_idx"]]
        summary = dict(state["summary"])
        summary[insurer_id] = len(state["last_items"])
        return {"target_idx": state["target_idx"] + 1, "attempt": 0, "last_items": [], "last_error": "", "summary": summary}

    def finalize_node(state: AppState) -> dict[str, Any]:
        """전체 수집 요약 및 자가 치유 이력을 healing_report.json으로 저장하고 출력."""
        out_base = Path(state["output_dir"])
        out_base.mkdir(parents=True, exist_ok=True)
        report_path = out_base / "healing_report.json"
        report_path.write_text(
            json.dumps({"summary": state["summary"], "healing_log": state["healing_log"], "blocked": state["blocked"], "error": state["last_error"]}, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        print("\n=== [최종 수집 및 자가 치유 요약] ===")
        print(json.dumps(state["summary"], ensure_ascii=False, indent=2))
        print(f"자가 치유 리포트 -> {report_path}")
        return {}

    def route_after_collect(state: AppState) -> Literal["heal", "advance", "finalize"]:
        """차단 시 즉시 종료, 오류/0건이고 재시도 여유가 있으면 heal, 그 외 advance로 분기."""
        if state["blocked"]:
            return "finalize"
        if (state["last_error"] or len(state["last_items"]) == 0) and state["attempt"] < state["max_heal"]:
            return "heal"
        return "advance"

    def route_after_advance(state: AppState) -> Literal["collect", "finalize"]:
        """남은 대상 보험사가 있으면 collect, 모두 완료했으면 finalize로 분기."""
        if state["blocked"] or state["target_idx"] >= len(state["targets"]):
            return "finalize"
        return "collect"

    builder = StateGraph(AppState)
    builder.add_node("init", init_node)
    builder.add_node("collect", collect_node)
    builder.add_node("heal", heal_node)
    builder.add_node("advance", advance_node)
    builder.add_node("finalize", finalize_node)

    builder.add_edge(START, "init")
    builder.add_edge("init", "collect")
    builder.add_conditional_edges("collect", route_after_collect)
    builder.add_edge("heal", "collect")
    builder.add_conditional_edges("advance", route_after_advance)
    builder.add_edge("finalize", END)
    return builder.compile(checkpointer=MemorySaver())


def main() -> None:
    """CLI 인자를 파싱하고 LangGraph 자가 치유 보험 약관 다운로더를 실행."""
    parser = argparse.ArgumentParser(description="자가 치유(Self-Healing) 7개 보험사 약관 PDF 다운로더")
    parser.add_argument("--target", default="all", help=f"수집 대상: all 또는 쉼표 구분 ({','.join(ALL_TARGETS)})")
    parser.add_argument("--output", default="./output", help="저장 루트 폴더 경로")
    parser.add_argument("--limit", type=int, default=5, help="보험사별 수집 제한 (0이면 전체)")
    parser.add_argument("--max-heal", type=int, default=2, help="보험사별 최대 자가 치유 재시도 횟수")
    parser.add_argument("--use-tavily", action="store_true", help="시작 시 TavilySearch로 공시실 URL 사전 탐색")
    parser.add_argument("--no-download", action="store_true", help="PDF 저장 없이 목록만 수집")
    parser.add_argument("--show-browser", action="store_true", help="브라우저 창 표시")
    args = parser.parse_args()

    targets = ALL_TARGETS if args.target.strip().lower() == "all" else [
        t.strip() for t in args.target.split(",") if t.strip() in RUNNERS
    ]
    if not targets:
        raise ValueError(f"--target은 all 또는 {ALL_TARGETS} 중 하나여야 합니다.")

    holder = UnifiedSessionHolder()
    app = build_self_healing_graph(holder)
    init_state: AppState = {
        "targets": targets,
        "target_idx": 0,
        "output_dir": str(Path(args.output).resolve()),
        "limit": args.limit,
        "download": not args.no_download,
        "headless": not args.show_browser,
        "use_tavily": args.use_tavily,
        "max_heal": args.max_heal,
        "attempt": 0,
        "last_items": [],
        "last_error": "",
        "override_urls": {},
        "click_hints": {},
        "healing_log": [],
        "summary": {},
        "blocked": False,
    }
    try:
        app.invoke(init_state, config={"configurable": {"thread_id": "self-healing-insurer"}, "recursion_limit": 200})
    finally:
        holder.close()


if __name__ == "__main__":
    main()
"""공개 공시실 수집 프로파일 자동 탐색·생성·검증기 (사이트 비종속).

목적 (2026-10-25 LuckyBoys 지시: "프로그램에 맡겨 스스로 고치게")
    사람이나 에이전트가 사이트 구조를 대신 조사하지 않아도, 프로그램이 스스로
    1) 브라우저(Playwright)로 시작 페이지를 열고 목록을 차례로 클릭하며 XHR 요청·응답을 기록하고
    2) 기록만 보고 수집 프로파일(steps/seeds/document)을 추론하고
    3) 실제로 끝까지 한 경로를 따라가 PDF 1건을 받아 검증한 뒤
    4) 검증에 실패하면 다른 항목을 골라 다시 탐색한다(최대 시도 횟수 config).
    이 파일에는 특정 사이트 이름·URL·필드명이 없다. 사이트 정보는 입력과 캡처 데이터뿐이다.

입력 (stdin JSON)
    {"mode": "auto"|"discover"|"validate",
     "name": "<프로파일 이름 [a-z0-9_]>",
     "start_urls": [{"url": "https://...", "vars": {"sale_label": "판매중"}}, ...],   # discover/auto
     "document_keyword": "약관",                                                     # 받을 문서 종류
     "apply": false}                                                                 # true일 때만 프로파일 저장
    - discover: 탐색·추론만(저장 없음, 후보 프로파일 출력)
    - validate: 저장된 프로파일을 실제 1경로로 검증(PDF 1건 임시 다운로드 후 삭제)
    - auto    : 저장된 프로파일이 검증되면 그대로 사용. 없거나 실패하면 재탐색→검증→(apply면) 저장
출력: stdout JSON 보고서. 캡처·후보·검증 증빙은 config.OUTPUT_PATH 아래 autodiscover 폴더에 남긴다.
안전: GET/POST 조회와 공개 PDF 다운로드만 한다. 로그인·입력폼 제출·외부 호스트 접근 없음.
"""
from __future__ import annotations

import importlib.util
import json
import re
import shutil
import sys
import tempfile
import time
import urllib.parse
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import config  # noqa: E402 - 루트 공통 설정(사용자 지침 4)
from common.common_function import now_kst_iso, write_json_atomic  # noqa: E402

_SETTINGS = config.PROFILE_AUTODISCOVER
NAME_PATTERN = re.compile(r"^[a-z0-9_]{1,64}$")
DOC_VAR = "doc_file"          # 프로파일에서 문서 파일명을 담는 변수 이름
ENGINE_PATH = Path(__file__).resolve().with_name("public_document_catalog_collector.py")


# ---------------------------------------------------------------------------
# 순수 추론 함수 (네트워크·브라우저 없이 테스트)
# ---------------------------------------------------------------------------
def find_lists(data: Any, prefix: str = "") -> list[tuple[str, list]]:
    """응답 JSON에서 '객체들의 목록'을 키 순서대로 찾는다(중첩은 점 경로). 빈 목록·값 목록은 제외."""
    found: list[tuple[str, list]] = []
    if not isinstance(data, dict):
        return found
    for key, value in data.items():
        path = f"{prefix}{key}"
        if isinstance(value, list) and value and all(isinstance(item, dict) for item in value):
            found.append((path, value))
        elif isinstance(value, dict):
            found.extend(find_lists(value, path + "."))
    return found


def _text(value: Any) -> str:
    """비교용 문자열(공백 정리). None은 빈 문자열."""
    return re.sub(r"\s+", " ", "" if value is None else str(value)).strip()


def score_element(item: dict, element: dict) -> int:
    """화면 요소가 목록 항목을 그린 것인지 점수화한다(속성값·전체 텍스트의 '완전 일치'만 센다).

    element = {"text": 보이는 글자, "attrs": {속성명: 값}}. 부분 문자열 일치는 오클릭 위험이 커서 제외.
    """
    values = {_text(v) for v in item.values() if _text(v)}
    score = sum(1 for name, value in element.get("attrs", {}).items()
                if name not in {"class", "style", "id", "href", "type", "title"} and _text(value) in values)
    if _text(element.get("text")) in values:
        score += 1
    return score


def pick_document_value(response: Any, keyword: str) -> tuple[str, str, str] | None:
    """응답 목록에서 keyword가 들어간 .pdf 파일명을 찾는다 → (목록 경로, 필드명, 값). 없으면 None."""
    for path, items in find_lists(response):
        for item in items:
            for field, value in item.items():
                text = _text(value)
                if text.lower().endswith(".pdf") and keyword in text:
                    return path, field, str(value).strip()   # 원문 보존(파일명 안 연속 공백 유지)
    return None


def _var_name(field: str) -> str:
    """응답 필드명을 프로파일 변수 이름으로 바꾼다(GOODS_TYPE → goods_type, goodsIdx → goodsidx)."""
    return re.sub(r"[^a-z0-9_]", "_", field.lower())


def _find_link(calls: list[dict], i: int, value: str) -> tuple[int, str, str] | None:
    """i번째 요청값이 앞선 응답(가까운 단계부터) 목록 항목의 어느 필드에서 왔는지 찾는다."""
    for j in range(i - 1, -1, -1):
        for path, items in find_lists(calls[j]["response"]):
            for item in items:
                for field, field_value in item.items():
                    if _text(field_value) == value:
                        return j, path, field
    return None


def parse_form_body(text: str | None) -> tuple[dict, str]:
    """폼 본문을 해석하고 문자셋을 판별한다(UTF-8 우선, 실패 시 cp949). → (값 dict, 문자셋).

    국내 ASP 문서 서버는 파일명을 cp949로 퍼센트 인코딩해 보낸다(2026-10-25 실제 캡처로 확인).
    """
    if not text:
        return {}, "utf-8"
    for charset in ("utf-8", "cp949"):
        try:
            parsed = urllib.parse.parse_qs(text, keep_blank_values=True, encoding=charset, errors="strict")
        except UnicodeDecodeError:
            continue
        return {key: values[-1] for key, values in parsed.items()}, charset
    return {}, "utf-8"


def volatile_params(calls: list[dict]) -> set[str]:
    """요청마다 값이 모두 다르고 어떤 앞선 응답에서도 오지 않는 파라미터(캐시 방지 난수 등)를 찾는다.

    이런 값은 서버가 의미 없이 받는 값이라 프로파일에서 뺀다(넣으면 연결 추론이 실패한다).
    """
    if len(calls) < 2:
        return set()
    common = set.intersection(*(set(call["body"]) for call in calls))
    found = set()
    for param in common:
        values = [_text(call["body"][param]) for call in calls]
        if len(set(values)) == len(values) and all(
                _find_link(calls, i, values[i]) is None for i in range(1, len(calls))):
            found.add(param)
    return found


def infer_document(download: dict, file_name: str, var: str, base_host: str | None = None) -> dict:
    """캡처된 다운로드 요청에서 파일명 자리를 변수로 바꿔 document 설정을 만든다.

    문서 서버가 목록 사이트와 다른 호스트면 절대 URL로 남긴다(엔진이 allowed_hosts로 재검사).
    """
    parts = urllib.parse.urlsplit(str(download.get("url", "")))
    origin = "" if base_host in (None, parts.hostname) else f"{parts.scheme}://{parts.netloc}"
    path_query = origin + parts.path + (f"?{parts.query}" if parts.query else "")
    document: dict[str, Any] = {"file_var": var}
    replaced = False
    for encoded in (urllib.parse.quote(file_name, safe=""), urllib.parse.quote(file_name, safe="/"),
                    urllib.parse.quote_plus(file_name)):
        if encoded in parts.query:
            path_query = origin + parts.path + "?" + parts.query.replace(encoded, "{" + var + "|q}")
            replaced = True
            break
    body = {key: ("{" + var + "}" if _text(value) == _text(file_name) else value)
            for key, value in (download.get("body") or {}).items()}
    if any(value == "{" + var + "}" for value in body.values()):
        replaced = True
    if not replaced:
        raise ValueError("download request does not contain the file name")
    document["url_template"] = path_query
    if str(download.get("method", "GET")).upper() == "POST":
        document["method"] = "POST"
        document["body"] = body
    if download.get("charset", "utf-8") != "utf-8":
        document["body_charset"] = download["charset"]
    return document


def infer_profile(name: str, base_url: str, runs: list[dict], keyword: str | None = None) -> dict:
    """시작 페이지별 캡처(runs)에서 수집 프로파일을 추론한다.

    규칙(사이트 비종속):
    - 첫 요청 본문: 시작 페이지마다 값이 다르면 시드 변수({파라미터명}), 같으면 고정값.
    - 이후 요청: 직전 요청과 값이 '바뀐' 파라미터는 앞선 응답 목록 항목의 필드에서 온 값으로 보고
      그 필드를 export 변수로 연결한다. 바뀌지 않은 파라미터는 직전 단계 템플릿을 그대로 잇는다.
    - 마지막 응답에서 다운로드한 파일명이 있는 필드를 문서 변수로 쓴다.
    추론할 수 없으면 ValueError(추측으로 잘못된 프로파일을 만들지 않음).
    """
    if not isinstance(name, str) or not NAME_PATTERN.fullmatch(name):
        raise ValueError("profile name must match [a-z0-9_]{1,64}")
    if not runs:
        raise ValueError("at least one captured run is required")
    if any(not run["calls"] for run in runs):
        raise ValueError("captured run has no list requests")
    if len({run["calls"][0]["path"] for run in runs}) != 1:
        raise ValueError("every start page must share the same first request")
    # 화면마다 중간 단계를 건너뛸 수 있다(예: 판매중지 화면). 가장 긴 경로를 구조로 쓰고,
    # 같은 경로를 탄 시작 페이지끼리만 연결 규칙을 교차 확인한다. 나머지는 시드 값만 제공.
    structural = max(runs, key=lambda run: len(run["calls"]))
    structure = [c["path"] for c in structural["calls"]]
    linked_runs = [run for run in runs if [c["path"] for c in run["calls"]] == structure]
    count = len(structure)
    skip = volatile_params(structural["calls"])

    steps = [{"url": call["path"], "body": {}, "list_path": None, "export": {}} for call in structural["calls"]]
    seed_vars: list[dict] = [dict(run["start"].get("vars", {})) for run in runs]

    # 1) 첫 요청: 시작 페이지 간 차이 → 시드 변수
    for param in runs[0]["calls"][0]["body"]:
        if param in skip:
            continue
        values = [_text(run["calls"][0]["body"].get(param)) for run in runs]
        if len(set(values)) > 1:
            steps[0]["body"][param] = "{" + param + "}"
            for index, value in enumerate(values):
                seed_vars[index][param] = value
        else:
            steps[0]["body"][param] = runs[0]["calls"][0]["body"][param]

    # 2) 이후 요청: 바뀐 값은 앞선 응답 필드로 연결, 안 바뀐 값은 이전 템플릿 승계
    for i in range(1, count):
        previous_template = steps[i - 1]["body"]
        for param in structural["calls"][i]["body"]:
            if param in skip:
                continue
            template = None
            for run in linked_runs:
                calls = run["calls"]
                value = _text(calls[i]["body"].get(param))
                before = calls[i - 1]["body"].get(param)
                if before is not None and _text(before) == value and param in previous_template:
                    candidate = previous_template[param]
                elif not value:
                    candidate = ""
                else:
                    link = _find_link(calls, i, value)
                    if link is None:
                        raise ValueError(f"cannot link request value: step {i} {param}={value!r}")
                    j, path, field = link
                    if steps[j]["list_path"] not in (None, path):
                        raise ValueError(f"conflicting list paths at step {j}: {steps[j]['list_path']} vs {path}")
                    steps[j]["list_path"] = path
                    steps[j]["export"][_var_name(field)] = field
                    candidate = "{" + _var_name(field) + "}"
                if template is not None and template != candidate:
                    raise ValueError(f"start pages disagree on step {i} {param}: {template!r} vs {candidate!r}")
                template = candidate
            steps[i]["body"][param] = template

    # 3) 마지막 응답에서 문서 파일명 필드
    last = steps[-1]
    for run in linked_runs:
        located = None
        for path, items in find_lists(run["calls"][-1]["response"]):
            for item in items:
                for field, value in item.items():
                    if _text(value) == _text(run["file_name"]):
                        located = (path, field)
                        break
                if located:
                    break
            if located:
                break
        if located is None:
            raise ValueError(f"downloaded file name not found in last response: {run['file_name']!r}")
        if last["list_path"] not in (None, located[0]) or last["export"].get(DOC_VAR) not in (None, located[1]):
            raise ValueError("start pages disagree on the document field")
        last["list_path"] = located[0]
        last["export"][DOC_VAR] = located[1]
    for index, step in enumerate(steps):
        if not step["list_path"]:
            raise ValueError(f"cannot link step {index}: no later request uses its list")

    base = urllib.parse.urlsplit(base_url)
    document = infer_document(structural["download"], structural["file_name"], DOC_VAR, base.hostname)
    hosts = [base.hostname]
    document_host = urllib.parse.urlsplit(str(structural["download"].get("url", ""))).hostname
    if document_host and document_host not in hosts:
        hosts.append(document_host)
    start_vars = runs[0]["start"].get("vars", {})
    if start_vars:
        document["subdir_var"] = "sale_label" if "sale_label" in start_vars else next(iter(start_vars))
    first_type = str(runs[0]["calls"][0].get("content_type", "")).lower()
    pages = []
    for run, variables in zip(runs, seed_vars):
        start = urllib.parse.urlsplit(run["start"]["url"])
        pages.append({"url": (start.path or "/") + (f"?{start.query}" if start.query else ""), "vars": variables})
    return {
        "_comment": f"profile_autodiscover가 {now_kst_iso()}에 브라우저 캡처로 자동 생성(키워드: {keyword or '-'}).",
        "name": name,
        "base_url": f"{base.scheme}://{base.netloc}",
        "allowed_hosts": hosts,
        "request": {"method": "POST", "body_format": "json" if "json" in first_type else "form",
                    "headers": {"User-Agent": _SETTINGS["user_agent"], "X-Requested-With": "XMLHttpRequest",
                                "Referer": runs[0]["start"]["url"]},
                    "delay_seconds": _SETTINGS["delay_seconds"], "timeout_seconds": _SETTINGS["timeout_seconds"]},
        "seeds": {"pages": pages},
        "steps": steps,
        "document": document,
        "time_limit_seconds": int(config.PUBLIC_DOCUMENT_COLLECTOR["max_time_limit_seconds"]),
    }


# ---------------------------------------------------------------------------
# 브라우저 캡처 (Playwright, 서버에서 실행)
# ---------------------------------------------------------------------------
_COLLECT_JS = """
(limit) => {
  const nodes = Array.from(document.querySelectorAll('a,button,[onclick],[data-idx],li,td'));
  const out = [];
  for (const el of nodes) {
    if (out.length >= limit) break;
    const r = el.getBoundingClientRect();
    if (r.width === 0 || r.height === 0) continue;
    if (el.closest('header,nav,footer,#header,#footer,#gnb')) continue;
    const attrs = {};
    for (const a of el.attributes) attrs[a.name.toLowerCase()] = a.value;
    el.setAttribute('data-sps-pick', String(out.length));
    out.push({index: out.length, text: (el.innerText || '').trim().slice(0, 200), attrs});
  }
  return out;
}
"""


def _parse_body(post_data: str | None, content_type: str) -> dict:
    """요청 본문을 dict로 바꾼다. JSON/폼 이외(암호화 등)는 빈 dict → 추론 단계에서 연결 실패로 드러남."""
    if not post_data:
        return {}
    if "json" in content_type.lower():
        try:
            data = json.loads(post_data)
            return data if isinstance(data, dict) else {}
        except ValueError:
            return {}
    return parse_form_body(post_data)[0]


def capture_run(start: dict, keyword: str, choice: int = 0) -> dict:
    """시작 페이지 1개를 브라우저로 열어 '목록 클릭 → 다음 목록' 순서로 내려가며 요청을 기록한다.

    choice: 각 목록에서 몇 번째 항목을 클릭할지(재탐색 시 다른 항목으로 다시 시도).
    """
    from playwright.sync_api import sync_playwright

    host = urllib.parse.urlsplit(start["url"]).hostname
    calls: list[dict] = []
    other_requests: list[dict] = []
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        context = browser.new_context(user_agent=_SETTINGS["user_agent"], accept_downloads=True)
        page = context.new_page()

        def on_response(response) -> None:
            request = response.request
            if urllib.parse.urlsplit(request.url).hostname != host:
                return
            if request.resource_type in ("xhr", "fetch"):
                try:
                    data = response.json()
                except Exception:  # noqa: BLE001 - JSON이 아닌 응답(HTML 조각)은 목록 API가 아님
                    return
                content_type = request.headers.get("content-type", "")
                calls.append({"path": urllib.parse.urlsplit(request.url).path, "method": request.method,
                              "content_type": content_type,
                              "body": _parse_body(request.post_data, content_type), "response": data})

        def on_request(request) -> None:
            # 다운로드는 폼 제출·새 창·XHR 확인 후 이동 등 방식이 다양하므로 같은 호스트 요청을 모두 기록한다.
            # 문서 서버가 별도 호스트일 수 있어 호스트 제한 없이 기록하고, 프로파일 생성 단계에서 호스트를 검사한다.
            if request.resource_type not in ("image", "stylesheet", "font", "media"):
                other_requests.append({"method": request.method, "url": request.url,
                                       "content_type": request.headers.get("content-type", ""),
                                       "post_data": request.post_data})

        console: list[str] = []
        response_types: dict[str, str] = {}

        def on_any_response(response) -> None:
            # 다운로드가 2단계(확인 페이지 → 실제 PDF)인 사이트를 판별하려고 응답 형식을 남긴다.
            response_types[response.url] = f"{response.status} {response.headers.get('content-type', '')}"

        page.on("response", on_response)
        context.on("response", on_any_response)
        context.on("request", on_request)
        page.on("console", lambda message: console.append(f"{message.type}: {message.text[:200]}"))
        page.on("dialog", lambda dialog: (console.append(f"dialog: {dialog.message[:200]}"), dialog.dismiss()))
        page.goto(start["url"], wait_until="networkidle", timeout=_SETTINGS["page_timeout_ms"])
        if not calls:
            browser.close()
            raise ValueError("start page made no JSON list request")
        chain = [calls[-1]]           # 마지막으로 받은 목록 응답부터 내려간다
        used_lists: set[str] = set()
        result: dict[str, Any] = {"start": start, "calls": chain, "choice": choice}
        for _depth in range(int(_SETTINGS["max_depth"])):
            current = chain[-1]
            found = pick_document_value(current["response"], keyword)
            # 문서 목록보다 앞에 아직 클릭하지 않은 목록(분류·상품)이 있으면 먼저 내려간다.
            # (첫 화면이 기본 상품의 문서를 미리 보여 주는 사이트에서 한 상품만 수집되는 오류 방지)
            if found:
                list_order = [p for p, _ in find_lists(current["response"])]
                earlier = list_order[:list_order.index(found[0])]
                if any(f"{current['path']}::{p}" not in used_lists for p in earlier):
                    found = None
            if found:
                _path, _field, file_name = found
                # 응답 직후 화면 그리기가 늦을 수 있어 잠시 다시 찾는다.
                target, elements = None, []
                deadline = time.monotonic() + _SETTINGS["click_wait_ms"] / 1000
                while target is None and time.monotonic() < deadline:
                    elements = page.evaluate(_COLLECT_JS, int(_SETTINGS["max_elements"]))
                    target = next((e for e in elements
                                   if any(_text(v) == _text(file_name) for v in e["attrs"].values())
                                   or _text(e["text"]) == _text(file_name)), None)
                    if target is None:
                        page.wait_for_timeout(500)
                if target is None:
                    shown = [v for e in elements for v in e["attrs"].values() if str(v).lower().endswith(".pdf")][:5]
                    raise ValueError(f"document button for {file_name!r} was not on screen; "
                                     f"chain={[c['path'] for c in chain]}; pdf attrs on screen={shown}")
                before = len(other_requests)
                try:
                    with page.expect_download(timeout=_SETTINGS["click_wait_ms"]):
                        page.click(f'[data-sps-pick="{target["index"]}"]')
                except Exception:  # noqa: BLE001 - 다운로드 대신 새 창/이동으로 처리하는 사이트도 있다
                    page.wait_for_timeout(3000)
                quoted = {urllib.parse.quote(file_name, safe=""), urllib.parse.quote_plus(file_name), file_name}
                download = next((r for r in other_requests[before:]
                                 if any(q in r["url"] for q in quoted)
                                 or any(_text(v) == _text(file_name)
                                        for v in parse_form_body(r["post_data"])[0].values())), None)
                if download is None:
                    seen = [{"method": r["method"], "url": r["url"][:200],
                             "post_data": (r["post_data"] or "")[:200]} for r in other_requests[before:]][:10]
                    raise ValueError("clicking the document did not produce a download request with the file name; "
                                     f"requests after click: {json.dumps(seen, ensure_ascii=False)}; "
                                     f"console: {json.dumps(console[-8:], ensure_ascii=False)}; target: {json.dumps(target, ensure_ascii=False)[:300]}")
                page.wait_for_timeout(3000)
                result["after_click"] = [{"method": r["method"], "url": r["url"][:300],
                                          "post_data": (r["post_data"] or "")[:300],
                                          "response": response_types.get(r["url"], "")}
                                         for r in other_requests[before:]][:15]
                raw_body = download.pop("post_data")
                if "json" in download["content_type"].lower():
                    download["body"], download["charset"] = _parse_body(raw_body, download["content_type"]), "utf-8"
                else:
                    download["body"], download["charset"] = parse_form_body(raw_body)
                result.update({"file_name": file_name, "download": download})
                browser.close()
                return result
            clicked = False
            for list_path, items in find_lists(current["response"]):
                key = f"{current['path']}::{list_path}"
                if key in used_lists:
                    continue
                elements = page.evaluate(_COLLECT_JS, int(_SETTINGS["max_elements"]))
                item = items[min(choice, len(items) - 1)]
                ranked = sorted(((score_element(item, e), e) for e in elements), key=lambda x: -x[0])
                if not ranked or ranked[0][0] == 0:
                    continue
                count_before = len(calls)
                page.click(f'[data-sps-pick="{ranked[0][1]["index"]}"]')
                deadline = time.monotonic() + _SETTINGS["click_wait_ms"] / 1000
                while len(calls) == count_before and time.monotonic() < deadline:
                    page.wait_for_timeout(200)
                used_lists.add(key)
                if len(calls) > count_before:
                    page.wait_for_timeout(500)
                    chain.append(calls[-1])
                    clicked = True
                    break
            if not clicked:
                break
        browser.close()
    raise ValueError(f"no '{keyword}' PDF reached within {_SETTINGS['max_depth']} clicks")


# ---------------------------------------------------------------------------
# 실검증 (엔진으로 1경로를 끝까지 따라가 PDF 1건 임시 다운로드 후 삭제)
# ---------------------------------------------------------------------------
def _load_engine():
    spec = importlib.util.spec_from_file_location("catalog_engine_for_autodiscover", ENGINE_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def validate_live(profile: dict) -> dict:
    """시드(시작 페이지)마다 각 단계 첫 항목을 따라가 문서 1건을 받아 PDF 검증한다. 파일은 남기지 않는다."""
    engine = _load_engine()
    engine.validate_profile(profile)
    client = engine.SiteClient(profile)
    report: dict[str, Any] = {"profile": profile["name"], "checked_kst": now_kst_iso(), "seeds": []}
    document = profile["document"]
    for seed in engine.collect_seeds(client, profile):
        ctx, counts = dict(seed), []
        items: list = []
        for step in profile["steps"]:
            items = engine.list_at(client.fetch_json(engine.render(step["url"], ctx),
                                                     engine.render(step["body"], ctx)), step["list_path"])
            if not items:
                raise ValueError(f"empty list at {step['url']} for seed {seed}")
            counts.append(len(items))
            if step is not profile["steps"][-1]:
                ctx.update({var: items[0].get(field) for var, field in step["export"].items()})
        # 마지막 목록에서 문서 몇 건을 차례로 시도한다(사이트에 손상 파일이 섞여 있을 수 있음).
        # 한 건이라도 정상 PDF면 이 시작 페이지는 통과, 모두 실패하면 파일별 원인을 남기고 실패.
        last = profile["steps"][-1]
        tried = []
        passed = None
        for item in items[: int(_SETTINGS["validate_documents_per_seed"])]:
            row = {**ctx, **{var: item.get(field) for var, field in last["export"].items()}}
            try:
                file_name = engine.safe_pdf_name(row.get(document["file_var"]))
                url, form = engine.document_request(document, file_name)
                work = Path(tempfile.mkdtemp(prefix="sps_autodiscover_"))
                try:
                    info = client.download(url, work / file_name, form, document.get("body_charset", "utf-8"))
                finally:
                    shutil.rmtree(work, ignore_errors=True)
                passed = {"file": file_name, **info}
                break
            except Exception as error:  # noqa: BLE001 - 다음 문서로 계속 시도
                tried.append({"file": row.get(document["file_var"]), "error": f"{type(error).__name__}: {str(error)[:200]}"})
        entry = {"seed": seed, "list_sizes": counts, "failed_tries": tried, "passed": passed}
        report["seeds"].append(entry)
        if passed is None:
            raise ValueError(f"no valid document for seed {seed}: {json.dumps(tried, ensure_ascii=False)[:600]}")
    report["ok"] = True
    return report


# ---------------------------------------------------------------------------
# 실행 모드
# ---------------------------------------------------------------------------
def _work_dir(name: str) -> Path:
    path = Path(str(config.OUTPUT_PATH)) / str(_SETTINGS["work_subdir"]) / name
    path.mkdir(parents=True, exist_ok=True)
    return path


def _profile_path(name: str) -> Path:
    return Path(config.PUBLIC_DOCUMENT_COLLECTOR["profile_dir"]) / f"{name}.json"


def discover(name: str, start_urls: list[dict], keyword: str, choice: int) -> dict:
    """모든 시작 페이지를 캡처하고 프로파일 후보를 추론한다(저장 안 함). 캡처는 증빙으로 남긴다."""
    if not start_urls:
        raise ValueError("start_urls is required")
    hosts = {urllib.parse.urlsplit(s["url"]).hostname for s in start_urls}
    if len(hosts) != 1 or None in hosts:
        raise ValueError("all start_urls must be absolute URLs on one host")
    runs = [capture_run(start, keyword, choice) for start in start_urls]
    work = _work_dir(name)
    stamp = now_kst_iso().replace(":", "").replace("-", "")[:15]
    write_json_atomic(work / f"capture_{stamp}_choice{choice}.json", runs)
    base = urllib.parse.urlsplit(start_urls[0]["url"])
    candidate = infer_profile(name, f"{base.scheme}://{base.netloc}", runs, keyword)
    write_json_atomic(work / f"candidate_{stamp}_choice{choice}.json", candidate)
    return candidate


def auto(request: dict) -> dict:
    """저장된 프로파일 검증 → 실패/없음이면 재탐색(choice 0,1,2…)→검증 → apply면 저장."""
    name = request["name"]
    report: dict[str, Any] = {"mode": "auto", "name": name, "attempts": []}
    path = _profile_path(name)
    # 재탐색 입력(시작 URL·문서 키워드)은 요청 → 저장된 프로파일의 autodiscover 블록 순으로 쓴다.
    # 그래서 수집기 self_heal은 이름만으로 사람 도움 없이 다시 탐색할 수 있다.
    existing = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
    saved_inputs = existing.get("autodiscover", {}) if isinstance(existing, dict) else {}
    start_urls = request.get("start_urls") or saved_inputs.get("start_urls", [])
    keyword = request.get("document_keyword") or saved_inputs.get("document_keyword", "약관")
    if path.exists():
        try:
            report["existing"] = validate_live(existing)
            report["result"] = "EXISTING_PROFILE_VALID"
            return report
        except Exception as error:  # noqa: BLE001 - 사이트가 바뀌었으면 재탐색으로 넘어간다
            report["existing_error"] = f"{type(error).__name__}: {str(error)[:300]}"
    for choice in range(int(_SETTINGS["max_attempts"])):
        attempt: dict[str, Any] = {"choice": choice}
        try:
            candidate = discover(name, start_urls, keyword, choice)
            attempt["validation"] = validate_live(candidate)
            # 다음 self_heal 재탐색에 쓸 입력을 프로파일에 함께 남긴다(엔진은 이 키를 쓰지 않음).
            candidate["autodiscover"] = {"start_urls": start_urls, "document_keyword": keyword}
            if request.get("apply"):
                if path.exists():
                    backup = path.with_name(f"{path.stem}_BACKUP_{now_kst_iso()[:19].replace('-', '').replace(':', '').replace('T', '_')}.json")
                    shutil.copy2(path, backup)
                    attempt["backup"] = str(backup)
                write_json_atomic(path, candidate)
                attempt["saved"] = str(path)
            attempt["profile"] = candidate
            report["attempts"].append(attempt)
            report["result"] = "DISCOVERED_AND_VALID" + ("_SAVED" if request.get("apply") else "_NOT_SAVED")
            return report
        except Exception as error:  # noqa: BLE001 - 다음 항목으로 재탐색
            attempt["error"] = f"{type(error).__name__}: {str(error)[:400]}"
            report["attempts"].append(attempt)
    report["result"] = "FAILED"
    return report


def main() -> None:
    request = json.loads(sys.stdin.read() or "{}")
    mode = request.get("mode")
    name = request.get("name")
    if mode not in {"auto", "discover", "validate"}:
        raise ValueError("mode must be auto|discover|validate")
    if not isinstance(name, str) or not NAME_PATTERN.fullmatch(name):
        raise ValueError("name must match [a-z0-9_]{1,64}")
    if mode == "validate":
        result = validate_live(json.loads(_profile_path(name).read_text(encoding="utf-8")))
    elif mode == "discover":
        result = discover(name, request.get("start_urls", []), request.get("document_keyword", "약관"),
                          int(request.get("choice", 0)))
    else:
        result = auto(request)
    print(json.dumps(result, ensure_ascii=False, indent=1, default=str))


if __name__ == "__main__":
    main()

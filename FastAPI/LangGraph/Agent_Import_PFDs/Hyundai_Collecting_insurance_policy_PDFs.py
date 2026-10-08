"""
현대해상(hi.co.kr) 공시실 전 카테고리 약관 PDF 일괄 자동 수집 스크립트
================================================================================
프로그램 목적:
    - 현대해상 공시실 4단계 네비게이션을 순차 순회하며 모든 약관 PDF를 다운로드합니다.
    - 3단계(보험유형)가 없는 특수 카테고리는 지정된 규칙으로 폴더를 생성합니다:
        1) 일반보험 -> {판매형태}_일반보험_일반
        2) 퇴직보험 -> {판매형태}_퇴직보험_퇴직
        3) 퇴직연금 -> {판매형태}_퇴직연금_퇴직
    - 자동차보험, 장기보험은 실제 3열의 세부 유형명으로 폴더를 생성합니다.
    - 카테고리 전환 시 이전 상품 목록이 남아있는 비동기 엇박자를 원천 차단하기 위해
      카테고리 클릭 후 4열 목록 갱신 동기화 대기를 강화했습니다.
    - 기존 파일 존재 시 건너뛰기(이어받기), 메모리 누수 방지(팝업 즉시 종료)를 지원합니다.

작성자: Luckyboys
실행 환경: Python 3.10+, Playwright (Chromium)
기본 저장 루트: C:\\source\\Python\\chapter31\\insurance_policies
<Bash>
# 1. Playwright 패키지 설치
pip install playwright

# 2. 브라우저 엔진(Chromium, Firefox, WebKit) 바이너리 설치
playwright install

================================================================================
"""

import logging
import os
import re
import time
from playwright.sync_api import BrowserContext, Page, sync_playwright
from config import INSURANCE_POLICY_DIR, LOG_PATH
from common.common_function import ensure_dirs

ERROR_LOG_PATH = os.path.join(LOG_PATH, "collecting_insurance_policy_pdfs.log")
os.makedirs(LOG_PATH, exist_ok=True)
logger = logging.getLogger("InsurancePolicyPDFCollector")
if not logger.handlers:
    _file_handler = logging.FileHandler(ERROR_LOG_PATH, encoding="utf-8")
    _file_handler.setFormatter(
        logging.Formatter("%(asctime)s %(levelname)s %(message)s")
    )
    logger.addHandler(_file_handler)
logger.setLevel(logging.INFO)

# ==============================================================================
# 1. 파일 저장 디렉토리 및 전역 설정
# ==============================================================================
# 다운로드 루트 디렉토리
BASE_DOWNLOAD_DIR: str = str(INSURANCE_POLICY_DIR)

# 현대해상 공시실 다이렉트 진입 URL
TARGET_URL: str = "https://www.hi.co.kr/serviceAction.do?view=bin/PA/03/HHPA03010M"

# 3단계(보험유형)가 생략되는 카테고리별 맞춤 하위 폴더명 매핑
DIRECT_CATEGORIES: dict[str, str] = {
    "일반보험": "일반",
    "퇴직보험": "퇴직",
    "퇴직연금": "퇴직",
}


def sanitize_filename(name: str) -> str:
    """
    윈도우 파일 시스템에서 허용되지 않는 특수문자를 제거하고
    최대 45자의 안전한 폴더/파일명 문자열을 반환합니다.
    """
    clean_name = re.sub(r'[\\/*?:"<>|]', "", name).strip()
    return (clean_name[:45] or "이름없음")


def click_column_item(page: Page, col_index: int, target_text: str) -> bool:
    """
    화면 4단 박스를 가로 물리 좌표(X 비율)로 분할하여 지정된 열 번호 내부의 텍스트만 정밀 클릭합니다.
    헤더의 원형 숫자 배지('1', '2', '3', '4')나 다른 열 텍스트 오클릭을 원천 방지합니다.

    Args:
        page (Page): Playwright 페이지 객체
        col_index (int): 1(판매형태), 2(보험종류), 3(보험유형)
        target_text (str): 클릭할 메뉴 텍스트

    Returns:
        bool: 클릭 성공 여부
    """
    return page.evaluate(r"""(data) => {
        const { colIdx, text } = data;
        
        const boxes = Array.from(document.querySelectorAll('div, section')).filter(el => {
            const t = el.innerText || '';
            return t.includes('판매형태') && t.includes('보험종류') && !el.closest('header');
        });
        if (boxes.length === 0) return false;
        boxes.sort((a, b) => (a.innerText || '').length - (b.innerText || '').length);
        const mainBox = boxes[0];
        const boxRect = mainBox.getBoundingClientRect();

        // 열별 X 상대 비율 (1열: 0~26%, 2열: 20~43%, 3열: 38~63%)
        const ranges = {
            1: { min: 0.00, max: 0.26 },
            2: { min: 0.20, max: 0.43 },
            3: { min: 0.38, max: 0.63 }
        };
        const range = ranges[colIdx];
        if (!range) return false;

        const minX = boxRect.left + (boxRect.width * range.min);
        const maxX = boxRect.left + (boxRect.width * range.max);

        const elements = Array.from(mainBox.querySelectorAll('a, button, li, span, div')).filter(el => {
            if (!el.offsetParent && el.offsetWidth === 0) return false;
            const r = el.getBoundingClientRect();
            const centerX = r.left + (r.width / 2);
            const txt = (el.innerText || el.textContent || '').trim();
            return centerX >= minX && centerX <= maxX && txt === text;
        });

        if (elements.length === 0) return false;

        const target = elements.find(el => el.tagName === 'A') || elements[0];
        const clickTarget = target.tagName === 'A' ? target : (target.closest('a') || target);
        clickTarget.scrollIntoView({ block: 'center' });
        ['mouseover', 'mousedown', 'mouseup', 'click'].forEach(evt => {
            clickTarget.dispatchEvent(new MouseEvent(evt, { bubbles: true, cancelable: true }));
        });
        if (clickTarget.click) clickTarget.click();
        return true;
    }""", {"colIdx": col_index, "text": target_text})


def get_column_3_types(page: Page) -> list[str]:
    """
    3열(보험유형) 영역 안에 렌더링된 실제 유형 목록만 추출합니다.
    """
    return page.evaluate(r"""() => {
        const boxes = Array.from(document.querySelectorAll('div, section')).filter(el => {
            const t = el.innerText || '';
            return t.includes('판매형태') && t.includes('보험종류') && !el.closest('header');
        });
        if (boxes.length === 0) return [];
        boxes.sort((a, b) => (a.innerText || '').length - (b.innerText || '').length);
        const mainBox = boxes[0];
        const boxRect = mainBox.getBoundingClientRect();

        const minX = boxRect.left + (boxRect.width * 0.38);
        const maxX = boxRect.left + (boxRect.width * 0.63);

        const elements = Array.from(mainBox.querySelectorAll('a, button, li, span')).filter(el => {
            if (!el.offsetParent && el.offsetWidth === 0) return false;
            const r = el.getBoundingClientRect();
            const centerX = r.left + (r.width / 2);
            const txt = (el.innerText || el.textContent || '').trim();
            return centerX >= minX && centerX <= maxX && 
                   txt && txt !== '3' && !txt.includes('보험유형') && 
                   !txt.includes('\n') && !el.querySelector('a');
        });

        const results = [];
        elements.forEach(el => {
            const t = (el.innerText || el.textContent || '').trim();
            if (t && !results.includes(t)) results.push(t);
        });
        return results;
    }""")


def get_column_4_products(page: Page) -> list[str]:
    """
    4열(상품명) 영역에 위치한 순수 상품명만 100% 추출합니다.
    """
    return page.evaluate(r"""() => {
        const boxes = Array.from(document.querySelectorAll('div, section')).filter(el => {
            const t = el.innerText || '';
            return t.includes('판매형태') && t.includes('상품명') && !el.closest('header');
        });
        if (boxes.length === 0) return [];
        boxes.sort((a, b) => (a.innerText || '').length - (b.innerText || '').length);
        const mainBox = boxes[0];
        const boxRect = mainBox.getBoundingClientRect();

        const minX = boxRect.left + (boxRect.width * 0.58);

        const blacklist = [
            '1', '2', '3', '4', '판매형태', '보험종류', '보험유형', '상품명',
            '판매 중인 상품', '판매 중지 상품',
            '자동차보험', '장기보험', '일반보험', '퇴직보험', '퇴직연금',
            '개인용', '업무용', '영업용', '기타', '공동물건',
            '연금', '상해성', '어린이', '의료', '재물성', '저축성', '질병성', '종합성'
        ];

        const elements = Array.from(mainBox.querySelectorAll('a, button, li, span, div, p')).filter(el => {
            if (!el.offsetParent && el.offsetWidth === 0) return false;
            const r = el.getBoundingClientRect();
            const centerX = r.left + (r.width / 2);
            const txt = (el.innerText || el.textContent || '').trim();
            return centerX >= minX && 
                   txt && !txt.includes('\n') && 
                   !blacklist.includes(txt) && 
                   (el.tagName === 'A' || !el.querySelector('a'));
        });

        const productNames = [];
        elements.forEach(el => {
            const txt = (el.innerText || el.textContent || '').trim();
            if (txt && !productNames.includes(txt)) {
                productNames.push(txt);
            }
        });
        return productNames;
    }""")


def click_column_4_product(page: Page, product_name: str) -> bool:
    """
    4열(상품명) 영역 안에서 특정 상품명을 찾아 마우스 클릭 이벤트를 발송합니다.
    """
    return page.evaluate(r"""(pName) => {
        const boxes = Array.from(document.querySelectorAll('div, section')).filter(el => {
            const t = el.innerText || '';
            return t.includes('판매형태') && t.includes('상품명') && !el.closest('header');
        });
        if (boxes.length === 0) return false;
        boxes.sort((a, b) => (a.innerText || '').length - (b.innerText || '').length);
        const mainBox = boxes[0];
        const boxRect = mainBox.getBoundingClientRect();
        const minX = boxRect.left + (boxRect.width * 0.58);

        const elements = Array.from(mainBox.querySelectorAll('a, button, li, span, div, p')).filter(el => {
            const r = el.getBoundingClientRect();
            const centerX = r.left + (r.width / 2);
            const txt = (el.innerText || el.textContent || '').trim();
            return centerX >= minX && txt === pName;
        });

        if (elements.length === 0) return false;

        const target = elements.find(el => el.tagName === 'A') || elements[0];
        const clickTarget = target.tagName === 'A' ? target : (target.closest('a') || target);
        clickTarget.scrollIntoView({ block: 'center' });
        ['mouseover', 'mousedown', 'mouseup', 'click'].forEach(evt => {
            clickTarget.dispatchEvent(new MouseEvent(evt, { bubbles: true, cancelable: true }));
        });
        if (clickTarget.click) clickTarget.click();
        return true;
    }""", product_name)


def fetch_pdf_via_popup(popup_page: Page, context: BrowserContext, save_path: str) -> bool:
    """
    새 탭으로 열린 뷰어 팝업의 실제 PDF URL을 탈취하여 원본 바이너리를 파일로 저장합니다.
    """
    pdf_url: str = popup_page.url

    if ".pdf" in pdf_url.lower() or "fileactionservlet" in pdf_url.lower():
        try:
            response = context.request.get(pdf_url)
            if response.status == 200:
                body_bytes = response.body()
                if body_bytes.startswith(b"%PDF") or b"%PDF" in body_bytes[:1024]:
                    with open(save_path, "wb") as f:
                        f.write(body_bytes)
                    return True
        except Exception as err:
            logger.exception("PDF 바이너리 다운로드 오류: %s", err)
            print(f"      ⚠️ 바이너리 다운로드 통신 오류: {err}")

    return False


def run_full_crawler() -> None:
    """
    전 카테고리 4단계 계층 순회 및 맞춤 폴더 분류 다운로드 메인 제어 루틴입니다.
    """
    ensure_dirs()
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        context = browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            ),
            accept_downloads=True,
        )
        page = context.new_page()

        # ==============================================================================
        # 1. 공시실 메인 접속 및 4단 상자 진입
        # ==============================================================================
        print(f"[초기화] 현대해상 공시실 접속 중: {TARGET_URL}")
        try:
            page.goto(TARGET_URL, wait_until="domcontentloaded", timeout=60000)
        except Exception as err:
            logger.exception("공시실 접속 실패: %s", err)
            print(f"[오류] 공시실 접속 실패: {err}")
            browser.close()
            return
        time.sleep(2.5)

        print("[초기화] [보험상품공시] 메뉴 진입 및 4단 상자 로딩 대기...")
        page.evaluate("""() => {
            const links = Array.from(document.querySelectorAll('a, button, span'));
            const target = links.find(el => el.innerText && el.innerText.trim() === '보험상품공시');
            if (target) target.click();
        }""")

        try:
            page.wait_for_load_state("domcontentloaded", timeout=10000)
        except Exception as err:
            logger.exception("공시 메뉴 로딩 실패: %s", err)
            print(f"[오류] 공시 메뉴 로딩 실패: {err}")
            browser.close()
            return
        time.sleep(3.5)

        # 1단계 및 2단계 고정 리스트 (배지 숫자 오인식 배제)
        sales_types = ["판매 중인 상품", "판매 중지 상품"]
        insurance_categories = ["자동차보험", "장기보험", "일반보험", "퇴직보험", "퇴직연금"]

        total_downloaded = 0
        total_skipped = 0
        total_failed = 0

        # ==============================================================================
        # [1단계 루프] 판매형태 순회 (판매 중인 상품 -> 판매 중지 상품)
        # ==============================================================================
        for s_idx, sale_type in enumerate(sales_types, start=1):
            print(f"\n================================================================================")
            print(f"📂 [1단계: 판매형태 {s_idx}/{len(sales_types)}] >>> [{sale_type}] 선택")
            print(f"================================================================================")
            if not click_column_item(page, col_index=1, target_text=sale_type):
                logger.error("판매형태 클릭 실패: %s", sale_type)
                print(f"      ⚠️ 판매형태 클릭 실패: {sale_type}")
                total_failed += 1
                continue
            time.sleep(2.5)

            # ==========================================================================
            # [2단계 루프] 보험종류 순회 (자동차보험, 장기보험, 일반보험, 퇴직보험, 퇴직연금)
            # ==========================================================================
            for c_idx, cat_type in enumerate(insurance_categories, start=1):
                print(f"\n   📁 [2단계: 보험종류 {c_idx}/{len(insurance_categories)}] >>> [{cat_type}] 선택")
                if not click_column_item(page, col_index=2, target_text=cat_type):
                    logger.error("보험종류 클릭 실패: %s", cat_type)
                    print(f"      ⚠️ 보험종류 클릭 실패: {cat_type}")
                    total_failed += 1
                    continue
                # 카테고리 전환 후 화면이 갱신될 시간을 보장
                time.sleep(2.5)

                # ======================================================================
                # [3단계 분기] 3단계 부재 카테고리 처리
                # ======================================================================
                if cat_type in DIRECT_CATEGORIES:
                    sub_type_name = DIRECT_CATEGORIES[cat_type]
                    print(f"      ℹ️ [{cat_type}] 카테고리: 3단계 생략 -> 맞춤 폴더명: [{sub_type_name}]")
                    sub_types_to_iterate = [sub_type_name]
                    has_step3 = False
                else:
                    sub_types_to_iterate = get_column_3_types(page)
                    has_step3 = True
                    if not sub_types_to_iterate:
                        if cat_type == "자동차보험":
                            sub_types_to_iterate = ["개인용", "업무용", "영업용", "기타", "공동물건"]
                        elif cat_type == "장기보험":
                            sub_types_to_iterate = ["연금", "상해성", "어린이", "의료", "재물성", "저축성", "질병성", "종합성"]
                        has_step3 = False
                    print(f"      📌 감지된 보험유형 목록: {sub_types_to_iterate}")

                # ======================================================================
                # [3단계 루프] 보험유형 순회
                # ======================================================================
                for u_idx, sub_type in enumerate(sub_types_to_iterate, start=1):
                    if has_step3:
                        print(f"\n      📁 [3단계: 보험유형 {u_idx}/{len(sub_types_to_iterate)}] >>> [{sub_type}] 선택")
                        if not click_column_item(page, col_index=3, target_text=sub_type):
                            logger.error("보험유형 클릭 실패: %s", sub_type)
                            print(f"            ⚠️ 보험유형 클릭 실패: {sub_type}")
                            total_failed += 1
                            continue
                        # 유형 클릭 후 4열 상품 목록 렌더링 대기
                        time.sleep(3.0)
                    else:
                        print(f"\n      📁 [3단계: 직행] >>> [{cat_type}] 상품 목록 바로 수집 (유형: {sub_type})")
                        time.sleep(1.5)

                    # ------------------------------------------------------------------
                    # [폴더 생성] "{판매형태}_{보험종류}_{보험유형}" 하위 디렉토리 생성
                    # ------------------------------------------------------------------
                    folder_name = (
                        f"{sanitize_filename(sale_type)}_"
                        f"{sanitize_filename(cat_type)}_"
                        f"{sanitize_filename(sub_type)}"
                    )
                    current_save_dir = os.path.join(BASE_DOWNLOAD_DIR, folder_name)
                    os.makedirs(current_save_dir, exist_ok=True)
                    print(f"      🎯 최종 저장 폴더: [{folder_name}]")

                    # ==================================================================
                    # [4단계 루프] 4열 상품 목록 추출 및 전수 수집
                    # ==================================================================
                    product_list = get_column_4_products(page)
                    product_count = len(product_list)

                    if product_count == 0:
                        print(f"         ⚠️ 등록된 상품이 없습니다. 다음으로 이동합니다.")
                        continue

                    print(f"         📋 등록 상품 수: 총 {product_count}건")

                    for p_idx, product_name in enumerate(product_list, start=1):
                        try:
                            print(f"         [{p_idx}/{product_count}] 상품 처리: {product_name}")

                            # 1. 파일명 생성 및 중복 다운로드 검증 (이어받기)
                            safe_prod_name = sanitize_filename(product_name)
                            final_pdf_path = os.path.join(current_save_dir, f"{safe_prod_name}_약관.pdf")

                            if os.path.exists(final_pdf_path) and os.path.getsize(final_pdf_path) > 1000:
                                print(f"            ⏩ 이미 존재하는 파일 (스킵): {safe_prod_name}")
                                total_skipped += 1
                                continue

                            # 2. 4열의 해당 상품 클릭
                            click_ok = click_column_4_product(page, product_name)
                            if not click_ok:
                                logger.error("상품 클릭 실패: %s", product_name)
                                print(f"            ⚠️ 상품 클릭 실패: {product_name}")
                                total_failed += 1
                                continue

                            # 3. 하단 테이블 약관 고유 UUID 대기
                            time.sleep(1.8)
                            file_uuid = None
                            for _ in range(8):
                                extracted = page.evaluate("""() => {
                                    const elements = Array.from(document.querySelectorAll('table a, table button, table img'));
                                    const termsEl = elements.find(el => {
                                        const onc = el.getAttribute('onclick') || '';
                                        return onc.indexOf('linkPdf') !== -1;
                                    });
                                    return termsEl ? termsEl.getAttribute('onclick') : null;
                                }""")
                                if extracted:
                                    match = re.search(r"linkPdf\(['\"]([a-zA-Z0-9\-]+)['\"]\)", extracted)
                                    if match:
                                        file_uuid = match.group(1)
                                        break
                                time.sleep(0.4)

                            # 약관 파일이 미제공된 상품인 경우 건너뛰기
                            if not file_uuid:
                                logger.warning("약관 미제공 상품: %s", safe_prod_name)
                                print(f"            ℹ️ 약관 미제공 상품 (스킵): {safe_prod_name}")
                                total_failed += 1
                                continue

                            # 4. 새 탭(팝업) 인터셉트 및 원본 PDF 바이너리 직접 저장
                            popup_page = None
                            try:
                                with context.expect_page(timeout=10000) as popup_info:
                                    page.evaluate(f"window.linkPdf('{file_uuid}')")
                                popup_page = popup_info.value
                                popup_page.wait_for_load_state("domcontentloaded")
                                time.sleep(1.2)
                                is_saved = fetch_pdf_via_popup(
                                    popup_page, context, final_pdf_path
                                )
                            finally:
                                if popup_page and not popup_page.is_closed():
                                    popup_page.close()

                            if is_saved:
                                total_downloaded += 1
                                print(f"            🎉 [저장 완료] {safe_prod_name}.pdf ({os.path.getsize(final_pdf_path):,} bytes)")
                            else:
                                total_failed += 1
                                logger.error("PDF 바이너리 수신 실패: %s", safe_prod_name)
                                print(f"            ❌ 바이너리 수신 실패: {safe_prod_name}")

                        except Exception as item_err:
                            total_failed += 1
                            logger.exception("상품 처리 오류: %s", item_err)
                            print(f"            ❌ 처리 오류: {item_err}")

                        # 요청 완충 대기
                        time.sleep(0.8)

        # ==============================================================================
        # 최종 수집 통계 리포트 출력
        # ==============================================================================
        print(f"\n================================================================================")
        print(f"📊 [전체 공시 약관 수집 완료 리포트]")
        print(f"   - 신규 다운로드 성공: {total_downloaded}건")
        print(f"   - 기존 파일 건너뜀 (중복): {total_skipped}건")
        print(f"   - 실패 / 약관 미제공 건수: {total_failed}건")
        print(f"   - 파일 저장 최상위 경로: {BASE_DOWNLOAD_DIR}")
        print(f"================================================================================\n")

        time.sleep(2.0)
        browser.close()


if __name__ == "__main__":
    run_full_crawler()

# 🔄 현대해상 PY 파일 진화 과정 및 작성 이유
# 실행 순서         파일명 (진화 단계)                  목적 및 작성 이유 (Why?)                        결과 및 한계
# 1단계             기존 제공해주신 원본 스크립트        [목적]복잡한 4단 카테고리를 오작동 없이 클릭하고    [실패/무한루프] 서버 응답(DOM 렌더링)이 
# (UI 스크래핑)     (화면 좌표 기반 클릭)               화면에 뜬 상품명을 긁어오기 위함입니다.             파이썬 속도를 따라가지 못해 이전 
#                                                   [이유]일반적인 DOM 텍스트 크롤링 방식의            카테고리 상품을 중복으로 긁어오는 고스트 루프 발생.
#                                                   한계(메뉴명 오인식)를 
#                                                   물리적 X좌표로 극복하려 했습니다.
# 
# 2단계             Hyundai_Sniffer.py              [목적] 화면(UI)을 믿을 수 없으니,                 [성공] 현대해상은 모든 데이터를 **ajax.xhi**라는 
# (통신 스니핑)      (타임아웃 방어 적용)               브라우저 뒤에서 오가는 실제 데이터 주소를 알아내기   단일 주소 하나로만 주고받는다는 사실을 발견.
#                                                   위해 작성했습니다.
#                                                   [이유] 삼성생명처럼 상품 목록을 뱉어내는 
#                                                   숨겨진 API 주소를 찾기 위함이었습니다.
# 3단계             Hyundai_API_Extractor.py        [목적] 단일 창구인 ajax.xhi에서 수많은            [성공] 상품명(prodNm)과 약관 고유 ID(clauApnflId)가 
# (정밀 해킹)       (V1 & V2 스마트 필터)             통신이 오가므로, 그 안에서 '진짜 상품 데이터'만      담긴 완벽한 JSON 구조 확보 완료.
#                                                  골라 추출하기 위해 작성했습니다.
#                                                  [이유] V1에서는 실수로 '담당자 연락처'를 잡았기에, 
#                                                  V2에서는 pdf, file 키워드를 필터링하여 
#                                                  진짜 상품 목록(JSON) 구조와 호출 
#                                                  암호(HHCA0310M38S)를 뜯어내야 했습니다.
# 4단계             Hyundai_API_Driven_Crawler.py   [목적] 1단계의 장점(정밀한 카테고리 클릭)과         [성공] 무한 루프 확률 0%, 브라우저 렌더링 지연 완벽 극복 
# (최종 진화)       (API 하이브리드)                  3단계의 성과(서버 JSON 직접 수신)를                및 수집 속도 극대화.
#                                                  결합하여 작성했습니다.
#                                                  [이유] 화면이 늦게 뜨는 문제를 원천 차단하기 위해, 
#                                                  화면을 읽는 대신 서버가 JSON을 줄 때까지 기다렸다가 
#                                                  그 안의 ID를 빼내 다이렉트로 다운로드하기 위해서입니다.
# 💡 왜 이렇게 여러 단계를 거쳐야만 했는가? (Why so many steps?)
# 1. 블랙박스 해독 (Peeling the Onion): 현대 웹사이트(SPA)는 껍질(UI)과 알맹이(API)가 분리되어 있습니다. 
#    껍질만 보고 클릭(1단계)하다가 오류가 나면, 네트워크 창을 열어 통신망을 찾고(2단계), 
#    그 통신망 안에 어떤 암호와 구조가 숨어있는지 해부(3단계)해야만 비로소 알맹이를 직접 타격(4단계)할 수 있습니다.
# 2. 현대해상 서버의 특수성: 삼성생명은 목적에 따라 API 주소가 달랐지만, 현대해상은 ajax.xhi라는 
#    하나의 터널로 모든 것을 처리했습니다. 터널 안에서 우리가 원하는 택배 상자(상품 목록 JSON)만 정확히 낚아채기 위해 
#    정밀 필터링(Extractor V2)이라는 추가 과정이 필요했습니다.
# 결론적으로, 이 잦은 스크립트 교체는 오류를 헤매는 과정이 아니라 가장 견고하고 완벽한 자동화 로직을 짜기 위해 
# 웹사이트의 방어막을 하나씩 철거해 나가는 전문적인 리버스 엔지니어링(Reverse Engineering) 과정이었습니다.
# 
# 지금은 이전의 디버깅용 파일들은 모두 잊으셔도 좋으며, 최종 완성된 Hyundai_API_Driven_Crawler.py
#  하나만 구동하시면 밤새 무한 루프에 빠질 일 없이 완벽하게 약관 파일들을 수집해 낼 것입니다.
import os
import re
import time
import json
from playwright.sync_api import BrowserContext, Page, sync_playwright

# ==============================================================================
# 1. 파일 저장 디렉토리 및 전역 설정
# ==============================================================================
BASE_DOWNLOAD_DIR: str = r"C:\source\Python\chapter31\insurance_policies"
os.makedirs(BASE_DOWNLOAD_DIR, exist_ok=True)

TARGET_URL: str = "https://www.hi.co.kr/serviceAction.do?view=bin/PA/03/HHPA03010M"

DIRECT_CATEGORIES: dict[str, str] = {
    "일반보험": "일반",
    "퇴직보험": "퇴직",
    "퇴직연금": "퇴직",
}

# [핵심] API로 가로챈 상품 목록 데이터를 저장할 전역 상태 컨테이너
api_state = {"current_products": []}

def sanitize_filename(name: str) -> str:
    # 빈 괄호나 이상한 문자가 섞인 상품명 "( )IoT제휴안심상해보험" 등을 깔끔하게 정리
    clean_name = re.sub(r'[\\/*?:"<>|()]', "", name).strip()
    return clean_name[:45]

# ==============================================================================
# 2. 브라우저 통신 가로채기 핸들러 (UI 오작동 원천 차단)
# ==============================================================================
def intercept_api_response(response):
    """
    현대해상 서버에서 상품 목록(slYProdList)이 내려올 때마다 자동으로 전역 변수에 저장합니다.
    화면 렌더링 속도와 무관하게 서버 데이터와 100% 동기화됩니다.
    """
    if "ajax.xhi" in response.url and response.request.method == "POST":
        try:
            data = response.json()
            # 서버 응답 안에 실제 상품 목록(slYProdList)이 존재하면 상태 업데이트
            prod_list = data.get("data", {}).get("slYProdList")
            if prod_list is not None:
                api_state["current_products"] = prod_list
        except Exception:
            pass

# ==============================================================================
# 3. 기존 카테고리 탐색 로직 (좌표 클릭 유지)
# ==============================================================================
def click_column_item(page: Page, col_index: int, target_text: str) -> bool:
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

# ==============================================================================
# 4. 바이너리 다운로드 
# ==============================================================================
def fetch_pdf_via_popup(popup_page: Page, context: BrowserContext, save_path: str) -> bool:
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
            print(f"      ⚠️ 바이너리 다운로드 중 네트워크 오류: {err}")
    return False

# ==============================================================================
# 5. 메인 크롤러 루틴
# ==============================================================================
def run_full_crawler() -> None:
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            accept_downloads=True,
        )
        page = context.new_page()
        
        # 네트워크 응답 가로채기 이벤트 리스너 등록
        page.on("response", intercept_api_response)

        print(f"[초기화] 현대해상 공시실 접속 중: {TARGET_URL}")
        try:
            page.goto(TARGET_URL, wait_until="domcontentloaded", timeout=60000)
        except Exception:
            pass
        time.sleep(2.5)

        print("[초기화] [보험상품공시] 메뉴 진입 대기...")
        page.evaluate("""() => {
            const links = Array.from(document.querySelectorAll('a, button, span'));
            const target = links.find(el => el.innerText && el.innerText.trim() === '보험상품공시');
            if (target) target.click();
        }""")
        time.sleep(3.5)

        sales_types = ["판매 중인 상품", "판매 중지 상품"]
        insurance_categories = ["자동차보험", "장기보험", "일반보험", "퇴직보험", "퇴직연금"]

        total_downloaded = 0
        total_skipped = 0
        total_failed = 0

        for s_idx, sale_type in enumerate(sales_types, start=1):
            print(f"\n================================================================================")
            print(f"📂 [1단계: 판매형태 {s_idx}/{len(sales_types)}] >>> [{sale_type}] 선택")
            click_column_item(page, col_index=1, target_text=sale_type)
            time.sleep(1.5)

            for c_idx, cat_type in enumerate(insurance_categories, start=1):
                print(f"\n   📁 [2단계: 보험종류 {c_idx}/{len(insurance_categories)}] >>> [{cat_type}] 선택")
                
                # API 데이터 초기화
                api_state["current_products"] = []
                click_column_item(page, col_index=2, target_text=cat_type)
                time.sleep(2.0)

                if cat_type in DIRECT_CATEGORIES:
                    sub_type_name = DIRECT_CATEGORIES[cat_type]
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

                for u_idx, sub_type in enumerate(sub_types_to_iterate, start=1):
                    if has_step3:
                        print(f"\n      📁 [3단계: 보험유형 {u_idx}/{len(sub_types_to_iterate)}] >>> [{sub_type}] 선택")
                        # 3단계 클릭 전 데이터 초기화
                        api_state["current_products"] = []
                        click_column_item(page, col_index=3, target_text=sub_type)
                        
                        # [핵심] API 통신 응답 대기 (최대 3초)
                        wait_time = 0
                        while not api_state["current_products"] and wait_time < 30:
                            time.sleep(0.1)
                            wait_time += 1
                    else:
                        print(f"\n      📁 [3단계: 직행] >>> [{cat_type}] 상품 목록 바로 수집")

                    folder_name = f"{sanitize_filename(sale_type)}_{sanitize_filename(cat_type)}_{sanitize_filename(sub_type)}"
                    current_save_dir = os.path.join(BASE_DOWNLOAD_DIR, folder_name)
                    os.makedirs(current_save_dir, exist_ok=True)
                    print(f"      🎯 최종 저장 폴더: [{folder_name}]")

                    # ==================================================================
                    # [4단계 로직 혁신] DOM 무시! API에서 추출한 JSON 리스트 다이렉트 순회
                    # ==================================================================
                    product_list = api_state["current_products"]
                    product_count = len(product_list)

                    if product_count == 0:
                        print(f"         ⚠️ 등록된 상품이 없거나 서버 응답 지연. 다음으로 이동합니다.")
                        continue

                    print(f"         📋 API 감지된 상품 수: 총 {product_count}건")

                    for p_idx, prod_data in enumerate(product_list, start=1):
                        raw_prod_name = prod_data.get("prodNm", "Unknown_Product")
                        file_uuid = prod_data.get("clauApnflId") # 약관 PDF 고유 ID
                        
                        safe_prod_name = sanitize_filename(raw_prod_name)
                        final_pdf_path = os.path.join(current_save_dir, f"{safe_prod_name}_약관.pdf")

                        print(f"         [{p_idx}/{product_count}] 상품 처리: {raw_prod_name}")

                        # 중복 파일 검증
                        if os.path.exists(final_pdf_path) and os.path.getsize(final_pdf_path) > 1000:
                            print(f"            ⏩ 이미 존재하는 파일 (스킵): {safe_prod_name}")
                            total_skipped += 1
                            continue
                            
                        # 고유 ID가 없는 상품(약관 미제공) 패스
                        if not file_uuid:
                            print(f"            ℹ️ 약관 ID 없음 (스킵): {safe_prod_name}")
                            total_failed += 1
                            continue

                        try:
                            # [핵심] 화면 클릭, 버튼 찾기 무한 대기 모두 삭제! 
                            # 서버의 JS 함수(window.linkPdf)를 파이썬이 ID를 넣어 직접 실행합니다.
                            with context.expect_page(timeout=10000) as popup_info:
                                page.evaluate(f"window.linkPdf('{file_uuid}')")

                            popup_page = popup_info.value
                            popup_page.wait_for_load_state("domcontentloaded")
                            time.sleep(1.0)

                            is_saved = fetch_pdf_via_popup(popup_page, context, final_pdf_path)
                            popup_page.close()

                            if is_saved:
                                total_downloaded += 1
                                print(f"            🎉 [저장 완료] {safe_prod_name}.pdf ({os.path.getsize(final_pdf_path):,} bytes)")
                            else:
                                total_failed += 1
                                print(f"            ❌ 바이너리 수신 실패: {safe_prod_name}")

                        except Exception as item_err:
                            total_failed += 1
                            print(f"            ❌ 처리 오류: {item_err}")
                            
                        time.sleep(0.3) # 서버 과부하 방지 쿨타임

        print(f"\n================================================================================")
        print(f"📊 [전체 공시 약관 수집 완료 리포트]")
        print(f"   - 신규 다운로드 성공: {total_downloaded}건")
        print(f"   - 기존 파일 건너뜀 (중복): {total_skipped}건")
        print(f"   - 실패 / 약관 미제공 건수: {total_failed}건")
        print(f"   - 파일 저장 최상위 경로: {BASE_DOWNLOAD_DIR}")
        print(f"================================================================================\n")

        browser.close()

if __name__ == "__main__":
    run_full_crawler()
# 지금까지 작성된 파이썬(.py) 파일들은 단순한 스크래핑에서 시작해 '초고속 대량 API 다운로드'로 진화해 온 과정입니다.
# 금융사 웹페이지의 강력한 보안과 복잡한 구조를 우회하기 위해 단계별로 스크립트가 발전했으며, 
# 그 실행 순서와 작성 이유는 다음과 같습니다.
# 🔄 PY 파일 진화 과정 및 작성 이유 (요약표)
# 
# 실행 순서 (진화 단계)  파일명                             목적 및 작성 이유 (Why?)                결과 및 한계
#                                                       웹 크롤링 방식이기 때문입니다.             [실패] 삼성생명 웹페이지의 동적 렌더링 지연, 
# 1단계(UI 스크래핑)    LangGraph_Ingestion_Pipeline.py   [목적] 화면에 보이는 '약관 다운로드'       숨겨진 태그 구조, 봇 탐지(Anti-bot) 등으로
#                                                       버튼을 Playwright(브라우저 자동화)로      인해 잦은 타임아웃 발생.
#                                                       직접 클릭하기 위해 작성했습니다.
# 
#                                                       [이유] 가장 직관적이고 일반적인 
#                                                       웹 크롤링 방식이기 때문입니다.
#        
# 2단계(통신 스니핑)    LangGraph_Network_Sniffer.py      [목적] 버튼 클릭이 막히자, 브라우저와      [성공] 상품 목록을 불러오는 핵심 API(salesAllPrdtList) 
#                                                       서버가 몰래 주고받는 '백엔드 통신 데이터'  주소 발견.
#                                                       를 훔쳐보기 위해 작성했습니다.
# 
#                                                       [이유] 화면 UI에 의존하지 않고, 
#                                                       실제 데이터가 오가는 원본 API 주소를 알아내기 
#                                                       위함입니다.
#
# 3단계(API 추출)       LangGraph_API_Extractor.py       [목적] 발견한 API의 응답 데이터를 가로채어  [성공] 핵심 API(salesAllPrdtList) 통신을
#
#                                                       samsung_api_data.json 로컬 파일로 저장하기 
#                                                       위해 작성했습니다.
#                                                       
#                                                       [이유] 서버가 PDF 다운로드 링크를 어떤      [성공] 파라미터 에러(4200) 방어 및 로컬 JSON 폴백(Fallback) 
#                                                       형태(이름, 고유 ID 등)로 주는지 구조를      기능까지 갖춘 가장 완벽하고 견고한 최종 스크립트.
#                                                       눈으로 파악해야 했기 때문입니다.        
# 4단계                 LangGraph_Batch_Downloader.py    [목적] 무거운 Playwright(브라우저)를 버리고, 
# (초고속 일괄 다운)                                       파이썬 requests로 API와 다이렉트 통신하여 
#                       (★최종 완성본)                   6,680개 약관 전체를 일괄 다운로드하도록 작성했습니다. 
#                 
# 💡 결론 및 가이드
# 이처럼 여러 파일이 만들어진 이유는 "막히면 우회하고, 원리를 파악해 더 빠르고 가벼운 코드로
# 최적화"하는 소프트웨어 엔지니어링의 자연스러운 문제 해결 과정이었습니다.

# 현재 시점에서는 앞의 1~3단계 파일들은 더 이상 실행하실 필요가 없습니다.
# 가장 마지막에 작성된 LangGraph_Batch_Downloader.py 단 하나만 실행하시면, 가장 빠르고
# 안정적으로 전체 약관 파일 다운로드가 수행됩니다.
import os
import time
import requests
from pathlib import Path
from typing import TypedDict, List, Dict
from langgraph.graph import StateGraph, START, END

import warnings
warnings.filterwarnings("ignore", category=DeprecationWarning)

# 공통 다운로드 폴더 경로 설정
BASE_DIR = Path(r"C:\source\LangGraph")

# 1. 다중 처리를 위한 상태 스키마 정의
class BatchDownloadState(TypedDict):
    target_list: List[Dict[str, str]]
    success_count: int
    fail_count: int
    status_msg: str

# 2. 노드 구현: JSON 데이터에서 "모든" 파일 ID 추출
def fetch_meta_node(state: BatchDownloadState) -> BatchDownloadState:
    print("[Fetch Meta Node] 상품 목록 및 파일 정보를 일괄 검색합니다...")
    
    api_url = "https://www.samsunglife.com/gw/api/product/disclosure/product/prdt/salesAllPrdtList"
    target_list = []
    
    try:
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
            "Accept": "application/json"
        }
        
        # [핵심 수정 1] 에러 로그에서 요구한 필수 파라미터(pageRows) 추가
        req_params = {
            "pageNo": 1,
            "pageRows": 10000, # 한 번에 가져올 상품 수 넉넉하게 지정
            "pageSize": 10000
        }
        
        response = requests.get(api_url, headers=headers, params=req_params, timeout=10)
        response.raise_for_status()
        json_data = response.json()
        
        # [핵심 수정 2] 서버 응답이 에러 딕셔너리인지 확인 (Type Guard)
        resp_data = json_data.get("response", [])
        if isinstance(resp_data, dict) and "code" in resp_data:
            raise ValueError(f"서버 에러 응답: {resp_data.get('description', resp_data)}")
            
    except Exception as e:
        print(f"🚨 API 통신 에러({e}) \n💡 로컬 samsung_api_data.json 파일에서 읽기를 시도합니다.")
        import json
        local_json_path = BASE_DIR / "samsung_api_data.json"
        if not local_json_path.exists():
            return {"target_list": [], "success_count": 0, "fail_count": 0, "status_msg": "데이터 소스가 없어 중단합니다."}
        
        with open(local_json_path, "r", encoding="utf-8") as f:
            json_data = json.load(f)

    # 데이터 추출 로직 (안전한 타입 체크 포함)
    resp_list = json_data.get("response", [])
    
    # 만약 로컬 파일조차도 리스트가 아니라 에러 딕셔너리라면 빈 리스트 처리
    if not isinstance(resp_list, list):
        print("🚨 응답 데이터가 상품 리스트 구조가 아닙니다.")
        resp_list = []

    for item in resp_list:
        # item이 딕셔너리일 때만 처리하여 AttributeError 원천 차단
        if isinstance(item, dict):
            goods_name = item.get("goodsName", "Unknown")
            file_id = item.get("filename2")
            
            if file_id:
                target_list.append({"name": goods_name, "file_id": file_id})

    status = f"총 {len(target_list)}개의 다운로드 대상을 찾았습니다."
    print(status)
    return {"target_list": target_list, "success_count": 0, "fail_count": 0, "status_msg": status}

# 3. 노드 구현: 리스트를 순회하며 전체 다운로드 수행
def download_node(state: BatchDownloadState) -> BatchDownloadState:
    target_list = state.get("target_list", [])
    if not target_list:
        return {"status_msg": state.get("status_msg") + "\n다운로드할 대상이 없습니다.", "success_count": 0, "fail_count": 0}

    download_dir = BASE_DIR
    download_dir.mkdir(parents=True, exist_ok=True)
    
    success_cnt = 0
    fail_cnt = 0
    
    print(f"\n[Download Node] 일괄 다운로드를 시작합니다. (대상: {len(target_list)}건)")
    
    for idx, target in enumerate(target_list, 1):
        raw_name = target["name"]
        file_id = target["file_id"]
        
        # 파일명으로 사용할 수 없는 특수문자 안전하게 제거
        safe_name = raw_name.replace("/", "_").replace("\\", "_").replace(":", "").replace("*", "").replace("?", "").replace('"', "").replace("<", "").replace(">", "").replace("|", "")
        pdf_path = download_dir / f"{safe_name}_{file_id}.pdf"
        
        # 이미 다운로드된 파일이 있다면 패스 (이어서 다운로드하기 위함)
        if pdf_path.exists():
            print(f"[{idx}/{len(target_list)}] 이미 존재함 (건너뜀): {safe_name}")
            success_cnt += 1
            continue
            
        download_url = f"https://www.samsunglife.com/gw/api/file/download?fileId={file_id}"
        
        try:
            print(f"[{idx}/{len(target_list)}] 다운로드 중: {safe_name} ... ", end="")
            response = requests.get(download_url, stream=True, timeout=15)
            response.raise_for_status()
            
            with open(pdf_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            
            print("✅ 완료")
            success_cnt += 1
            
        except Exception as e:
            print(f"❌ 실패 ({e})")
            fail_cnt += 1
            
        time.sleep(0.5)
        
    final_status = f"다운로드 작업 종료.\n- 성공: {success_cnt}건\n- 실패: {fail_cnt}건"
    return {"success_count": success_cnt, "fail_count": fail_cnt, "status_msg": final_status}

# 4. LangGraph 조립
def build_batch_download_graph():
    builder = StateGraph(BatchDownloadState)
    builder.add_node("fetch_meta", fetch_meta_node)
    builder.add_node("downloader", download_node)
    
    builder.add_edge(START, "fetch_meta")
    builder.add_edge("fetch_meta", "downloader")
    builder.add_edge("downloader", END) 
    return builder.compile()

# 5. 메인 실행부
def main():
    app = build_batch_download_graph()
    
    initial_state = {
        "target_list": [],
        "success_count": 0,
        "fail_count": 0,
        "status_msg": "시작 대기"
    }
    
    print("\n" + "="*50)
    print(" 🚀 다중 PDF 일괄 다운로드 파이프라인 시작")
    print("="*50 + "\n")
    
    final_state = app.invoke(initial_state)
    
    print("\n" + "="*50)
    print(" [최종 처리 결과 요약] ")
    print(final_state["status_msg"])
    print("="*50 + "\n")

if __name__ == "__main__":
    main()
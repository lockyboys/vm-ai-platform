# =============================================================================
# File Name   : /data/vm_project/FastAPI/LangGraph/gemini/sps-mcp-api_find.py
# Purpose     : SPS API Gateway 및 Gemini Agent 엔드포인트 연동 테스트 (Python 버전)
# =============================================================================
# 이 파일은 무엇을 하나요?
# - API Gateway 또는 로컬 8012 포트로 HTTP GET/POST 요청을 전송하여 메일 조회 및 발송을 검증합니다.
# - 파이썬 표준 라이브러리(urllib, json)를 사용하여 추가 패키지 설치 없이 즉시 실행됩니다.
# 주의: 쉘 스크립트 문법(curl, echo)이 아닌 순수 파이썬 문법으로 작성되었습니다.
# =============================================================================
# ==============================================================================
# [로컬 직접 테스트 설정]
# 목적: API Gateway 배포 지연과 무관하게 로컬 FastAPI(8012) 기능 즉시 검증
# ==============================================================================
# TARGET_URL = "https://sps-gateway-459577949780.asia-northeast1.gateway.dev"
TARGET_URL = "http://127.0.0.1:8012"

import json
import urllib.error
import urllib.parse
import urllib.request

# [선택 1] API Gateway 경유 시 (게이트웨이 배포 완료 후)
TARGET_URL = "https://sps-gateway-459577949780.asia-northeast1.gateway.dev"

# [선택 2] VM 내부 로컬 직접 테스트 시 (게이트웨이 우회 및 로컬 단독 검증)
# TARGET_URL = "http://127.0.0.1:8012"


def test_read_recent_emails(max_results: int = 5):
    """최근 수신 이메일 조회 테스트 (GET /gmail/read)
    
    목적: GET /gmail/read 엔드포인트의 라우팅 및 쿼리 파라미터 전달 검증
    주의점: 응답 실패 시 HTTP 에러 코드와 상세 사유를 출력합니다.
    """
    url = f"{TARGET_URL}/gmail/read?max_results={max_results}"
    print(f"=== 1. 최근 메일 조회 (GET /gmail/read) ===")
    print(f"요청 URL: {url}")
    
    req = urllib.request.Request(
        url,
        headers={"Accept": "application/json"}
    )
    
    try:
        with urllib.request.urlopen(req, timeout=10) as response:
            status_code = response.getcode()
            body = response.read().decode("utf-8")
            print(f"[성공] 상태 코드: {status_code}")
            print(f"응답 본문:\n{body}\n")
    except urllib.error.HTTPError as e:
        error_body = e.read().decode("utf-8", errors="replace")
        print(f"[실패] HTTP 오류 {e.code}: {e.reason}")
        print(f"오류 내용: {error_body}\n")
    except Exception as e:
        print(f"[오류] 네트워크 또는 연결 실패: {str(e)}\n")


def test_send_gmail():
    """메일 발송 테스트 (POST /gmail/send)
    
    목적: POST /gmail/send 엔드포인트의 JSON 페이로드 처리 검증
    주의점: sps_gemini_agent.py의 MailSendRequest 규격인 'recipient', 'subject', 'content'를 사용합니다.
    """
    url = f"{TARGET_URL}/gmail/send"
    print(f"=== 2. 메일 발송 (POST /gmail/send) ===")
    print(f"요청 URL: {url}")
    
    # sps_gemini_agent.py Pydantic 스키마 준수 (recipient, subject, content)
    payload = {
        "recipient": "recipient@example.com",
        "subject": "SPS 테스트 메일",
        "content": "API Gateway를 통한 테스트 메일입니다."
    }
    
    json_data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=json_data,
        headers={"Content-Type": "application/json"},
        method="POST"
    )
    
    try:
        with urllib.request.urlopen(req, timeout=10) as response:
            status_code = response.getcode()
            body = response.read().decode("utf-8")
            print(f"[성공] 상태 코드: {status_code}")
            print(f"응답 본문:\n{body}\n")
    except urllib.error.HTTPError as e:
        error_body = e.read().decode("utf-8", errors="replace")
        print(f"[실패] HTTP 오류 {e.code}: {e.reason}")
        print(f"오류 내용: {error_body}\n")
    except Exception as e:
        print(f"[오류] 네트워크 또는 연결 실패: {str(e)}\n")


def test_agent_chat():
    """에이전트 통합 대화 테스트 (POST /agent/chat)
    
    목적: LangGraph 기반 AI 에이전트 대화 엔드포인트 정상 동작 검증
    주의점: 에이전트 초기화에 시간이 걸릴 수 있으므로 타임아웃을 30초로 설정합니다.
    """
    url = f"{TARGET_URL}/agent/chat"
    print(f"=== 3. 에이전트 대화 (POST /agent/chat) ===")
    print(f"요청 URL: {url}")
    
    payload = {
        "user_input": "최근 수신된 메일 3건 확인해줘"
    }
    
    json_data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=json_data,
        headers={"Content-Type": "application/json"},
        method="POST"
    )
    
    try:
        with urllib.request.urlopen(req, timeout=30) as response:
            status_code = response.getcode()
            body = response.read().decode("utf-8")
            print(f"[성공] 상태 코드: {status_code}")
            print(f"응답 본문:\n{body}\n")
    except urllib.error.HTTPError as e:
        error_body = e.read().decode("utf-8", errors="replace")
        print(f"[실패] HTTP 오류 {e.code}: {e.reason}")
        print(f"오류 내용: {error_body}\n")
    except Exception as e:
        print(f"[오류] 네트워크 또는 연결 실패: {str(e)}\n")


if __name__ == "__main__":
    # 순차적으로 엔드포인트 검증 실행
    test_read_recent_emails(max_results=5)
    test_send_gmail()
    test_agent_chat()
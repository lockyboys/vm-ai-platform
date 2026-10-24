# 서비스명									역할																				포트
# fastapi-insurance-rag.service			  FastAPI + 다중 PDF RAG + Tavily + Google Grounding + 토큰 사용량 추적 통합 서버.		  8003
# sudo /data/vm_project/venv/bin/python /data/vm_project/FastAPI/LangGraph/agent_cli.py "너는 누구니??"
"""서버 터미널에서 운영 8003 API에 질문한다. 직접 실행·--query·--dry-run을 지원한다."""
import argparse
import getpass
import json
import os
import sys
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from config import AGENT_CLI
from common.common_function import normalize_required_text

def make_payload(query):
    """빈 질문·과도한 길이를 네트워크 호출 전에 거부하고 독립된 요청 ID를 생성한다."""
    query = normalize_required_text(query, "질문")
    if len(query) > AGENT_CLI["max_query_length"]:
        raise ValueError("질문은 12000자 이내로 입력하세요.")
    request_id = "cli-" + uuid4().hex
    return {"query": query, "thread_id": request_id, "request_id": request_id,
            "calendar_results": [], "gmail_results": []}

def get_token(user):
    """기존 환경 토큰을 우선 사용하고, 없으면 서버의 보호 파일로 로컬 사용자 토큰을 발급한다."""
    token = os.getenv("SPS_AGENT_ACCESS_TOKEN", "").strip()
    if token:
        return token
    from dotenv import dotenv_values
    from common.auth import CommonAuth
    values = dotenv_values(AGENT_CLI["auth_env_file"])
    key = values.get("SPS_AUTH_JWT_SECRET_KEY")
    if not key:
        raise RuntimeError("인증키를 읽을 수 없습니다. SPS_AGENT_ACCESS_TOKEN을 설정하거나 보호 파일 읽기 권한을 확인하세요.")
    lifetime = AGENT_CLI["token_lifetime_seconds"]
    return CommonAuth(secret_key=key, jwt_expire_seconds=lifetime,
                      refresh_token_expire_seconds=lifetime).issue_access_token(user)

def ask(payload, token):
    """Bearer 인증으로 실제 API를 호출한다. 오류에 토큰이나 원시 응답을 포함하지 않는다."""
    request = Request(AGENT_CLI["endpoint"],
                      data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
                      headers={"Content-Type": "application/json", "Accept": "application/json",
                               "Authorization": "Bearer " + token}, method="POST")
    try:
        with urlopen(request, timeout=AGENT_CLI["timeout_seconds"]) as response:
            result = json.load(response)
    except HTTPError as error:
        raise RuntimeError(f"API HTTP {error.code}: 인증 또는 서비스 상태를 확인하세요.") from None
    except (URLError, TimeoutError, OSError):
        raise RuntimeError("API 연결 실패 또는 응답 시간 초과입니다.") from None
    except (ValueError, UnicodeError):
        raise RuntimeError("API가 올바른 JSON 응답을 반환하지 않았습니다.") from None
    if not isinstance(result, dict) or result.get("status") != "success" or not str(result.get("response") or "").strip():
        raise RuntimeError("API가 정상 답변을 반환하지 않았습니다.")
    return result

def main(argv=None):
    """질문 한 건을 실행한다. dry-run은 인증키 조회·모델 호출·DB 저장을 수행하지 않는다."""
    parser = argparse.ArgumentParser(description="8003 에이전트 질문 테스트")
    # 따옴표로 묶은 질문과 여러 단어를 모두 지원하고 기존 --query 방식도 유지한다.
    parser.add_argument("question", nargs="*", help="명령 뒤에 바로 입력할 질문")
    parser.add_argument("--query", help="생략하면 질문을 입력받습니다.")
    parser.add_argument("--dry-run", action="store_true", help="전송할 질문만 확인합니다.")
    args = parser.parse_args(argv)
    if args.query is not None and args.question:
        parser.error("위치 질문과 --query 중 하나만 사용하세요.")
    if args.question:
        args.query = " ".join(args.question)
    try:
        query = args.query if args.query is not None else input("질문> ")
        payload = make_payload(query)
        if args.dry_run:
            print(json.dumps({"dry_run": True, "endpoint": AGENT_CLI["endpoint"], "payload": payload}, ensure_ascii=False))
            return 0
        # sudo 실행에서도 실제 터미널 사용자의 기억 영역을 사용한다.
        result = ask(payload, get_token(os.getenv("SUDO_USER") or getpass.getuser()))
        print("답변:", result["response"])
        print("요청 ID:", payload["request_id"], "| 저장:", result.get("memory_saved") is True)
        return 0
    except (ValueError, RuntimeError, OSError) as error:
        print("오류:", str(error), file=sys.stderr)
        return 1
    except (EOFError, KeyboardInterrupt):
        print("\n입력을 종료했습니다.", file=sys.stderr)
        return 130

if __name__ == "__main__":
    raise SystemExit(main())

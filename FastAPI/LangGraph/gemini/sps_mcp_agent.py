import os
import argparse
from dotenv import load_dotenv

# .env 파일 로드
load_dotenv()

# CLI 인자 파서 설정 (기본값을 .env 환경변수에서 참조)
parser = argparse.ArgumentParser(description="SPS Gemini Agent")
parser.add_argument(
    "--common-auth-user",
    type=str,
    default=os.getenv("COMMON_AUTH_USER", "jeaje"),
    help="인증 사용자 계정 (기본값: .env의 COMMON_AUTH_USER)"
)
parser.add_argument("--check-mcp", action="store_true", help="MCP 연결 상태만 확인")
args = parser.parse_args()

gemini_api_key = os.getenv("GEMINI_API_KEY")
if not gemini_api_key and not args.check_mcp:
    raise ValueError("GEMINI_API_KEY가 .env 또는 환경 변수에 설정되어 있지 않습니다.")
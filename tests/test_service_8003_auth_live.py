"""기존 8003 배포 서비스 인증을 검증한다. 빈 본문으로 LLM 호출과 저장을 방지한다."""
import json
from urllib.error import HTTPError
from urllib.request import Request, urlopen
from dotenv import dotenv_values
from common.auth import CommonAuth

def _status(token=None):
    # 정상 토큰은 본문 검증(422)까지 도달하고, 누락·변조 토큰은 인증(401)에서 차단돼야 한다.
    headers = {"Content-Type": "application/json"}
    if token is not None:
        headers["Authorization"] = "Bearer " + token
    request = Request("http://127.0.0.1:8003/api/agent/context", data=b"{}", headers=headers)
    try:
        with urlopen(request, timeout=12) as response:
            return response.status
    except HTTPError as error:
        return error.code

def test_missing_token_is_rejected():
    assert _status() == 401

def test_invalid_token_is_rejected():
    assert _status("invalid") == 401

def test_current_service_secret_is_accepted():
    # 보호 파일은 서버 안에서만 읽으며 키와 발급 토큰을 출력하지 않는다.
    settings = dotenv_values("/etc/sps-harness/secrets.env")
    auth = CommonAuth(secret_key=settings["SPS_AUTH_JWT_SECRET_KEY"],
                      jwt_expire_seconds=60, refresh_token_expire_seconds=120)
    assert _status(auth.issue_access_token("8003-auth-readonly-probe")) == 422

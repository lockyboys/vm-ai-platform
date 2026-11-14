"""워커 → 로컬 SPS MCP(8000) CommonAuth 토큰 401 원인 진단 (2026-11-14, LuckyBoys 승인 흐름: 메리츠 자기 수리 401).

배경
    수리 워커(source_partner_agent._load_sps_mcp_tools)는 CommonAuth().issue_access_token("jeaje") 로 토큰을 만들어
    SPS_MCP_URL 에 붙인다. 서버(oauth_provider._decode_common_auth_token)는 서명·허용 사용자·jti·iat·iss·aud·
    token_use·scope 를 검사해 하나라도 어긋나면 401 을 준다. 키 위치는 secrets.env 한 곳으로 확인됨(①키 불일치 아님).

출력(비밀값 없음)
    - 토큰 header, claim '이름' 목록, 비밀이 아닌 claim 값(sub/token_type/iss/aud/scope/token_use 유무·값, iat/exp 타입)
    - 서버 쪽 설정 환경변수가 이 실행 환경에 '있는지'만(값은 URL 류만 표시)
    - 로컬 http://127.0.0.1:8000/mcp 에 initialize 1회 POST → HTTP 상태 코드와 WWW-Authenticate 헤더
    토큰 원문·서명 키는 절대 출력하지 않는다.
실행: python FastAPI/LangGraph/diag_mcp_common_auth_20261114.py
"""
import base64
import json
import os
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

import config  # 루트 공통 설정(일반 지침 4)

sys.path.insert(0, str(Path(config.PROJECT_ROOT)))
from common.auth import CommonAuth  # noqa: E402  워커와 같은 발급기

LOCAL_MCP_URL = "http://127.0.0.1:8000/mcp"   # 진단은 로컬만(외부 요청 없음)
NON_SECRET_CLAIMS = ("sub", "token_type", "token_use", "iss", "aud", "scope")
SERVER_ENV = ("SPS_MCP_URL", "SPS_MCP_OAUTH_ISSUER_URL", "SPS_MCP_OAUTH_RESOURCE_URL", "SPS_MCP_OAUTH_SCOPES",
              "SPS_MCP_COMMON_AUTH_ALLOWED_SUBJECTS", "SPS_AUTH_JWT_SECRET_KEY", "SPS_AGENT_SUBJECT_ID")
SECRET_ENV = {"SPS_AUTH_JWT_SECRET_KEY"}      # 이 값은 '있음/없음'만 표시


def _b64(segment: str) -> dict:
    """JWT 조각을 디코드(서명 검증 없이 내용만 본다)."""
    return json.loads(base64.urlsafe_b64decode(segment + "=" * (-len(segment) % 4)))


def main() -> int:
    report = {"checked_epoch": int(time.time())}
    # 1) 이 실행 환경의 관련 환경변수(비밀은 유무만)
    report["env"] = {name: ("있음" if os.getenv(name) else "없음") if name in SECRET_ENV
                     else (os.getenv(name) or "없음") for name in SERVER_ENV}
    # 2) 워커와 똑같이 토큰 발급 → 내용만 확인
    subject = os.getenv("SPS_AGENT_SUBJECT_ID", "jeaje").strip()
    token = CommonAuth().issue_access_token(subject)
    header_seg, payload_seg, _ = token.split(".")
    payload = _b64(payload_seg)
    report["token"] = {"header": _b64(header_seg), "claim_names": sorted(payload),
                       "values": {k: payload.get(k, "(없음)") for k in NON_SECRET_CLAIMS},
                       "iat_type": type(payload.get("iat")).__name__, "exp_type": type(payload.get("exp")).__name__,
                       "jti_present": bool(payload.get("jti")),
                       "self_verify": "ok"}
    try:  # 같은 키로 자기 검증(서명 계산이 깨졌는지 확인)
        CommonAuth().verify_token(token, expected_type="access")
    except Exception as error:  # noqa: BLE001
        report["token"]["self_verify"] = f"{type(error).__name__}: {error}"
    # 3) 로컬 MCP 서버에 initialize 1회
    body = json.dumps({"jsonrpc": "2.0", "id": 1, "method": "initialize",
                       "params": {"protocolVersion": "2025-03-26", "capabilities": {},
                                  "clientInfo": {"name": "sps-diag", "version": "1"}}}).encode()
    request = urllib.request.Request(LOCAL_MCP_URL, data=body, method="POST", headers={
        "Authorization": f"Bearer {token}", "Content-Type": "application/json",
        "Accept": "application/json, text/event-stream"})
    try:
        with urllib.request.urlopen(request, timeout=15) as response:
            report["local_mcp"] = {"status": response.status}
    except urllib.error.HTTPError as error:
        report["local_mcp"] = {"status": error.code, "www_authenticate": error.headers.get("WWW-Authenticate"),
                               "body_head": error.read(300).decode("utf-8", "replace")}
    except Exception as error:  # noqa: BLE001
        report["local_mcp"] = {"error": f"{type(error).__name__}: {error}"}
    print(json.dumps(report, ensure_ascii=False, indent=1, default=str))
    return 0


if __name__ == "__main__":
    sys.exit(main())

"""현재 8003 인증을 HTTP로 재현한다. 빈 본문을 사용해 LLM 실행과 데이터 쓰기를 방지한다."""
import json, sys
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.error import HTTPError
root=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(root))
from dotenv import dotenv_values
from common.auth import CommonAuth
def check(label, token=None):
    headers={"Content-Type":"application/json"}
    if token: headers["Authorization"]="Bearer "+token
    try:
        with urlopen(Request("http://127.0.0.1:8003/api/agent/context",data=b"{}",headers=headers),timeout=12) as r:
            print(label,r.status)
    except HTTPError as e:
        # 에러 응답에는 입력한 토큰이 포함되지 않도록 detail의 문자열만 표시한다.
        data=json.load(e)
        print(label,e.code,data.get("detail") if isinstance(data.get("detail"),str) else "request validation")
check("missing")
check("invalid","invalid")
for name, path in [("root_env",root/".env"),("service_secrets",Path("/etc/sps-harness/secrets.env")),
                   ("agent_env",root/"FastAPI/LangGraph/.env"),("fastapi_env",root/"FastAPI/.env")]:
    try:
        settings=dotenv_values(path)
        key=settings.get("SPS_AUTH_JWT_SECRET_KEY")
        if not key:
            print(name,"key_absent")
            continue
        auth=CommonAuth(secret_key=key,jwt_expire_seconds=60,refresh_token_expire_seconds=120)
        check(name,auth.issue_access_token("8003-auth-readonly-probe"))
    except (OSError,ValueError,RuntimeError) as e:
        print(name,type(e).__name__)

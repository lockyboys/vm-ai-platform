"""8003 인증 장애를 읽기 전용으로 진단한다. 비밀키·토큰·전체 환경은 출력하지 않는다."""
import json, os, subprocess
from pathlib import Path
def run(args):
    p = subprocess.run(args, capture_output=True, text=True, timeout=12)
    return p.stdout
print("LISTENER", run(["ss","-ltnp","sport","=" ,":8003"]))
for p in Path("/proc").iterdir():
    if not p.name.isdigit():
        continue
    try:
        cmd = (p/"cmdline").read_bytes().replace(b"\0",b" ").decode()
        if ("uvicorn" not in cmd and "LangGraph/main.py" not in cmd and "langgraph_long_term_memory_agent" not in cmd) or int(p.name)==os.getpid():
            continue
        # 명령의 전체 인자는 비밀정보가 포함될 수 있으므로 알려진 모듈명만 보고한다.
        env = dict(x.split("=",1) for x in (p/"environ").read_bytes().decode().split("\0") if "=" in x)
        keys = ["SPS_AUTH_JWT_SECRET_KEY","SPS_AUTH_JWT_EXPIRE_SECONDS","SPS_AUTH_REFRESH_TOKEN_EXPIRE_SECONDS"]
        print(json.dumps({"pid":int(p.name),"cwd":str((p/"cwd").resolve()),"memory_agent":"langgraph_long_term_memory_agent" in cmd,
              "main_py":"main.py" in cmd,"auth_present":{k:bool(env.get(k)) for k in keys},
              "cgroup":(p/"cgroup").read_text().strip()},ensure_ascii=False))
    except (OSError,UnicodeError,ValueError):
        pass

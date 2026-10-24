"""8003 인증 설정의 출처와 일치 여부만 보고한다. 비밀값은 출력하지 않는다."""
import json, subprocess, sys
from pathlib import Path
root=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(root))
from dotenv import dotenv_values
from FastAPI.LangGraph.langgraph_long_term_memory_agent import get_auth
def show(prop):
    p=subprocess.run(["systemctl","show","fastapi-insurance-rag.service","--value","--property="+prop],capture_output=True,text=True,timeout=12,check=True)
    return p.stdout.strip()
expected=dotenv_values("/etc/sps-harness/secrets.env").get("SPS_AUTH_JWT_SECRET_KEY")
print(json.dumps({"environment_files":show("EnvironmentFiles"),"user":show("User"),"group":show("Group"),"dropins":show("DropInPaths")}))
try:
    auth=get_auth()
    print(json.dumps({"local_effective_key_matches_protected":auth._secret_key==expected,"auth_module":str(sys.modules[type(auth).__module__].__file__)}))
except Exception as e:
    print(json.dumps({"local_auth_error":type(e).__name__}))
pid=show("MainPID")
try:
    env=dict(x.split("=",1) for x in Path("/proc",pid,"environ").read_bytes().decode().split("\0") if "=" in x)
    key=env.get("SPS_AUTH_JWT_SECRET_KEY")
    print(json.dumps({"process_key_present":bool(key),"process_key_matches_protected":bool(key) and key==expected}))
except OSError as e:
    print(json.dumps({"process_env_error":type(e).__name__}))

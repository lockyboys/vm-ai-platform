"""8003リスナーの所有サービスと対象ユニットの起動状態を秘密値なしで確認する。"""
import json,re,subprocess
from pathlib import Path
def run(args):
    return subprocess.run(args,capture_output=True,text=True,timeout=12).stdout.strip()
for service in ["fastapi-insurance-rag.service","fastapi-langgraph.service"]:
    raw=run(["systemctl","show",service,"--property=ActiveState,SubState,MainPID,Result,EnvironmentFiles,FragmentPath"])
    print(json.dumps({"service":service,"properties":raw}))
ss=run(["ss","-H","-ltnp","sport","=",":8003"])
for pid in re.findall(r"pid=(\d+)",ss):
    try:
        print(json.dumps({"listener_pid":pid,"cgroup":Path("/proc",pid,"cgroup").read_text().strip()}))
    except OSError:
        pass
print(json.dumps({"port_8003_listening":bool(ss)}))
# 例外の種類のみを抽出し、ログ本文・設定・トークンを表示しない。
raw=run(["journalctl","-u","fastapi-insurance-rag.service","-n","90","--no-pager","-o","cat"])
safe=[line for line in raw.splitlines() if any(s in line for s in ["Address already in use","address already in use","SPS_AUTH_JWT_SECRET_KEY environment variable is required","Failed with result","Started ","Stopped "])]
print(json.dumps({"safe_events":safe[-10:]}))

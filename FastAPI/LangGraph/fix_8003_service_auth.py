"""동일 앱의 수동 실행과 인증 설정 불일치를 수정하고 8003 실제 소유자·인증을 검증한다."""
import datetime, json, os, re, signal, subprocess, sys, tempfile, time
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.error import HTTPError
ROOT=Path("/data/vm_project")
sys.path.insert(0,str(ROOT))
from dotenv import dotenv_values
from common.auth import CommonAuth
SERVICE="fastapi-insurance-rag.service"
UNIT=Path("/etc/systemd/system")/SERVICE
DROPIN=Path(str(UNIT)+".d")/"90-sps-auth.conf"
CONTENT="# 공용 인증키를 보호 파일에서 주입한다. 앱 소스와 키 값은 변경하지 않는다.\n[Service]\nEnvironmentFile=/data/vm_project/.env\nEnvironmentFile=/etc/sps-harness/secrets.env\n"
def run(args):
    return subprocess.run(args,capture_output=True,text=True,timeout=35,check=True)
def owner():
    raw=run(["ss","-H","-ltnp","sport","=",":8003"]).stdout
    ids=re.findall(r"pid=(\d+)",raw)
    if not ids:
        return None
    if len(set(ids))!=1:
        raise RuntimeError("Ambiguous listener ownership")
    return int(ids[0])
def status(token=None):
    headers={"Content-Type":"application/json"}
    if token: headers["Authorization"]="Bearer "+token
    try:
        with urlopen(Request("http://127.0.0.1:8003/api/agent/context",data=b"{}",headers=headers),timeout=12) as r:
            return r.status
    except HTTPError as e:
        return e.code
def main():
    values=dotenv_values("/etc/sps-harness/secrets.env")
    key=values.get("SPS_AUTH_JWT_SECRET_KEY")
    if not key or not UNIT.is_file() or not (ROOT/".env").is_file():
        raise RuntimeError("Required unit/config/secret missing")
    if DROPIN.exists():
        raise RuntimeError("Target drop-in exists; inspect before changing")
    pid=owner()
    if pid is not None:
        base=Path("/proc",str(pid))
        args=base.joinpath("cmdline").read_bytes().decode().split("\0")
        cgroup=base.joinpath("cgroup").read_text()
        if str(ROOT/"FastAPI/LangGraph/main.py") not in args or "/session-" not in cgroup:
            raise RuntimeError("Listener is not the confirmed manual main.py process")
        # 키 값은 메모리 안에서 비교만 한다. 일치하면 이 장애의 원인과 다르므로 변경을 중단한다.
        env=dict(x.split("=",1) for x in base.joinpath("environ").read_bytes().decode().split("\0") if "=" in x)
        if env.get("SPS_AUTH_JWT_SECRET_KEY")==key:
            raise RuntimeError("Manual listener already uses expected key")
    plan={"service":SERVICE,"manual_listener_pid":pid,"dropin":str(DROPIN),"action":"replace manual main.py with systemd and protected auth environment"}
    print(json.dumps({"dry_run":True,**plan}))
    if sys.stdin.read().strip()!="APPLY 8003 AUTH FIX":
        return
    stamp=datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=9))).strftime("%Y%m%d_%H%M%S")
    backup=ROOT/"haness/backups"/("service_8003_auth_"+stamp)
    backup.mkdir(parents=True,exist_ok=False)
    original=UNIT.read_bytes()
    (backup/("fastapi-insurance-rag_BACKUP_"+stamp+".service")).write_bytes(original)
    (backup/"plan.json").write_text(json.dumps(plan,indent=2),encoding="utf-8")
    # 검증된 동일 앱만 SIGTERM으로 종료한다. 다른 서비스·프로세스는 변경하지 않는다.
    run(["sudo","-n","systemctl","stop",SERVICE])
    if pid is not None:
        if owner()!=pid:
            raise RuntimeError("Listener changed before termination")
        os.kill(pid,signal.SIGTERM)
        deadline=time.monotonic()+15
        while owner()==pid and time.monotonic()<deadline:
            time.sleep(0.3)
        if owner() is not None:
            raise RuntimeError("8003 still occupied")
    run(["sudo","-n","install","-d","-m","755",str(DROPIN.parent)])
    with tempfile.NamedTemporaryFile(mode="w",encoding="utf-8") as f:
        f.write(CONTENT);f.flush()
        run(["sudo","-n","install","-m","644",f.name,str(DROPIN)])
    run(["sudo","-n","systemctl","daemon-reload"])
    run(["sudo","-n","systemctl","start",SERVICE])
    deadline=time.monotonic()+25
    while owner() is None and time.monotonic()<deadline:
        time.sleep(0.5)
    time.sleep(3)
    pid_now=owner()
    cgroup=Path("/proc",str(pid_now),"cgroup").read_text() if pid_now else ""
    active=run(["systemctl","is-active",SERVICE]).stdout.strip()
    enabled=run(["systemctl","is-enabled",SERVICE]).stdout.strip()
    auth=CommonAuth(secret_key=key,jwt_expire_seconds=60,refresh_token_expire_seconds=120)
    codes={"missing":status(),"invalid":status("invalid"),"valid":status(auth.issue_access_token("8003-auth-readonly-probe"))}
    verified=SERVICE in cgroup and active=="active" and enabled=="enabled" and codes=={"missing":401,"invalid":401,"valid":422}
    evidence={"service":SERVICE,"active":active,"enabled":enabled,"listener_owned_by_service":SERVICE in cgroup,
              "http_status":codes,"verified":verified,"backup":str(backup),"original_unit_unchanged":UNIT.read_bytes()==original}
    (backup/"verification.json").write_text(json.dumps(evidence,indent=2),encoding="utf-8")
    print(json.dumps(evidence))
    if not verified:
        raise RuntimeError("Post-apply verification failed")
if __name__=="__main__":
    try:
        main()
    except Exception as e:
        # 예외 객체에 토큰이나 키가 포함되지 않도록 유형만 출력한다.
        print(json.dumps({"error_type":type(e).__name__,"verified":False}))
        raise SystemExit(1)

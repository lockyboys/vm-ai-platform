#!/usr/bin/env python3
"""Rotate the SPS JWT key and move the agent under systemd.

Purpose: move signing material out of project .env files, update the agent unit,
restart both JWT consumers, and verify old-key rejection/new-key acceptance.
Caveat: existing JWTs become invalid. Rollback restores the original env files
and restarts the prior local agent if any post-write verification fails.
"""
from __future__ import annotations
import json, os, pwd, re, secrets, shutil, signal, subprocess, sys, tempfile, time
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen

ROOT=Path("/data/vm_project")
PROJECT_ENV=ROOT/".env"
PROTECTED=Path("/etc/sps-harness/secrets.env")
AGENT_UNIT=Path("/etc/systemd/system/sps-gemini-agent.service")
AGENT_CWD=ROOT/"FastAPI/LangGraph/gemini"
AGENT_PID=515315
HARNESS_UNIT="sps-harness.service"
GATEWAY_HOST="sps-mcp-gateway-5v4kufkk.an.gateway.dev"
SECRET_KEYS=("SPS_AUTH_JWT_SECRET_KEY","SPS_MCP_GOOGLE_CLIENT_SECRET")

def run(args, *, input_text=None, timeout=30):
    return subprocess.run(args,input=input_text,capture_output=True,text=True,timeout=timeout,check=False)

def require_ok(args, *, timeout=30):
    p=run(args,timeout=timeout)
    if p.returncode:
        raise RuntimeError("command failed: "+Path(args[0]).name+" "+(p.stderr[-500:] or p.stdout[-500:]))
    return p.stdout.strip()

def parse_env(raw):
    values={}
    for line in raw.decode("utf-8").splitlines():
        text=line.strip()
        if not text or text.startswith("#"): continue
        if text.startswith("export "): text=text[7:].lstrip()
        if "=" not in text: continue
        key,value=text.split("=",1)
        key=key.strip()
        value=value.strip()
        if len(value)>=2 and value[0]==value[-1] and value[0] in ("'",'"'):
            value=value[1:-1]
        if re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*",key):
            values[key]=value
    return values

def remove_keys(raw, keys, add_comment=False):
    names=set(keys)
    kept=[]
    for line in raw.decode("utf-8").splitlines():
        m=re.match(r"^\s*(?:export\s+)?([A-Za-z_][A-Za-z0-9_]*)\s*=",line)
        if m and m.group(1) in names: continue
        kept.append(line)
    if add_comment:
        kept.extend(["","# SPS_AUTH_JWT_SECRET_KEY and SPS_MCP_GOOGLE_CLIENT_SECRET are in /etc/sps-harness/secrets.env."])
    return ("\n".join(kept).rstrip()+"\n").encode("utf-8")

def env_from_proc(pid):
    entries=(Path("/proc")/str(pid)/"environ").read_bytes().split(bytes([0]))
    return {x.split(b"=",1)[0].decode("ascii","ignore"):x.split(b"=",1)[1].decode("utf-8","ignore") for x in entries if b"=" in x}

def env_uid(pid):
    status=(Path("/proc")/str(pid)/"status").read_text()
    return int(next(x.split()[1] for x in status.splitlines() if x.startswith("Uid:")))

def agent_unit_text(user, group):
    return f'''[Unit]
Description=SPS Gemini Agent API
After=network-online.target sps-harness.service
Wants=network-online.target sps-harness.service

[Service]
Type=simple
User={user}
Group={group}
WorkingDirectory={AGENT_CWD}
# Load non-secret application settings first; the protected file supplies the rotated keys.
EnvironmentFile={PROJECT_ENV}
EnvironmentFile={PROTECTED}
Environment="SPS_MCP_COMMON_AUTH_ALLOWED_SUBJECTS=jeaje"
UMask=0077
ExecStart=/data/vm_project/venv/bin/python -m uvicorn sps_gemini_agent:app --host 0.0.0.0 --port 8012
Restart=on-failure
RestartSec=5
TimeoutStopSec=30

[Install]
WantedBy=multi-user.target
'''

ROOT_INSTALL=r'''
import json, os, stat, tempfile, time
from pathlib import Path
d=json.load(__import__("sys").stdin)
base=Path("/etc/sps-harness")
base.mkdir(mode=0o700,parents=True,exist_ok=True)
os.chmod(base,0o700)
backup=base/(".jwt-rotation-"+str(int(time.time())))
backup.mkdir(mode=0o700)
os.chmod(backup,0o700)
targets=[d["project_env"],d["protected_env"]]+d["extra_updates"]
manifest=[]
def save_backup(path,content,mode,uid,gid,index):
    b=backup/("file-"+str(index)+".backup")
    fd=os.open(b,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
    with os.fdopen(fd,"wb") as f: f.write(content.encode("utf-8"))
    os.chmod(b,0o600)
    manifest.append({"path":path,"backup":str(b),"mode":mode,"uid":uid,"gid":gid})
def atomic(path,content,mode,uid,gid):
    p=Path(path)
    fd,tmp=tempfile.mkstemp(prefix=".sps-secret-",dir=str(p.parent))
    try:
        os.fchmod(fd,mode)
        os.fchown(fd,uid,gid)
        with os.fdopen(fd,"wb") as f:
            f.write(content.encode("utf-8")); f.flush(); os.fsync(f.fileno())
        os.replace(tmp,p)
    finally:
        try: os.unlink(tmp)
        except FileNotFoundError: pass
for i,item in enumerate(targets):
    p=Path(item["path"])
    st=p.stat()
    old=p.read_text(encoding="utf-8")
    save_backup(str(p),old,stat.S_IMODE(st.st_mode),st.st_uid,st.st_gid,i)
    atomic(str(p),item["content"],item.get("mode",stat.S_IMODE(st.st_mode)),item.get("uid",st.st_uid),item.get("gid",st.st_gid))
unit=Path(d["unit_path"])
if unit.exists(): raise RuntimeError("agent unit unexpectedly exists")
unit.write_text(d["unit_content"],encoding="utf-8")
os.chown(unit,0,0); os.chmod(unit,0o644)
(backup/"manifest.json").write_text(json.dumps(manifest),encoding="utf-8")
os.chown(backup/"manifest.json",0,0); os.chmod(backup/"manifest.json",0o600)
print(json.dumps({"written":True,"backup_dir":str(backup)}))
'''

ROOT_RESTORE=r'''
import json, os, shutil, stat, tempfile
from pathlib import Path
d=json.load(__import__("sys").stdin)
for item in d["items"]:
    p=Path(item["path"]); data=item["content"].encode("utf-8")
    fd,tmp=tempfile.mkstemp(prefix=".sps-restore-",dir=str(p.parent))
    try:
        os.fchmod(fd,item["mode"]); os.fchown(fd,item["uid"],item["gid"])
        with os.fdopen(fd,"wb") as f: f.write(data); f.flush(); os.fsync(f.fileno())
        os.replace(tmp,p)
    finally:
        try: os.unlink(tmp)
        except FileNotFoundError: pass
unit=Path(d["unit_path"])
try: unit.unlink()
except FileNotFoundError: pass
backup=Path(d["backup_dir"])
if backup.exists(): shutil.rmtree(backup)
print("restored")
'''

def sudo_python(code,payload):
    p=subprocess.run(["sudo","-n","python3","-c",code],input=json.dumps(payload),capture_output=True,text=True,timeout=30,check=False)
    if p.returncode: raise RuntimeError("protected-file operation failed: "+(p.stderr[-500:] or p.stdout[-500:]))
    return p.stdout.strip()

def parse_main_pid(unit):
    raw=require_ok(["systemctl","show",unit,"-p","MainPID","--value"])
    return int(raw or "0")

def mcp_post(token):
    body=json.dumps({"jsonrpc":"2.0","id":1,"method":"initialize","params":{"protocolVersion":"2025-06-18","capabilities":{},"clientInfo":{"name":"jwt-rotation-check","version":"1"}}}).encode()
    req=Request("http://127.0.0.1:8000/mcp",data=body,method="POST",headers={
        "Host":GATEWAY_HOST,"Authorization":"Bearer "+token,
        "Content-Type":"application/json","Accept":"application/json, text/event-stream"})
    try:
        with urlopen(req,timeout=12) as response:
            payload=response.read(4096)
            return response.status, b'"protocolVersion"' in payload
    except HTTPError as exc:
        exc.read(1024)
        return exc.code,False

def main():
    old_project=PROJECT_ENV.read_bytes()
    old_protected=require_ok(["sudo","-n","cat",str(PROTECTED)]).encode("utf-8")
    project_values=parse_env(old_project)
    protected_values=parse_env(old_protected)
    old_key=project_values.get("SPS_AUTH_JWT_SECRET_KEY","")
    if len(old_key)<32: raise RuntimeError("project JWT key missing/too short; aborting")
    if protected_values.get("SPS_AUTH_JWT_SECRET_KEY"): raise RuntimeError("protected JWT key already set; manual review required")
    agent_env=env_from_proc(AGENT_PID)
    harness_pid=parse_main_pid(HARNESS_UNIT)
    harness_env=env_from_proc(harness_pid)
    if agent_env.get("SPS_AUTH_JWT_SECRET_KEY")!=old_key or harness_env.get("SPS_AUTH_JWT_SECRET_KEY")!=old_key:
        raise RuntimeError("running consumers do not match the project env key; aborting to avoid partial rotation")
    if str((Path("/proc")/str(AGENT_PID)/"cwd").resolve())!=str(AGENT_CWD):
        raise RuntimeError("manual agent working directory changed; refusing guessed restart")
    if os.getuid()!=env_uid(AGENT_PID):
        raise RuntimeError("execution user differs from agent owner; refusing unsafe manual-process handoff")
    agent_comm=(Path("/proc")/str(AGENT_PID)/"comm").read_text().strip()
    if agent_comm!="uvicorn": raise RuntimeError("expected uvicorn agent process not found")
    if parse_main_pid("sps-gemini-agent.service")!=0:
        raise RuntimeError("agent service already exists; refusing unit replacement")

    old_agent_env=os.environ.copy()
    old_agent_env.update(project_values)
    old_agent_env.update(protected_values)
    new_key=secrets.token_urlsafe(48)
    protected_new=remove_keys(old_protected,("SPS_AUTH_JWT_SECRET_KEY",))+f"SPS_AUTH_JWT_SECRET_KEY={new_key}\n".encode()
    project_new=remove_keys(old_project,SECRET_KEYS,add_comment=True)

    extras=[]
    extra_originals=[]
    for p in sorted(ROOT.glob(".env_backup*")):
        if not p.is_file(): continue
        raw=p.read_bytes()
        sanitized=remove_keys(raw,SECRET_KEYS,add_comment=True)
        if sanitized!=raw:
            st=p.stat()
            extras.append({"path":str(p),"content":sanitized.decode("utf-8"),"mode":st.st_mode & 0o777,"uid":st.st_uid,"gid":st.st_gid})
            extra_originals.append({"path":str(p),"content":raw.decode("utf-8"),"mode":st.st_mode & 0o777,"uid":st.st_uid,"gid":st.st_gid})

    project_stat=PROJECT_ENV.stat()
    prot_meta=require_ok(["sudo","-n","stat","-c","%a %u %g",str(PROTECTED)]).split()
    prot_mode=int(prot_meta[0],8)
    prot_uid,prot_gid=int(prot_meta[1]),int(prot_meta[2])
    unit_user=pwd.getpwuid(env_uid(AGENT_PID)).pw_name
    unit_group=pwd.getpwuid(env_uid(AGENT_PID)).pw_name
    payload={
        "project_env":{"path":str(PROJECT_ENV),"content":project_new.decode(),"mode":project_stat.st_mode & 0o777,"uid":project_stat.st_uid,"gid":project_stat.st_gid},
        "protected_env":{"path":str(PROTECTED),"content":protected_new.decode(),"mode":0o600,"uid":prot_uid,"gid":prot_gid},
        "extra_updates":extras,
        "unit_path":str(AGENT_UNIT),
        "unit_content":agent_unit_text(unit_user,unit_group),
    }
    backup_dir=None
    old_stopped=False
    new_started=False
    try:
        install_result=json.loads(sudo_python(ROOT_INSTALL,payload))
        backup_dir=install_result["backup_dir"]
        require_ok(["sudo","-n","systemctl","daemon-reload"])
        require_ok(["sudo","-n","kill","-TERM",str(AGENT_PID)])
        old_stopped=True
        for _ in range(100):
            if not Path("/proc").joinpath(str(AGENT_PID)).exists(): break
            time.sleep(.1)
        if Path("/proc").joinpath(str(AGENT_PID)).exists():
            raise RuntimeError("old agent did not stop within 10 seconds")
        require_ok(["sudo","-n","systemctl","restart",HARNESS_UNIT],timeout=45)
        require_ok(["sudo","-n","systemctl","enable","--now","sps-gemini-agent.service"],timeout=45)
        new_started=True
        for _ in range(80):
            if run(["systemctl","is-active","--quiet","sps-gemini-agent.service"]).returncode==0: break
            time.sleep(.25)
        if run(["systemctl","is-active","--quiet","sps-gemini-agent.service"]).returncode!=0:
            raise RuntimeError("new agent service did not become active")
        new_harness_pid=parse_main_pid(HARNESS_UNIT)
        new_agent_pid=parse_main_pid("sps-gemini-agent.service")
        env_h=env_from_proc(new_harness_pid)
        env_a=env_from_proc(new_agent_pid)
        protected_read=require_ok(["sudo","-n","cat",str(PROTECTED)]).encode()
        protected_now=parse_env(protected_read)
        project_now=parse_env(PROJECT_ENV.read_bytes())
        if env_h.get("SPS_AUTH_JWT_SECRET_KEY")!=new_key or env_a.get("SPS_AUTH_JWT_SECRET_KEY")!=new_key:
            raise RuntimeError("rotated key was not loaded by both running services")
        if protected_now.get("SPS_AUTH_JWT_SECRET_KEY")!=new_key:
            raise RuntimeError("protected file does not contain the active key")
        if "SPS_AUTH_JWT_SECRET_KEY" in project_now or "SPS_MCP_GOOGLE_CLIENT_SECRET" in project_now:
            raise RuntimeError("project .env still contains a protected secret")

        # Verify old-key rejection and new-key acceptance against the restarted MCP.
        sys.path.insert(0,str(ROOT))
        os.environ["SPS_MCP_COMMON_AUTH_ALLOWED_SUBJECTS"]="jeaje"
        os.environ["SPS_AUTH_JWT_SECRET_KEY"]=old_key
        from common.auth import CommonAuth
        old_token=CommonAuth().issue_access_token("jeaje")
        old_status,_=mcp_post(old_token)
        os.environ["SPS_AUTH_JWT_SECRET_KEY"]=new_key
        new_token=CommonAuth().issue_access_token("jeaje")
        new_status,new_protocol=mcp_post(new_token)
        if old_status!=401 or new_status!=200 or not new_protocol:
            raise RuntimeError(f"JWT acceptance check failed: old={old_status}, new={new_status}")

        # Read only FastAPI's schema to confirm the required request field.
        with urlopen("http://127.0.0.1:8012/openapi.json",timeout=8) as resp:
            spec=json.loads(resp.read(2_000_000))
        route=spec.get("paths",{}).get("/agent/chat",{}).get("post",{})
        request_body=route.get("requestBody",{}).get("content",{}).get("application/json",{}).get("schema",{})
        ref=request_body.get("$ref","")
        component=ref.rsplit("/",1)[-1] if ref else ""
        properties=spec.get("components",{}).get("schemas",{}).get(component,{}).get("properties",{})
        if not route or "user_input" not in properties:
            raise RuntimeError("agent route schema did not expose user_input")

        # Remove temporary rollback copies after successful dual-service verification.
        require_ok(["sudo","-n","rm","-rf",backup_dir])
        out={
            "rotation":"success",
            "services":{"sps_harness":"active","sps_gemini_agent":"active"},
            "agent_port":8012,
            "agent_route":"/agent/chat",
            "request_field":"user_input",
            "old_key_rejected":old_status==401,
            "new_key_accepted":new_status==200,
            "protected_file_mode":"600",
            "project_env_secret_assignments_removed":True,
            "backup_env_files_sanitized":len(extras),
            "temporary_rollback_copies_removed":True,
            "secret_value_printed":False,
        }
        print(json.dumps(out,ensure_ascii=False))
    except Exception as exc:
        rollback={"items":[
            {"path":str(PROJECT_ENV),"content":old_project.decode(),"mode":project_stat.st_mode & 0o777,"uid":project_stat.st_uid,"gid":project_stat.st_gid},
            {"path":str(PROTECTED),"content":old_protected.decode(),"mode":prot_mode,"uid":prot_uid,"gid":prot_gid},
            *extra_originals,
        ],"unit_path":str(AGENT_UNIT),"backup_dir":backup_dir or ""}
        try:
            require_ok(["sudo","-n","systemctl","stop","sps-gemini-agent.service"],timeout=20)
            require_ok(["sudo","-n","systemctl","disable","sps-gemini-agent.service"],timeout=20)
        except Exception: pass
        try:
            sudo_python(ROOT_RESTORE,rollback)
            require_ok(["sudo","-n","systemctl","daemon-reload"])
            require_ok(["sudo","-n","systemctl","restart",HARNESS_UNIT],timeout=45)
            if old_stopped:
                legacy=[str(ROOT/"venv/bin/python"),"-m","uvicorn","sps_gemini_agent:app","--host","0.0.0.0","--port","8012"]
                subprocess.Popen(legacy,cwd=str(AGENT_CWD),env=old_agent_env,stdin=subprocess.DEVNULL,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL,start_new_session=True)
                time.sleep(2)
            print(json.dumps({"rotation":"rolled_back","reason":type(exc).__name__,"old_agent_relaunched":old_stopped,"secret_value_printed":False}))
        except Exception as rollback_exc:
            print(json.dumps({"rotation":"failed","reason":type(exc).__name__,"rollback":"incomplete","rollback_error":type(rollback_exc).__name__,"backup_dir":backup_dir,"secret_value_printed":False}))
            raise
        raise SystemExit(1)

if __name__=="__main__": main()

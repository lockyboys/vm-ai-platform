"""승인된 Gemma 12B Q4 설치·진행 조회 CLI. E4B와 기존 소스는 삭제하지 않습니다."""
import sys, json, shlex, subprocess, uuid
sys.path.insert(0, "/data/vm_project")
import config
from haness.mcp.tools.ssh_execution_tools import run_remote
payload = json.loads(sys.stdin.read() or '{"mode":"plan"}')
mode = payload.get("mode", "plan")
if mode not in ("plan", "install", "status"):
    raise ValueError("Expected plan, install, status")
job = payload.get("job") or uuid.uuid4().hex
import re
if not re.fullmatch(r"[0-9a-f]{32}", job):
    raise ValueError("Invalid job id")
model = "gemma4:12b-it-q4_K_M"
plan = run_remote(path="FastAPI/LangGraph/multi_persona/multi_persona_agent_Ollama_Gemma4_e4b.py", ssh_target="gpu")
if mode == "plan":
    print(json.dumps({"dry_run":True,"model":model,"keep_existing":True,"target":"gpu","context":65536,"job":job}))
    raise SystemExit(0)
script = r"""
import sys, json, subprocess, shutil, os
from pathlib import Path
mode, job, model = sys.argv[1:4]
folder = Path("/data/vm_project/.sps_ssh_jobs") / job
if mode == "status":
    print((folder / "progress.json").read_text() if (folder / "progress.json").exists() else '{"state":"starting"}')
    raise SystemExit(0)
# 8GB 파일과 작업 여유를 확보한 뒤 다운로드합니다. 공간 부족이면 삭제 없이 중단합니다.
free = shutil.disk_usage("/usr/share/ollama/.ollama/models").free
if free < 11_000_000_000:
    raise RuntimeError("Need at least 11GB free for 12B Q4 installation")
folder.mkdir(mode=0o700, exist_ok=False)
worker = r'''
import json, sys, urllib.request, subprocess, time
from pathlib import Path
folder, model = Path(sys.argv[1]), sys.argv[2]
def save(value):
    temp = folder / "progress.tmp"
    temp.write_text(json.dumps(value, ensure_ascii=False))
    temp.replace(folder / "progress.json")
def post(route, data, timeout=600):
    request = urllib.request.Request("http://127.0.0.1:11434/api/" + route,
        data=json.dumps(data).encode(), headers={"Content-Type":"application/json"})
    return urllib.request.urlopen(request, timeout=timeout)
try:
    save({"state":"downloading","model":model})
    with post("pull", {"model":model,"stream":True}) as stream:
        for line in stream:
            update = json.loads(line)
            if update.get("error"):
                raise RuntimeError(update["error"])
            save({"state":"downloading","model":model,**update})
    with post("show", {"model":model}) as response:
        info = json.load(response)
    details = info.get("details", {})
    if details.get("quantization_level") != "Q4_K_M":
        raise RuntimeError("Unexpected quantization: " + str(details))
    save({"state":"testing","model":model,"details":details})
    started = time.monotonic()
    with post("chat", {"model":model,"stream":False,"think":False,"keep_alive":"5m",
         "options":{"num_ctx":65536,"num_predict":512,"temperature":0},
         "messages":[{"role":"user","content":"Fix this Python function so b=0 returns None. Return only the complete Python function.\ndef safe_divide(a, b):\n    return a / b"}]}) as response:
        answer = json.load(response)
    code = answer.get("message",{}).get("content","")
    # 생성된 테스트 함수만 격리된 제한 네임스페이스에서 검사합니다. 프로젝트 소스는 실행하지 않습니다.
    import ast
    cleaned = code.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.split("\n",1)[1].rsplit("```",1)[0].strip()
    # 아래 런타임 검사는 모델 응답을 실행하지 않고 문법과 함수 존재만 검사합니다.
    tree = ast.parse(cleaned)
    if not any(isinstance(node, ast.FunctionDef) and node.name == "safe_divide" for node in tree.body):
        raise RuntimeError("Smoke test function missing")
    ps = subprocess.run(["ollama","ps"], text=True, capture_output=True, timeout=20)
    save({"state":"finished","model":model,"details":details,"done":answer.get("done"),"done_reason":answer.get("done_reason"),
          "response":code,"elapsed_seconds":round(time.monotonic()-started,2),"ollama_ps":ps.stdout,
          "eval_count":answer.get("eval_count"),"prompt_eval_count":answer.get("prompt_eval_count")})
except Exception as error:
    save({"state":"failed","model":model,"error":str(error)})
    raise
'''
with (folder / "worker.log").open("ab") as output:
    child = subprocess.Popen([sys.executable,"-u","-c",worker,str(folder),model],
        stdin=subprocess.DEVNULL,stdout=output,stderr=output,start_new_session=True)
print(json.dumps({"state":"submitted","job":job,"pid":child.pid,"model":model}))
"""
command = plan["command"][:-1] + [shlex.join([config.SPS_SSH_TARGETS["gpu"]["python"], "-c", script, mode, job, model])]
result = subprocess.run(command, text=True, capture_output=True, timeout=90)
print(result.stdout)
print(result.stderr, file=sys.stderr)
raise SystemExit(result.returncode)

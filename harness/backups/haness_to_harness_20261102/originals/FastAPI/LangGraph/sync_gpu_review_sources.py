"""승인된 GPU 소스 동기화: 원본 백업, dry-run, 해시와 문법 검증만 수행합니다."""
import sys, json, shlex, subprocess, hashlib, shutil
from pathlib import Path
from datetime import datetime
ROOT = Path("/data/vm_project")
sys.path.insert(0, str(ROOT))
from haness.mcp.tools.ssh_execution_tools import run_remote
import config
FILES = ["FastAPI/LangGraph/multi_persona/" + name for name in (
    "multi_persona_agent_Ollama_Gemma4_e4b.py", "multi_persona_agent_gemini.py", "review_contract.py")]
mode = sys.stdin.read().strip() or "plan"
stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
if mode == "backup":
    for relative in FILES[:2] + ["config.py"]:
        path = ROOT / relative
        backup = path.with_name(path.stem + "_BACKUP_" + stamp + path.suffix)
        shutil.copy2(path, backup)
        print(json.dumps({"backup": str(backup), "sha256": hashlib.sha256(backup.read_bytes()).hexdigest()}))
    raise SystemExit(0)
if mode not in ("plan", "deploy"):
    raise ValueError("Expected backup, plan or deploy")
payload = {}
for relative in FILES:
    source = (ROOT / relative).read_text(encoding="utf-8")
    compile(source, relative, "exec")
    payload[relative] = source
plan = run_remote(path=FILES[0], ssh_target="gpu")
print(json.dumps({"dry_run": mode == "plan", "files": {p: hashlib.sha256(s.encode()).hexdigest() for p,s in payload.items()},
                  "credentials_ready": plan["credentials_ready"]}))
if mode == "plan":
    raise SystemExit(0)
# SSH 표준 입력으로 소스만 전송하며, 기존 원격 파일을 날짜 백업한 후 교체합니다.
remote = r'''
import sys, json, hashlib, shutil, os
from pathlib import Path
from datetime import datetime
root = Path("/data/vm_project")
payload = json.load(sys.stdin)
stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
for relative, source in payload.items():
    target = (root / relative).resolve()
    target.relative_to(root / "FastAPI" / "LangGraph" / "multi_persona")
    compile(source, str(target), "exec")
    if target.exists():
        backup = target.with_name(target.stem + "_BACKUP_" + stamp + target.suffix)
        shutil.copy2(target, backup)
        print(json.dumps({"backup": str(backup)}))
    temp = target.with_name(target.name + ".sync.tmp")
    temp.write_text(source, encoding="utf-8")
    temp.replace(target)
    print(json.dumps({"path": relative, "sha256": hashlib.sha256(target.read_bytes()).hexdigest(), "syntax": "OK"}))
'''
command = plan["command"][:-1] + [shlex.join([config.SPS_SSH_TARGETS["gpu"]["python"], "-c", remote])]
result = subprocess.run(command, input=json.dumps(payload), text=True, capture_output=True, timeout=110)
print(result.stdout)
print(result.stderr, file=sys.stderr)
raise SystemExit(result.returncode)

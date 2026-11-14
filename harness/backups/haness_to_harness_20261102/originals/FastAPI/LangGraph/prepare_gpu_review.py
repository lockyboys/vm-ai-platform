"""AI 서버의 이전 리뷰 보고서를 보존하고 원격 대상 상태를 확인합니다."""
import json
import shlex
import subprocess
import sys
import config
from haness.mcp.tools.ssh_execution_tools import run_remote

mode = (sys.stdin.read().strip() or "plan")
if mode not in {"plan", "backup"}:
    raise ValueError("mode must be plan or backup")
plan = run_remote(path="FastAPI/LangGraph/multi_persona/multi_persona_agent_Ollama_Gemma4_e4b.py", ssh_target="gpu")
if mode == "plan":
    print(json.dumps({"dry_run": True, "target": "gpu", "backup_previous_report": True,
                      "credentials_ready": plan["credentials_ready"]}))
    raise SystemExit(0)
script = r'''
import datetime, json, pathlib, shutil
root = pathlib.Path("/data/vm_project")
base = root / "FastAPI/LangGraph/multi_persona"
source = base / "multi_persona_agent_gemini.py"
agent = base / "multi_persona_agent_Ollama_Gemma4_e4b.py"
for path in (source, agent):
    if not path.is_file():
        raise FileNotFoundError(path)
reports = [source.with_suffix(".review.md"), source.with_suffix(".proposed.py")]
folder = root / ".sps_ssh_jobs" / ("review_backup_" + datetime.datetime.now().strftime("%Y%m%d_%H%M%S"))
existing = [path for path in reports if path.exists()]
if existing:
    folder.mkdir(mode=0o700)
    for path in existing:
        shutil.copy2(path, folder / path.name)
print(json.dumps({"source_exists": True, "agent_exists": True,
                  "previous_reports": [str(path) for path in existing],
                  "backup_dir": str(folder) if existing else None}))
'''
command = plan["command"][:-1] + [shlex.join([config.SPS_SSH_TARGETS["gpu"]["python"], "-c", script])]
result = subprocess.run(command, text=True, capture_output=True, timeout=90)
print(result.stdout, end="")
print(result.stderr, file=sys.stderr, end="")
raise SystemExit(result.returncode)

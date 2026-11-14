"""현재 GPU 리뷰 작업 하나만 중단하고 상태를 남깁니다."""
import json
import re
import shlex
import subprocess
import sys
import config
from haness.mcp.tools.ssh_execution_tools import run_remote

request = json.loads(sys.stdin.read())
mode, job = request.get("mode"), request.get("job")
if mode not in {"plan", "cancel"} or not isinstance(job, str) or not re.fullmatch(r"[0-9a-f]{32}", job):
    raise ValueError("mode plan/cancel and valid job required")
plan = run_remote(path="FastAPI/LangGraph/multi_persona/multi_persona_agent_Ollama_Gemma4_e4b.py",
                  ssh_target="gpu", ssh_operation="status", job_id=job)
remote = r'''
import json, os, pathlib, signal, sys
mode, job = sys.argv[1:3]
root = pathlib.Path("/data/vm_project")
folder = root / ".sps_ssh_jobs" / job
if not folder.is_dir():
    raise FileNotFoundError(folder)
processes = {}
for item in pathlib.Path("/proc").iterdir():
    if not item.name.isdecimal():
        continue
    try:
        raw = (item / "cmdline").read_bytes().split(b"\0")
        stat = (item / "stat").read_text()
        pid = int(item.name)
        ppid = int(stat.rsplit(")", 1)[1].split()[1])
        processes[pid] = (ppid, [part.decode(errors="replace") for part in raw if part])
    except (OSError, ValueError, IndexError):
        continue
marker = str(folder)
workers = [pid for pid, (_ppid, args) in processes.items()
           if marker in args and any("folder, root, seconds, command" in arg for arg in args)]
children = [pid for pid, (ppid, args) in processes.items()
            if ppid in workers and any(arg.endswith("multi_persona_agent_Ollama_Gemma4_e4b.py") for arg in args)]
if len(workers) != 1 or len(children) != 1:
    raise RuntimeError("expected exactly one own worker and one agent process")
if mode == "cancel":
    os.killpg(children[0], signal.SIGTERM)
print(json.dumps({"mode":mode,"job":job,"workers":workers,"children":children}))
'''
command = plan["command"][:-1] + [
    shlex.join([config.SPS_SSH_TARGETS["gpu"]["python"], "-c", remote, mode, job])
]
result = subprocess.run(command, capture_output=True, text=True, timeout=60)
print(result.stdout, end="")
print(result.stderr, file=sys.stderr, end="")
raise SystemExit(result.returncode)

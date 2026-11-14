"""중앙 SSH 설정으로 GPU 모델 저장소의 남은 공간과 설치 목록을 조회합니다."""
import sys, subprocess, shlex
sys.path.insert(0, "/data/vm_project")
import config
from haness.mcp.tools.ssh_execution_tools import run_remote
plan = run_remote(path="FastAPI/LangGraph/multi_persona/multi_persona_agent_Ollama_Gemma4_e4b.py", ssh_target="gpu")
script = """
import json, shutil, subprocess
from pathlib import Path
paths = ["/", "/usr/share/ollama/.ollama/models", "/data/vm_project"]
print(json.dumps({p:dict(zip(("total","used","free"), shutil.disk_usage(p))) for p in paths if Path(p).exists()}))
for cmd in (["ollama","--version"], ["ollama","list"], ["ollama","ps"]):
    r = subprocess.run(cmd, text=True, capture_output=True, timeout=15)
    print(json.dumps({"command":cmd,"returncode":r.returncode,"stdout":r.stdout,"stderr":r.stderr}))
"""
command = plan["command"][:-1] + [shlex.join([config.SPS_SSH_TARGETS["gpu"]["python"], "-c", script])]
r = subprocess.run(command, text=True, capture_output=True, timeout=60)
print(r.stdout)
print(r.stderr, file=sys.stderr)
raise SystemExit(r.returncode)

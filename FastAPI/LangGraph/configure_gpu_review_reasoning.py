"""AI 서버 config.py의 Ollama 추론 모드만 백업 후 설정합니다."""
import json
import shlex
import subprocess
import sys
import config
from haness.mcp.tools.ssh_execution_tools import run_remote

mode = sys.stdin.read().strip() or "plan"
if mode not in {"plan", "apply", "verify"}:
    raise ValueError("plan/apply/verify only")
plan = run_remote(path="FastAPI/LangGraph/multi_persona/multi_persona_agent_Ollama_Gemma4_e4b.py",
                  ssh_target="gpu")
if mode == "plan":
    print(json.dumps({"dry_run": True, "target": "gpu/config.py",
                      "setting": "MULTI_PERSONA_OLLAMA_REASONING = False"}))
    raise SystemExit(0)
script = r'''
import datetime, os, pathlib, re, shutil, sys, json
mode = sys.argv[1]
path = pathlib.Path("/data/vm_project/config.py")
original = path.read_text()
key = "MULTI_PERSONA_OLLAMA_REASONING"
matches = re.findall(r"^" + key + r"\s*=\s*(True|False)\s*$", original, re.M)
if len(matches) > 1:
    raise RuntimeError("duplicate reasoning settings")
backup = None
if mode == "apply" and matches != ["False"]:
    folder = pathlib.Path.home() / ".sps_config_backups"
    folder.mkdir(mode=0o700, exist_ok=True)
    backup = folder / ("config_BACKUP_" + datetime.datetime.now().strftime("%Y%m%d_%H%M%S") + ".py")
    shutil.copy2(path, backup)
    if matches:
        updated = re.sub(r"^" + key + r"\s*=.*$", key + " = False", original, count=1, flags=re.M)
    else:
        updated = original.rstrip() + "\n# AI 서버에서만 모델의 긴 사고 출력을 비활성화합니다.\n" + key + " = False\n"
    compile(updated, str(path), "exec")
    try:
        with path.open("r+") as output:
            output.seek(0)
            output.write(updated)
            output.truncate()
            output.flush()
            os.fsync(output.fileno())
    except Exception:
        with path.open("w") as rollback:
            rollback.write(original)
        raise
    matches = re.findall(r"^" + key + r"\s*=\s*(True|False)\s*$", path.read_text(), re.M)
if matches != ["False"]:
    raise RuntimeError("reasoning setting not applied")
print(json.dumps({"mode":mode,"reasoning":False,"backup":str(backup) if backup else None}))
'''
cmd = plan["command"][:-1] + [shlex.join([config.SPS_SSH_TARGETS["gpu"]["python"], "-c", script, mode])]
result = subprocess.run(cmd, capture_output=True, text=True, timeout=90)
print(result.stdout, end="")
print(result.stderr, file=sys.stderr, end="")
raise SystemExit(result.returncode)

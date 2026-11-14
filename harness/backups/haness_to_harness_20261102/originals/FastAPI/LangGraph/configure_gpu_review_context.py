"""GPU 서버의 리뷰 컨텍스트만 백업 후 조정하고 팩토리 값을 검증합니다."""
import json
import shlex
import subprocess
import sys
import config
from haness.mcp.tools.ssh_execution_tools import run_remote

mode = sys.stdin.read().strip() or "plan"
if mode not in {"plan", "apply", "verify"}:
    raise ValueError("Expected plan, apply or verify")
plan = run_remote(path="FastAPI/LangGraph/multi_persona/multi_persona_agent_Ollama_Gemma4_e4b.py", ssh_target="gpu")
if mode == "plan":
    print(json.dumps({"dry_run": True, "target": "gpu/config.py",
                      "setting": "MULTI_PERSONA_OLLAMA_CONTEXT", "value": 98304,
                      "credentials_ready": plan["credentials_ready"]}))
    raise SystemExit(0)
remote = r'''
import ast, datetime, json, pathlib, re, shutil, sys
mode = sys.argv[1]
root = pathlib.Path("/data/vm_project")
target = root / "config.py"
source = target.read_text(encoding="utf-8")
key = "MULTI_PERSONA_OLLAMA_CONTEXT"
matches = re.findall(r"^" + key + r"\s*=\s*([^#\n]+)", source, re.M)
if len(matches) > 1:
    raise ValueError("Duplicate context settings")
if mode == "apply" and matches != ["98304"]:
    backup_dir = pathlib.Path.home() / ".sps_config_backups"
    backup_dir.mkdir(mode=0o700, exist_ok=True)
    backup = backup_dir / ("config_BACKUP_" + datetime.datetime.now().strftime("%Y%m%d_%H%M%S") + ".py")
    shutil.copy2(target, backup)
    updated = (re.sub(r"^" + key + r"\s*=.*$", key + " = 98304", source, count=1, flags=re.M)
               if matches else source.rstrip() + "\n" + key + " = 98304\n")
    compile(updated, str(target), "exec")
    with target.open("r+", encoding="utf-8") as output:
        output.seek(0)
        output.write(updated)
        output.truncate()
    print(json.dumps({"backup": str(backup)}))
sys.path.insert(0, str(root))
import config as project_config
agent = root / "FastAPI/LangGraph/multi_persona/multi_persona_agent_Ollama_Gemma4_e4b.py"
function = next(node for node in ast.parse(agent.read_text(encoding="utf-8")).body
                if isinstance(node, ast.FunctionDef) and node.name == "initialize_llm")
scope = {"os": __import__("os"), "Optional": __import__("typing").Optional,
         "project_config": project_config, "ChatOllama": lambda **kwargs: kwargs}
exec(compile(ast.Module(body=[function], type_ignores=[]), str(agent), "exec"), scope)
actual = scope["initialize_llm"]()
result = {"mode": mode, "model": actual["model"], "num_ctx": actual["num_ctx"],
          "reasoning": actual["reasoning"]}
if actual["model"] != "gemma4:12b-it-q4_K_M" or actual["num_ctx"] != 98304:
    raise RuntimeError("GPU review factory mismatch: " + repr(result))
print(json.dumps(result))
'''
command = plan["command"][:-1] + [shlex.join([config.SPS_SSH_TARGETS["gpu"]["python"], "-c", remote, mode])]
result = subprocess.run(command, text=True, capture_output=True, timeout=90)
print(result.stdout, end="")
print(result.stderr, file=sys.stderr, end="")
raise SystemExit(result.returncode)

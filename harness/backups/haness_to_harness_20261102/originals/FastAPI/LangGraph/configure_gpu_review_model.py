"""AI 서버의 Ollama 모델 선택만 조회·백업·적용·검증합니다."""
import json
import shlex
import subprocess
import sys

from haness.mcp.tools.ssh_execution_tools import run_remote
import config

MODE = (sys.stdin.read().strip() or "inspect")
if MODE not in {"inspect", "plan", "apply", "verify"}:
    raise ValueError("mode must be inspect, plan, apply, or verify")
MODEL = "gemma4:12b-it-q4_K_M"
plan = run_remote(
    path="FastAPI/LangGraph/multi_persona/multi_persona_agent_Ollama_Gemma4_e4b.py",
    ssh_target="gpu",
)
remote = r'''
import ast
import datetime
import json
import os
import pathlib
import re
import shutil
import subprocess
import sys

mode, model = sys.argv[1:3]
root = pathlib.Path("/data/vm_project")
target = root / "config.py"
dotenv = root / ".env"
key = "MULTI_PERSONA_OLLAMA_MODEL"
def inspect():
    source = target.read_text(encoding="utf-8")
    assigned = re.findall(r"^" + key + r"\s*=\s*['\"]([^'\"]+)['\"]\s*$", source, re.M)
    # 비밀 내용은 읽거나 출력하지 않고 Ollama 모델 값만 확인합니다.
    dotenv_model = None
    if dotenv.exists():
        for line in dotenv.read_text(encoding="utf-8").splitlines():
            match = re.match(r'^\s*(?:export\s+)?OLLAMA_MODEL\s*=\s*(.*?)\s*$', line)
            if match:
                dotenv_model = match.group(1).strip().strip(chr(39) + chr(34))
    return {"config_exists": target.exists(), "config_model": assigned,
            "dotenv_model": dotenv_model, "process_model": os.getenv("OLLAMA_MODEL"),
            "config_writable": os.access(target, os.W_OK)}
state = inspect()
if mode == "apply":
    if len(state["config_model"]) > 1:
        raise RuntimeError("duplicate model assignments; refusing to edit")
    if state["dotenv_model"] and state["dotenv_model"] != model:
        raise RuntimeError("AI .env defines another model; refusing to shadow it")
    if state["process_model"] and state["process_model"] != model:
        raise RuntimeError("SSH session defines another model; refusing to shadow it")
    result = subprocess.run(["ollama", "list"], text=True, capture_output=True, timeout=15, check=True)
    if not any(line.split()[:1] == [model] for line in result.stdout.splitlines()):
        raise RuntimeError("requested model is not installed")
    if state["config_model"] != [model]:
        original = target.read_text(encoding="utf-8")
        stamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        # 프로젝트 루트는 쓰기 제한이 있으므로 사용자 소유의 비공개 디렉터리에 원본을 보존합니다.
        backup_dir = pathlib.Path.home() / ".sps_config_backups"
        backup_dir.mkdir(mode=0o700, exist_ok=True)
        backup = backup_dir / ("config_BACKUP_" + stamp + ".py")
        shutil.copy2(target, backup)
        replacement = "# AI 서버에서만 사용할 Ollama 모델. PC와 dev의 설정은 변경하지 않습니다.\n" + key + " = " + repr(model) + "\n"
        if state["config_model"]:
            updated = re.sub(r"^" + key + r"\s*=.*$", replacement.rstrip(), original, count=1, flags=re.M)
        else:
            updated = original.rstrip() + "\n\n" + replacement
        compile(updated, str(target), "exec")
        # 대상 디렉터리에 임시 파일을 만들 수 없어 쓰기 가능한 기존 파일을 백업 후 갱신합니다.
        try:
            with target.open("r+", encoding="utf-8") as output:
                output.seek(0)
                output.write(updated)
                output.truncate()
                output.flush()
                os.fsync(output.fileno())
        except Exception:
            with target.open("w", encoding="utf-8") as rollback:
                rollback.write(original)
            raise
        state = inspect()
        state["backup"] = str(backup)
    if state["config_model"] != [model]:
        raise RuntimeError("model configuration verification failed")
if mode == "verify":
    # 실제 팩토리만 추출해 생성 인자를 검사하고 모델/서비스 호출은 피합니다.
    sys.path.insert(0, str(root))
    import config as project_config
    agent = root / "FastAPI/LangGraph/multi_persona/multi_persona_agent_Ollama_Gemma4_e4b.py"
    tree = ast.parse(agent.read_text(encoding="utf-8"))
    function = next(node for node in tree.body
                    if isinstance(node, ast.FunctionDef) and node.name == "initialize_llm")
    fake = lambda **kwargs: kwargs
    scope = {"os": os, "Optional": __import__("typing").Optional, "project_config": project_config, "ChatOllama": fake}
    exec(compile(ast.Module(body=[function], type_ignores=[]), str(agent), "exec"), scope)
    actual = scope["initialize_llm"]()
    state["factory_model"] = actual["model"]
    state["context"] = actual["num_ctx"]
    state["reasoning"] = actual["reasoning"]
    state["source_sha256"] = __import__("hashlib").sha256(agent.read_bytes()).hexdigest()
    if actual["model"] != model:
        raise RuntimeError("AI factory did not select installed model")
print(json.dumps({"mode": mode, **state}, ensure_ascii=False))
'''
command = plan["command"][:-1] + [
    shlex.join([config.SPS_SSH_TARGETS["gpu"]["python"], "-c", remote, MODE, MODEL])
]
if MODE == "plan":
    print(json.dumps({"dry_run": True, "target": "gpu/config.py",
                      "model": MODEL, "credentials_ready": plan["credentials_ready"]}))
    MODE = "inspect"
    command = plan["command"][:-1] + [
        shlex.join([config.SPS_SSH_TARGETS["gpu"]["python"], "-c", remote, MODE, MODEL])
    ]
result = subprocess.run(command, text=True, capture_output=True, timeout=90)
print(result.stdout, end="")
print(result.stderr, file=sys.stderr, end="")
raise SystemExit(result.returncode)

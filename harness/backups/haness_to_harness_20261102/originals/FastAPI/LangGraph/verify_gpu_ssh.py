"""GPU SSH 연결과 소스 해시를 확인하는 운영 점검 CLI. stdin의 execute가 있을 때만 접속합니다."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import hashlib
import json
from haness.mcp.tools.ssh_execution_tools import run_remote

if __name__ == "__main__":
    execute = sys.stdin.read().strip() == "execute"
    for name in ("multi_persona_agent_Ollama_Gemma4_e4b.py", "multi_persona_agent_gemini.py"):
        path = "FastAPI/LangGraph/multi_persona/" + name
        plan = run_remote(path=path, ssh_target="gpu", dry_run=True)
        print(json.dumps({key: plan[key] for key in (
            "ssh_target", "ssh_operation", "credentials_ready", "executed")}))
        if execute:
            result = run_remote(path=path, ssh_target="gpu", dry_run=False, execute_confirmed=True)
            print(json.dumps({key: result.get(key) for key in (
                "executed", "returncode", "timed_out", "stdout", "stderr")}))
            print("local_sha256:", hashlib.sha256(Path(path).read_bytes()).hexdigest())
            if result.get("returncode") != 0:
                raise SystemExit(1)

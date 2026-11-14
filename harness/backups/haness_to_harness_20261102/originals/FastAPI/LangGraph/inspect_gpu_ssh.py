"""등록된 GPU 대상의 상태·기존 오류 로그를 읽기 전용으로 조회합니다."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import json
from haness.mcp.tools.ssh_execution_tools import run_remote
if __name__ == "__main__":
    execute = sys.stdin.read().strip() == "execute"
    queries = [
        ("gpu", "FastAPI/LangGraph/multi_persona/multi_persona_agent_Ollama_Gemma4_e4b.py"),
        ("log", "FastAPI/LangGraph/multi_persona/multi_persona_error.log"),
    ]
    for operation, path in queries:
        result = run_remote(path=path, ssh_target="gpu", ssh_operation=operation,
                            dry_run=not execute, execute_confirmed=execute)
        print(json.dumps({key: result.get(key) for key in
                         ("ssh_operation", "executed", "returncode", "stdout", "stderr")}))

"""종료된 GPU 리뷰 작업의 최종 답변만 읽는 점검 CLI."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import json
import re
import shlex
import subprocess
from haness.mcp.tools.ssh_execution_tools import run_remote

if __name__ == "__main__":
    job = sys.stdin.read().strip()
    if not re.fullmatch(r"[0-9a-f]{32}", job):
        raise ValueError("Expected one review job_id")
    # 기존 중앙 설정과 SSH 옵션을 그대로 사용하여 승인된 작업 로그만 읽습니다.
    plan = run_remote(path="FastAPI/LangGraph/multi_persona/multi_persona_agent_Ollama_Gemma4_e4b.py",
                      ssh_target="gpu", ssh_operation="status", job_id=job)
    script = r'''
import json, sys
from pathlib import Path
folder = Path("/data/vm_project/.sps_ssh_jobs") / sys.argv[1]
status = json.loads((folder / "status.json").read_text())
text = (folder / "output.log").read_text(errors="replace")
marker = "[최종 검증된 답변]:"
final = text.rsplit(marker, 1)[-1] if marker in text else text[-7000:]
lines = [line for line in text.splitlines() if any(
    key in line for key in ("[Planner]", "토큰 소모량", "추출된 검증", "[호출 집계]"))]
print(json.dumps({"status": status, "progress": lines[-12:], "final": final[-7000:]},
                 ensure_ascii=False))
'''
    import config
    command = plan["command"][:-1] + [shlex.join(
        [config.SPS_SSH_TARGETS["gpu"]["python"], "-c", script, job])]
    result = subprocess.run(command, capture_output=True, text=True, timeout=30)
    print(result.stdout)
    print(result.stderr, file=sys.stderr)
    raise SystemExit(result.returncode)

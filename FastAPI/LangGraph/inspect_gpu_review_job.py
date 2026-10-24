"""GPU 리뷰 작업의 상태·실측 컨텍스트·출력 계약만 읽는 점검 CLI."""
import sys, re, json, shlex, subprocess
from pathlib import Path
sys.path.insert(0, "/data/vm_project")
import config
from haness.mcp.tools.ssh_execution_tools import run_remote
job = sys.stdin.read().strip()
if not re.fullmatch(r"[0-9a-f]{32}", job):
    raise ValueError("Expected generated job_id")
plan = run_remote(path="FastAPI/LangGraph/multi_persona/multi_persona_agent_Ollama_Gemma4_e4b.py", ssh_target="gpu", ssh_operation="status", job_id=job)
script = r'''
import sys, json, subprocess
from pathlib import Path
root = Path("/data/vm_project")
sys.path.insert(0, str(root))
from FastAPI.LangGraph.multi_persona.review_contract import build_review_query, validate_review, source_block
folder = root / ".sps_ssh_jobs" / sys.argv[1]
status = json.loads((folder / "status.json").read_text())
text = (folder / "output.log").read_text(errors="replace") if (folder / "output.log").exists() else ""
keys = ("[Planner]", "[Agent]", "토큰 소모량", "추출된 검증", "[출력 계약 실패]", "[출력 검증]", "[경고]", "Traceback", "Error", "호출 제한")
progress = [line for line in text.splitlines() if any(key in line for key in keys)]
answer = {"status": status, "log_bytes": len(text.encode()), "progress": progress[-20:], "tail": text[-1500:] if status["state"] != "running" else ""}
for cmd in (["ollama", "ps"], ["nvidia-smi", "--query-gpu=name,memory.used,utilization.gpu", "--format=csv,noheader"]):
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
    answer[cmd[0]] = r.stdout
if status["state"] != "running":
    source = root / "FastAPI/LangGraph/multi_persona/multi_persona_agent_gemini.py"
    report = source.with_name(source.stem + ".review.md")
    if report.exists():
        final = report.read_text()
        query = build_review_query(source, source.read_text())
        answer["review"] = {"path":str(report), "chars":len(final), "code_chars":len(source_block(final.split("## 3. 최종 수정 전체 소스 코드", 1)[-1])), "errors":validate_review(final, query)}
print(json.dumps(answer, ensure_ascii=False))
'''
command = plan["command"][:-1] + [shlex.join([config.SPS_SSH_TARGETS["gpu"]["python"], "-c", script, job])]
result = subprocess.run(command, capture_output=True, text=True, timeout=40)
print(result.stdout)
print(result.stderr, file=sys.stderr)
raise SystemExit(result.returncode)

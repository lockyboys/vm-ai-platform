"""비동기 Ollama 블라인드 리뷰 제출/상태 조회."""
import json, os, subprocess
from pathlib import Path
from uuid import uuid4
PROJECT_ROOT=Path("/data/vm_project")
JOB_ROOT=PROJECT_ROOT/"harness/memory/blind_review_jobs"
def _paths(job_id):
    if len(job_id)!=32 or any(c not in "0123456789abcdef" for c in job_id): raise ValueError("Invalid job_id")
    d=JOB_ROOT/job_id
    return d/"request.json",d/"result.json"
def submit(provider="ollama"):
    """Ollama/Gemini 블라인드 리뷰를 독립 프로세스로 제출하고 즉시 job_id를 반환한다."""
    if provider not in ("ollama","gemini"): raise ValueError("invalid provider")
    job_id=uuid4().hex
    req_path,res_path=_paths(job_id); req_path.parent.mkdir(parents=True,exist_ok=True)
    cmd=[str(PROJECT_ROOT/"venv/bin/python"),"FastAPI/LangGraph/blind_review_20261027.py"]
    out=res_path.open("w",encoding="utf-8")
    p=subprocess.Popen(cmd,cwd=PROJECT_ROOT,stdin=subprocess.PIPE,stdout=out,stderr=subprocess.STDOUT,start_new_session=True)
    p.stdin.write((json.dumps({"provider":provider})+"\n").encode()); p.stdin.close(); out.close()
    req={"job_id":job_id,"provider":provider,"state":"running","pid":p.pid,"result_path":str(res_path)}
    req_path.write_text(json.dumps(req,ensure_ascii=False),encoding="utf-8")
    return req
def _alive(pid):
    try:
        os.kill(int(pid),0); return True
    except (ProcessLookupError,PermissionError): return False
def status(job_id):
    """프로세스 생존 여부와 최종 결과 JSON을 확인해 상태를 반환한다."""
    req_path,res_path=_paths(job_id); req=json.loads(req_path.read_text(encoding="utf-8"))
    output=res_path.read_text(encoding="utf-8") if res_path.exists() else ""
    if _alive(req.get("pid",0)):
        return {**req,"state":"running","output":output}
    final=None
    for line in reversed(output.splitlines()):
        try:
            candidate=json.loads(line)
            if isinstance(candidate,dict) and ("status" in candidate or "error" in candidate):
                final=candidate; break
        except json.JSONDecodeError: pass
    state="completed" if final and final.get("status") in ("completed","blocked_after_10_consecutive_failures","blocked_after_3_consecutive_failures") else "failed"
    return {**req,"state":state,"return_code":final.get("returncode") if final else None,"final":final,"output":output}

"""Durable async blind-review job runner with separate stdout/stderr artifacts."""
import json, os, subprocess
from pathlib import Path
from uuid import uuid4

PROJECT_ROOT = Path("/data/vm_project")
JOB_ROOT = PROJECT_ROOT / "harness/memory/blind_review_jobs"

# 2026-10-30 완료 게이트: 워커 최종 status 가 이 값일 때만 성공 후보로 본다.
# (이전에는 blocked_after_* 도 completed 로 집계되어 0/82 결과가 완료로 보고됨)
SUCCESS_STATUS = "completed"

def _paths(job_id):
    if len(job_id) != 32 or any(c not in "0123456789abcdef" for c in job_id):
        raise ValueError("Invalid job_id")
    d = JOB_ROOT / job_id
    return d / "request.json", d / "result.json", d / "stderr.log"

def submit(provider="ollama"):
    if provider not in ("ollama", "gemini"):
        raise ValueError("invalid provider")
    job_id = uuid4().hex
    req_path, result_path, stderr_path = _paths(job_id)
    req_path.parent.mkdir(parents=True, exist_ok=True)
    rc_path = req_path.parent / "return_code"
    # 분리 실행(start_new_session)된 프로세스의 종료코드는 status() 에서 얻을 수 없으므로
    # sh 가 python 종료 직후 $? 를 return_code 파일에 기록한다.
    # 경로는 위치 인자($0, $1)로만 전달해 셸 문자열 조합(인젝션)을 피한다.
    py_cmd = [str(PROJECT_ROOT / "venv/bin/python"), "FastAPI/LangGraph/blind_review_20261027.py"]
    cmd = ["/bin/sh", "-c", '"$0" "$1"; echo $? > "$2"', py_cmd[0], py_cmd[1], str(rc_path)]
    out = result_path.open("w", encoding="utf-8")
    err = stderr_path.open("w", encoding="utf-8")
    p = subprocess.Popen(cmd, cwd=PROJECT_ROOT, stdin=subprocess.PIPE,
                         stdout=out, stderr=err, start_new_session=True)
    # job_id 를 넘겨 워커가 job 별 결과 디렉터리를 쓰게 한다 (job 간 결과 섞임 방지)
    p.stdin.write((json.dumps({"provider": provider, "job_id": job_id}) + "\n").encode())
    p.stdin.close(); out.close(); err.close()
    req = {"job_id": job_id, "provider": provider, "state": "running",
           "pid": p.pid, "result_path": str(result_path),
           "stderr_path": str(stderr_path), "return_code": None}
    req_path.write_text(json.dumps(req, ensure_ascii=False), encoding="utf-8")
    return req

def _alive(pid):
    # pid 가 없거나 0 이면 실행 중이 아니다.
    # (os.kill(0, 0) 은 '자기 프로세스 그룹'에 대한 검사라 항상 성공 → 예전 job 이 running 고착)
    if not pid:
        return False
    try:
        os.kill(int(pid), 0)
        return True
    except (ProcessLookupError, PermissionError, ValueError):
        return False

def _read_return_code(rc_path):
    """sh 래퍼가 남긴 종료코드. 파일이 없거나 숫자가 아니면 None(미확인)."""
    try:
        return int(rc_path.read_text(encoding="utf-8").strip())
    except (FileNotFoundError, ValueError):
        return None

def judge_state(final, return_code):
    """종료된 job 의 최종 상태 판정 (보고서 7장 완료 조건).

    completed  : 워커 status=completed, completed==total>0, 고유 ID 수==total, 종료코드 0 또는 미확인(구 job)
    incomplete : 워커는 정상 종료했으나 82건 게이트 미충족 (예: 0/82)
    failed     : 최종 JSON 없음, preflight/blocked 실패, 또는 종료코드 != 0
    """
    if not final or final.get("status") != SUCCESS_STATUS:
        return "failed"
    if return_code not in (0, None):
        return "failed"
    total = final.get("total") or 0
    done = final.get("completed") or 0
    unique = final.get("unique_ids", done)  # 구 워커 출력에는 unique_ids 가 없음
    if total > 0 and done == total and unique == total:
        return "completed"
    return "incomplete"

def _persist_state(req_path, req, state, return_code):
    """종료 상태를 request.json 에 기록해 파일만 봐도 running 으로 오인하지 않게 한다."""
    if req.get("state") == state and req.get("return_code") == return_code:
        return
    tmp = req_path.with_suffix(".tmp")
    tmp.write_text(json.dumps({**req, "state": state, "return_code": return_code}, ensure_ascii=False), encoding="utf-8")
    tmp.replace(req_path)  # 원자적 교체 (쓰는 도중 끊겨도 기존 파일 보존)

def status(job_id):
    req_path, result_path, stderr_path = _paths(job_id)
    req = json.loads(req_path.read_text(encoding="utf-8"))
    output = result_path.read_text(encoding="utf-8") if result_path.exists() else ""
    stderr = stderr_path.read_text(encoding="utf-8") if stderr_path.exists() else ""
    if _alive(req.get("pid", 0)):
        return {**req, "state": "running", "output": output, "stderr": stderr}
    final = None
    for line in reversed(output.splitlines()):
        try:
            candidate = json.loads(line)
            if isinstance(candidate, dict) and ("status" in candidate or "error" in candidate):
                final = candidate
                break
        except json.JSONDecodeError:
            pass
    return_code = _read_return_code(req_path.parent / "return_code")
    state = judge_state(final, return_code)
    _persist_state(req_path, req, state, return_code)
    return {**req, "state": state, "return_code": return_code,
            "final": final, "output": output, "stderr": stderr}

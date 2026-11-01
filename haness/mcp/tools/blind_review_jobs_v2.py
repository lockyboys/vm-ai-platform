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

def _next_attempt(job_dir):
    """이전 실행 산출물을 보존할 attempt 번호(1부터). 이미 있는 번호는 건너뛴다(덮어쓰기 금지)."""
    n = 1
    while (job_dir / f"request.attempt{n}.json").exists():
        n += 1
    return n

def _preserve_previous(job_dir, n):
    """이전 request/result/stderr/return_code를 attemptN 이름으로 옮긴다(삭제 없음, 원본 보존).
    return_code를 비워 두는 이유: 새 실행이 끝나기 전에 status()가 옛 종료코드를 읽지 않게 하기 위해서다."""
    for name, new_name in (("request.json", f"request.attempt{n}.json"),
                           ("result.json", f"result.attempt{n}.json"),
                           ("stderr.log", f"stderr.attempt{n}.log"),
                           ("return_code", f"return_code.attempt{n}")):
        if (job_dir / name).exists():
            (job_dir / name).replace(job_dir / new_name)

def submit(provider="ollama", resume_job_id="", prompt_variant="", ollama_target="", ollama_model=""):
    """블라인드 리뷰 job을 독립 프로세스로 띄운다.

    resume_job_id(2026-11-01 LuckyBoys): 멈춘 job을 같은 job_id·같은 결과 폴더로 다시 띄운다.
      워커는 success=true 결과를 재사용하므로 성공한 건은 건너뛰고 나머지만 처리한다.
      잘못된 id·없는 job·다른 provider·아직 실행 중인 job은 프로세스를 띄우기 전에 거부한다.
    prompt_variant(2026-11-01 LuckyBoys): config.BLIND_REVIEW_PROMPTS 의 지시문 이름("review"|"bug_focus").
      빈 값이면 새 job은 기본값(review), 이어서 실행은 이전 job의 지시문을 그대로 쓴다.
      이어서 실행에 다른 지시문을 주면 거부한다(한 job 안에서 지시문이 섞이면 비교가 무의미해짐).
    ollama_target / ollama_model(2026-11-01 LuckyBoys: GPU 서버 gemma4:12b-it-q4_K_M 실험):
      대상은 config.BLIND_REVIEW_OLLAMA_ENDPOINTS 이름(laptop|gpu), 모델은 config.BLIND_REVIEW_MODEL_DIGESTS 이름.
      빈 값이면 새 job은 laptop + config.OLLAMA_MODEL(기존 동작), 이어서 실행은 이전 job 값을 그대로 쓴다.
      provider=ollama 일 때만 의미가 있으며, 이어서 실행에 다른 값을 주면 거부한다(한 job 안에서 모델이 섞이지 않게).
    """
    import config  # 지연 import: 지시문 목록은 루트 공통 설정에서만 읽는다(하드코딩 금지)

    if provider not in ("ollama", "gemini"):
        raise ValueError("invalid provider")
    if prompt_variant is None:
        prompt_variant = ""  # MCP에서 null이 오면 '지정 안 함'으로 본다
    if not isinstance(prompt_variant, str) or (prompt_variant and prompt_variant not in config.BLIND_REVIEW_PROMPTS):
        raise ValueError(f"unknown prompt_variant: {prompt_variant!r}")  # 등록 안 된 이름·숫자 등은 실행 전 거부
    # 대상·모델 검증: None(MCP null)은 '지정 안 함', 문자열이 아니거나 목록에 없으면 프로세스를 띄우기 전에 거부
    if ollama_target is None:
        ollama_target = ""
    if ollama_model is None:
        ollama_model = ""
    if not isinstance(ollama_target, str) or (ollama_target and ollama_target not in config.BLIND_REVIEW_OLLAMA_ENDPOINTS):
        raise ValueError(f"unknown ollama_target: {ollama_target!r}")
    if not isinstance(ollama_model, str) or (ollama_model and ollama_model not in config.BLIND_REVIEW_MODEL_DIGESTS):
        raise ValueError(f"unknown ollama_model: {ollama_model!r}")
    attempt = None
    if resume_job_id:
        req_path, result_path, stderr_path = _paths(resume_job_id)  # 형식 검사(32자리 소문자 hex)
        if not req_path.exists():
            raise ValueError(f"resume job not found: {resume_job_id}")
        previous = json.loads(req_path.read_text(encoding="utf-8"))
        if previous.get("provider") != provider:
            raise ValueError(f"provider mismatch: job={previous.get('provider')}, requested={provider}")
        if _alive(previous.get("pid", 0)):
            raise ValueError(f"job is still running: {resume_job_id}")
        previous_variant = previous.get("prompt_variant", config.BLIND_REVIEW_DEFAULT_PROMPT)  # 예전 job=review
        if prompt_variant and prompt_variant != previous_variant:
            raise ValueError(f"prompt_variant mismatch: job={previous_variant}, requested={prompt_variant}")
        variant = previous_variant
        # 예전 job(대상·모델 기록 없음)은 노트북 + config.OLLAMA_MODEL 로 돌았던 것으로 본다
        previous_target = previous.get("ollama_target", config.BLIND_REVIEW_DEFAULT_OLLAMA_TARGET)
        previous_model = previous.get("ollama_model", config.OLLAMA_MODEL)
        if ollama_target and ollama_target != previous_target:
            raise ValueError(f"ollama_target mismatch: job={previous_target}, requested={ollama_target}")
        if ollama_model and ollama_model != previous_model:
            raise ValueError(f"ollama_model mismatch: job={previous_model}, requested={ollama_model}")
        target, model = previous_target, previous_model
        attempt = _next_attempt(req_path.parent)
        _preserve_previous(req_path.parent, attempt)
        job_id = resume_job_id
    else:
        variant = prompt_variant or config.BLIND_REVIEW_DEFAULT_PROMPT
        target = ollama_target or config.BLIND_REVIEW_DEFAULT_OLLAMA_TARGET
        model = ollama_model or config.OLLAMA_MODEL
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
    payload = {"provider": provider, "job_id": job_id, "prompt_variant": variant}
    if provider == "ollama":
        payload.update(ollama_target=target, ollama_model=model)  # Gemini 실행에는 넘기지 않는다(의미 없음)
    p.stdin.write((json.dumps(payload) + "\n").encode())
    p.stdin.close(); out.close(); err.close()
    req = {"job_id": job_id, "provider": provider, "state": "running",
           "pid": p.pid, "result_path": str(result_path),
           "stderr_path": str(stderr_path), "return_code": None, "prompt_variant": variant}
    if provider == "ollama":
        req.update(ollama_target=target, ollama_model=model)  # 이어서 실행이 같은 대상·모델을 쓰도록 기록
    if attempt is not None:
        req["resumed_from_attempt"] = attempt  # 몇 번째 재실행인지(이전 산출물은 *.attemptN.*)
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

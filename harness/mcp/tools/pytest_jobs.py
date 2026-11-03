"""pytest를 비동기 job으로 실행하고 상태를 보존하는 도구."""
from __future__ import annotations

import json
import subprocess
from pathlib import Path
from uuid import uuid4

PROJECT_ROOT = Path("/data/vm_project").resolve()
JOB_ROOT = PROJECT_ROOT / "harness/memory/pytest_jobs"


def _paths(job_id: str) -> tuple[Path, Path]:
    if len(job_id) != 32 or any(c not in "0123456789abcdef" for c in job_id):
        raise ValueError("Invalid pytest job_id")
    folder = JOB_ROOT / job_id
    return folder / "request.json", folder / "result.json"


def submit(test_paths: list[str], title: str = "") -> dict:
    """pytest를 독립 프로세스로 제출하고 즉시 job_id를 반환한다."""
    if not test_paths:
        raise ValueError("test_paths must not be empty")
    job_id = uuid4().hex
    request_path, result_path = _paths(job_id)
    request_path.parent.mkdir(parents=True, exist_ok=True)
    request = {"job_id": job_id, "test_paths": test_paths, "title": title,
               "state": "running", "result_path": str(result_path)}
    request_path.write_text(json.dumps(request, ensure_ascii=False), encoding="utf-8")
    request_path.chmod(0o600)
    command = [str(PROJECT_ROOT / "venv/bin/python"), "-m", "pytest",
               *test_paths, "--disable-warnings", "--tb=short", "-q"]
    subprocess.Popen(command, cwd=PROJECT_ROOT, stdout=result_path.open("w", encoding="utf-8"),
                     stderr=subprocess.STDOUT, start_new_session=True)
    return request


def status(job_id: str) -> dict:
    """pytest job의 저장 상태를 반환한다."""
    request_path, result_path = _paths(job_id)
    request = json.loads(request_path.read_text(encoding="utf-8"))
    if result_path.exists():
        return {**request, "state": "completed", "output": result_path.read_text(encoding="utf-8")}
    return request

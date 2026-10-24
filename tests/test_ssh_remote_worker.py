"""고정 원격 프로그램의 실제 파일 경계와 백그라운드 실행을 로컬 임시 저장소에서 검증합니다."""
import json
import subprocess
import sys
import time
import uuid
from haness.mcp.tools.ssh_execution_tools import REMOTE_HELPER

def invoke(root, operation, job="", arguments=None):
    return subprocess.run(
        [sys.executable, "-c", REMOTE_HELPER, str(root), operation,
         "FastAPI/LangGraph/sample.py", job, "3", json.dumps(arguments or [])],
        capture_output=True, text=True, timeout=5,
    )

def test_remote_worker_background_result_and_literal_args(tmp_path):
    source = tmp_path / "FastAPI/LangGraph/sample.py"
    source.parent.mkdir(parents=True)
    source.write_text("import sys\nprint(sys.argv[1])\n")
    job = uuid.uuid4().hex
    result = invoke(tmp_path, "run", job, ["$(touch NEVER)"])
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout)["state"] == "submitted"
    for attempt in range(100):
        status = invoke(tmp_path, "status", job)
        payload = json.loads(status.stdout)
        if payload["state"] == "finished":
            break
        time.sleep(0.02)
    assert payload["state"] == "finished"
    assert payload["returncode"] == 0
    assert "$(touch NEVER)" in payload["output"]
    assert not (tmp_path / "NEVER").exists()

def test_remote_hash_rejects_symlink_escape(tmp_path):
    folder = tmp_path / "FastAPI/LangGraph"
    folder.mkdir(parents=True)
    outside = tmp_path / "outside.txt"
    outside.write_text("private")
    (folder / "sample.py").symlink_to(outside)
    result = invoke(tmp_path, "hash")
    assert result.returncode != 0
    assert "private" not in result.stdout

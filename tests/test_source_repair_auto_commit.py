"""haness/source_repair.py의 자동 git 커밋 작성자(PARTNER 페르소나) 분리 회귀 테스트.

검증 의도:
- _auto_commit이 git commit을 호출할 때 --author로 사람 계정이 아닌 PARTNER 페르소나
  신원을 지정하는지 확인한다(커밋 메시지 태그와 별개로, git log 작성자 칼럼만 봐도
  사람 커밋과 AI 자동 커밋이 구분되게 하기 위함).
- GIT_AUTHOR_NAME/GIT_COMMITTER_NAME 환경변수도 같은 페르소나 이름으로 전달되는지,
  이메일 local-part에 agent_run_id가 들어가는지 확인한다.
기대 결과: 모든 git 서브프로세스 호출이 성공하면 committed=True와 새 커밋 sha를 반환하고,
실제 git commit 커맨드 인자에 PARTNER 페르소나 신원과 실행 ID가 포함되어 있어야 한다.
"""

import importlib.util
import os
import sys
import types
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

SOURCE_PATH = PROJECT_ROOT / "haness" / "source_repair.py"
SPEC = importlib.util.spec_from_file_location("haness_source_repair_under_test", SOURCE_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class _FakeCompletedProcess:
    """subprocess.run 결과를 흉내 낸다. stdout은 bytes로 유지한다."""

    def __init__(self, returncode: int = 0, stdout: bytes = b""):
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = b""


def test_auto_commit_uses_partner_persona_identity_not_human_account(monkeypatch, tmp_path):
    """git commit 호출에 사람 계정이 아닌 PARTNER 페르소나 신원이 --author로 들어가야 한다."""
    target = tmp_path / "example.py"
    target.write_text("print('x')\n", encoding="utf-8")
    monkeypatch.setattr(MODULE, "_root", lambda: tmp_path)

    calls = []

    def fake_run(cmd, **kwargs):
        calls.append({"cmd": cmd, "env": kwargs.get("env")})
        if cmd[:2] == ["git", "add"]:
            return _FakeCompletedProcess(returncode=0)
        if cmd[:2] == ["git", "commit"]:
            return _FakeCompletedProcess(returncode=0)
        if cmd[:2] == ["git", "rev-parse"]:
            return _FakeCompletedProcess(returncode=0, stdout=b"deadbeef1234\n")
        raise AssertionError(f"예상치 못한 git 호출: {cmd}")

    monkeypatch.setattr(MODULE.subprocess, "run", fake_run)

    result = MODULE._auto_commit(
        target,
        "[SPS 자동수정] example.py 패치 적용\n\n에이전트 실행 ID: run-001",
        "run-001",
    )

    assert result == {"committed": True, "commit": "deadbeef1234"}

    commit_call = next(c for c in calls if c["cmd"][:2] == ["git", "commit"])
    assert "--author" in commit_call["cmd"]
    author_value = commit_call["cmd"][commit_call["cmd"].index("--author") + 1]
    assert "SPS PARTNER" in author_value
    assert "run-001" in author_value  # 이메일에 실행 ID가 들어가 실행 단위까지 구분된다.
    assert "PARK" not in author_value.upper()  # 사람 계정 이름이 섞여 들어가지 않아야 한다.

    env = commit_call["env"]
    assert env["GIT_AUTHOR_NAME"] == "SPS PARTNER"
    assert env["GIT_COMMITTER_NAME"] == "SPS PARTNER"
    assert env["GIT_AUTHOR_EMAIL"] == "sps.partner+run-001@sps.local"
    assert env["GIT_COMMITTER_EMAIL"] == env["GIT_AUTHOR_EMAIL"]

    message_arg = commit_call["cmd"][commit_call["cmd"].index("-m") + 1]
    assert "[SPS 자동수정]" in message_arg  # 커밋 메시지가 한글 태그로 시작해야 한다.


def test_auto_commit_reports_failure_without_raising(monkeypatch, tmp_path):
    """git commit이 실패해도 예외를 던지지 않고 committed=False로 보고해야 한다."""
    target = tmp_path / "example.py"
    target.write_text("print('x')\n", encoding="utf-8")
    monkeypatch.setattr(MODULE, "_root", lambda: tmp_path)

    def fake_run(cmd, **kwargs):
        if cmd[:2] == ["git", "add"]:
            return _FakeCompletedProcess(returncode=0)
        if cmd[:2] == ["git", "commit"]:
            return _FakeCompletedProcess(returncode=1)
        raise AssertionError(f"예상치 못한 git 호출: {cmd}")

    monkeypatch.setattr(MODULE.subprocess, "run", fake_run)

    result = MODULE._auto_commit(target, "[SPS 자동수정] example.py 패치 적용", "run-002")

    assert result == {"committed": False, "commit": None, "error": "git commit 실패"}

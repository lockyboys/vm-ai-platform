"""apply_source_proposal(어느 AI든 수정 코드를 넘겨 적용) 테스트 (2026-11-10).

검증: dry_run 기본은 쓰기 없음 / 정상 적용 / 테스트 실패 시 되돌림 / 잘못된 입력 거부 /
      생략 기호·심볼 누락·없는 import·expected_sha256 불일치 거부.
LLM·실제 pytest는 실행하지 않는다(subprocess.run 대역).
"""
import hashlib
from types import SimpleNamespace

import pytest

from harness.mcp.tools import apply_proposal_tools as tool
from harness.mcp.tools import auto_apply

ORIGINAL = "def keep():\n    return 1\n"
FIXED = "def keep():\n    return 2\n"


@pytest.fixture
def repo(tmp_path, monkeypatch):
    """임시 저장소로 PROJECT_ROOT를 바꾸고 원본·테스트 파일을 만든다."""
    monkeypatch.setattr(tool, "PROJECT_ROOT", tmp_path)
    source = tmp_path / "pkg.py"
    source.write_text(ORIGINAL, encoding="utf-8")
    (tmp_path / "tests").mkdir()
    (tmp_path / "tests/test_pkg.py").write_text("def test_ok():\n    assert True\n", encoding="utf-8")
    return source


def _pytest_returns(monkeypatch, code):
    monkeypatch.setattr(auto_apply.subprocess, "run",
                        lambda *a, **k: SimpleNamespace(returncode=code, stdout=b"result"))


def test_dry_run_default_writes_nothing(repo, monkeypatch):
    monkeypatch.setattr(auto_apply.subprocess, "run", lambda *a, **k: pytest.fail("tests must not run"))
    plan = tool.apply_source_proposal("pkg.py", FIXED, test_paths=["tests/test_pkg.py"])
    assert plan["dry_run"] is True and plan["checks_passed"] is True and plan["applied"] is False
    assert repo.read_text(encoding="utf-8") == ORIGINAL


def test_apply_and_keep_when_tests_pass(repo, monkeypatch):
    _pytest_returns(monkeypatch, 0)
    sha = hashlib.sha256(repo.read_bytes()).hexdigest()
    result = tool.apply_source_proposal("pkg.py", FIXED, ["tests/test_pkg.py"], sha, dry_run=False)
    assert result["applied"] is True and repo.read_text(encoding="utf-8") == FIXED
    assert result["backup_path"].endswith("original.py")


def test_rollback_when_tests_fail(repo, monkeypatch):
    _pytest_returns(monkeypatch, 1)
    result = tool.apply_source_proposal("pkg.py", FIXED, ["tests/test_pkg.py"], dry_run=False)
    assert result["rolled_back"] is True and repo.read_text(encoding="utf-8") == ORIGINAL


@pytest.mark.parametrize("proposal,fragment", [
    ("def keep(:\n", "syntax"),                               # 문법 오류
    ("def keep():\n    ...\n", "Ellipsis"),                    # 생략 기호
    ("def other():\n    return 1\n", "drops existing"),        # 기존 함수 누락
    ("import no_such_pkg_20261110\n" + FIXED, "missing modules"),  # 없는 import
])
def test_bad_proposals_are_not_applied(repo, proposal, fragment):
    result = tool.apply_source_proposal("pkg.py", proposal, dry_run=False)
    assert result["applied"] is False and any(fragment in e for e in result["errors"])
    assert repo.read_text(encoding="utf-8") == ORIGINAL


def test_stale_expected_sha_blocks_apply(repo):
    result = tool.apply_source_proposal("pkg.py", FIXED, expected_sha256="0" * 64, dry_run=False)
    assert result["applied"] is False and repo.read_text(encoding="utf-8") == ORIGINAL


@pytest.mark.parametrize("kwargs", [
    {"source_path": "../escape.py", "proposed_source": FIXED},
    {"source_path": "missing.py", "proposed_source": FIXED},
    {"source_path": "pkg.py", "proposed_source": ""},
    {"source_path": "pkg.py", "proposed_source": FIXED, "expected_sha256": "xyz"},
    {"source_path": "pkg.py", "proposed_source": FIXED, "test_paths": ["pkg.py"]},
])
def test_invalid_input_rejected(repo, kwargs):
    """잘못된 입력: 경로 탈출, 없는 파일, 빈 제안, 잘못된 해시, 테스트 폴더 밖 경로."""
    with pytest.raises((ValueError, FileNotFoundError)):
        tool.apply_source_proposal(**kwargs)

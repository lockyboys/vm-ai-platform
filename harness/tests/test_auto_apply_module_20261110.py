"""재사용 모듈 harness.mcp.tools.auto_apply 직접 테스트 (2026-11-10).

다른 도구가 review_python_source 없이도 같은 자동 수정(백업→적용→검증→되돌림)을 쓸 수 있는지 확인한다.
LLM·systemd는 실행하지 않는다(pytest 호출은 subprocess.run 대역).
"""
import hashlib
from types import SimpleNamespace

import pytest

from harness.mcp.tools import auto_apply

ORIGINAL = "X = 1\n"
PROPOSED = "X = 2\n"


@pytest.fixture
def repo(tmp_path):
    """임시 저장소: 원본·제안·백업 폴더·테스트 파일을 만든다."""
    source = tmp_path / "pkg.py"
    source.write_text(ORIGINAL, encoding="utf-8")
    proposed = tmp_path / "proposed.py"
    proposed.write_text(PROPOSED, encoding="utf-8")
    job_dir = tmp_path / "job"
    job_dir.mkdir()
    (tmp_path / "tests").mkdir()
    (tmp_path / "tests/test_pkg.py").write_text("def test_ok():\n    assert True\n", encoding="utf-8")
    sha = hashlib.sha256(source.read_bytes()).hexdigest()
    return tmp_path, source, proposed, job_dir, sha


def test_apply_success(repo, monkeypatch):
    root, source, proposed, job_dir, sha = repo
    monkeypatch.setattr(auto_apply.subprocess, "run",
                        lambda *a, **k: SimpleNamespace(returncode=0, stdout=b"1 passed"))
    state = auto_apply.apply_with_rollback(source, proposed, job_dir, sha, ["tests/test_pkg.py"], 600, root)
    assert state["applied"] is True and source.read_text(encoding="utf-8") == PROPOSED
    assert (job_dir / "original.py").read_text(encoding="utf-8") == ORIGINAL


def test_rollback_on_test_failure(repo, monkeypatch):
    root, source, proposed, job_dir, sha = repo
    monkeypatch.setattr(auto_apply.subprocess, "run",
                        lambda *a, **k: SimpleNamespace(returncode=1, stdout=b"1 failed"))
    state = auto_apply.apply_with_rollback(source, proposed, job_dir, sha, ["tests/test_pkg.py"], 600, root)
    assert state["rolled_back"] is True and source.read_text(encoding="utf-8") == ORIGINAL


def test_wrong_expected_hash_does_not_touch_source(repo):
    root, source, proposed, job_dir, _ = repo
    state = auto_apply.apply_with_rollback(source, proposed, job_dir, "0" * 64, [], 600, root)
    assert state["applied"] is False and state["reason"] == "source changed during review"
    assert source.read_text(encoding="utf-8") == ORIGINAL


@pytest.mark.parametrize("bad", [["pkg.py"], ["../x.py"], [""], "tests/test_pkg.py", [None]])
def test_validate_rejects_bad_input(repo, bad):
    """잘못된 입력: 테스트 폴더 밖, 경로 탈출, 빈 문자열, 목록 아님, 문자열 아님."""
    root = repo[0]
    with pytest.raises((ValueError, FileNotFoundError)):
        auto_apply.validate_test_paths(bad, root)


def test_validate_accepts_test_file(repo):
    assert auto_apply.validate_test_paths(["tests/test_pkg.py"], repo[0]) == ["tests/test_pkg.py"]

"""git_commit이 이미 스테이징된 삭제 파일을 expected_paths로 받아들이는지 검증한다.

재현 버그(2026-10-25):
  git_stage_delete로 삭제를 스테이징하면 해당 경로가 index에서 빠져
  `git ls-files --error-unmatch`가 실패한다. 그 결과 git_commit이
  "Only tracked deleted files can be staged." 로 거부되어 삭제 포함 커밋이 불가능했다.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from harness.mcp.tools import git_mutation_tools


def _git(repo: Path, *args: str) -> None:
    """임시 저장소에서 git 명령을 실행한다(실패 시 즉시 예외)."""
    subprocess.run(["git", *args], cwd=repo, check=True, capture_output=True, text=True)


@pytest.fixture()
def repo(tmp_path, monkeypatch):
    """tracked 파일 2개가 커밋된 임시 Git 저장소를 만들고 도구 PROJECT_ROOT를 그곳으로 돌린다."""
    _git(tmp_path, "init", "-q")
    _git(tmp_path, "config", "user.email", "test@example.com")
    _git(tmp_path, "config", "user.name", "tester")
    (tmp_path / "old.md").write_text("old\n", encoding="utf-8")
    (tmp_path / "keep.md").write_text("keep\n", encoding="utf-8")
    _git(tmp_path, "add", "old.md", "keep.md")
    _git(tmp_path, "commit", "-q", "-m", "init")
    monkeypatch.setattr(git_mutation_tools, "PROJECT_ROOT", tmp_path)
    return tmp_path


def test_commit_accepts_already_staged_deletion(repo):
    """삭제 스테이징 + 신규 파일 추가를 한 커밋으로 묶을 수 있어야 한다."""
    (repo / "old.md").unlink()
    git_mutation_tools.git_stage_delete(["old.md"], dry_run=False)
    (repo / "new.md").write_text("new\n", encoding="utf-8")
    git_mutation_tools.git_add(["new.md"], dry_run=False)

    result = git_mutation_tools.git_commit("docs: rename", ["old.md", "new.md"], dry_run=False)

    assert result["committed"] is True
    assert result["committed_paths"] == ["new.md", "old.md"]


def test_commit_still_rejects_untracked_missing_path(repo):
    """잘못된 입력: 추적된 적도, 스테이징된 적도 없는 없는 파일은 계속 거부해야 한다."""
    (repo / "x.md").write_text("x\n", encoding="utf-8")
    git_mutation_tools.git_add(["x.md"], dry_run=False)
    with pytest.raises(ValueError, match="Only tracked deleted files"):
        git_mutation_tools.git_commit("bad", ["x.md", "ghost.md"], dry_run=True)


def test_stage_delete_rejects_existing_file(repo):
    """잘못된 입력: 존재하는 파일은 git_stage_delete가 거부해야 한다(기존 동작 유지)."""
    with pytest.raises(ValueError, match="already-deleted"):
        git_mutation_tools.git_stage_delete(["keep.md"], dry_run=True)

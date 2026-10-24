"""git_stage_manage(스테이징 조회·추가·삭제반영·해제·전체해제·선택만 유지) 도구 검증.

배경(2026-10-25): 다른 세션이 올린 스테이징이나 잘못 올린 삭제를 내릴 도구가 없어
git_commit(정확한 staged 집합 요구)이 막혔다. 이 도구는 Git index만 바꾸고
작업 트리 파일은 절대 바꾸지 않아야 한다.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from harness.mcp.tools import git_mutation_tools as gm


def _git(repo: Path, *args: str) -> str:
    """임시 저장소에서 git 명령을 실행하고 stdout을 돌려준다."""
    return subprocess.run(["git", *args], cwd=repo, check=True, capture_output=True, text=True).stdout


@pytest.fixture()
def repo(tmp_path, monkeypatch):
    """a.md, b.md, gone.md가 커밋된 임시 저장소. 도구 PROJECT_ROOT를 이곳으로 돌린다."""
    _git(tmp_path, "init", "-q")
    _git(tmp_path, "config", "user.email", "t@example.com")
    _git(tmp_path, "config", "user.name", "t")
    for name in ("a.md", "b.md", "gone.md"):
        (tmp_path / name).write_text(name + "\n", encoding="utf-8")
    _git(tmp_path, "add", "a.md", "b.md", "gone.md")
    _git(tmp_path, "commit", "-q", "-m", "init")
    monkeypatch.setattr(gm, "PROJECT_ROOT", tmp_path)
    # 공통 상태: a.md 수정, new.md 신규, gone.md 삭제를 모두 스테이징
    (tmp_path / "a.md").write_text("changed\n", encoding="utf-8")
    (tmp_path / "new.md").write_text("new\n", encoding="utf-8")
    (tmp_path / "gone.md").unlink()
    _git(tmp_path, "add", "a.md", "new.md")
    _git(tmp_path, "add", "--update", "gone.md")
    return tmp_path


def test_status_lists_staged_with_change_type(repo):
    result = gm.git_stage_manage("status")
    assert result["staged"] == [
        {"status": "M", "path": "a.md"},
        {"status": "D", "path": "gone.md"},
        {"status": "A", "path": "new.md"},
    ]


def test_unstage_dry_run_changes_nothing(repo):
    result = gm.git_stage_manage("unstage", ["gone.md"], dry_run=True)
    assert result["would_unstage"] == ["gone.md"]
    assert "gone.md" in gm._staged_paths()


def test_unstage_staged_delete_keeps_worktree(repo):
    """잘못 올린 삭제를 내린다. 작업 트리의 삭제 상태(파일 없음)는 그대로여야 한다."""
    result = gm.git_stage_manage("unstage", ["gone.md"], dry_run=False)
    assert result["unstaged"] == ["gone.md"]
    assert result["staged_after"] == ["a.md", "new.md"]
    assert not (repo / "gone.md").exists()


def test_unstage_new_file_keeps_file_on_disk(repo):
    gm.git_stage_manage("unstage", ["new.md"], dry_run=False)
    assert "new.md" not in gm._staged_paths()
    assert (repo / "new.md").read_text(encoding="utf-8") == "new\n"


def test_unstage_modified_keeps_worktree_content(repo):
    gm.git_stage_manage("unstage", ["a.md"], dry_run=False)
    assert "a.md" not in gm._staged_paths()
    assert (repo / "a.md").read_text(encoding="utf-8") == "changed\n"


def test_unstage_all(repo):
    result = gm.git_stage_manage("unstage_all", dry_run=False)
    assert result["unstaged"] == ["a.md", "gone.md", "new.md"]
    assert gm._staged_paths() == []


def test_keep_only_unstages_everything_else(repo):
    result = gm.git_stage_manage("keep_only", ["new.md"], dry_run=False)
    assert result["unstaged"] == ["a.md", "gone.md"]
    assert gm._staged_paths() == ["new.md"]


def test_stage_and_stage_delete_delegate(repo):
    gm.git_stage_manage("unstage_all", dry_run=False)
    gm.git_stage_manage("stage", ["new.md"], dry_run=False)
    gm.git_stage_manage("stage_delete", ["gone.md"], dry_run=False)
    assert gm._staged_paths() == ["gone.md", "new.md"]


# ---- 잘못된 입력 ----

def test_rejects_unknown_action(repo):
    with pytest.raises(ValueError, match="Unknown action"):
        gm.git_stage_manage("reset_hard", ["a.md"])


def test_unstage_rejects_not_staged_path(repo):
    with pytest.raises(ValueError, match="not staged"):
        gm.git_stage_manage("unstage", ["b.md"], dry_run=True)


@pytest.mark.parametrize("bad", ["/etc/passwd", "../x.md", "", "a/./b.md"])
def test_unstage_rejects_unsafe_paths(repo, bad):
    with pytest.raises(ValueError):
        gm.git_stage_manage("unstage", [bad], dry_run=True)


def test_unstage_requires_paths(repo):
    with pytest.raises(ValueError, match="At least one"):
        gm.git_stage_manage("unstage", [], dry_run=True)


def test_unstage_all_rejects_paths_argument(repo):
    with pytest.raises(ValueError, match="does not take paths"):
        gm.git_stage_manage("unstage_all", ["a.md"], dry_run=True)


def test_unstage_all_with_nothing_staged(repo):
    gm.git_stage_manage("unstage_all", dry_run=False)
    with pytest.raises(ValueError, match="no staged"):
        gm.git_stage_manage("unstage_all", dry_run=True)

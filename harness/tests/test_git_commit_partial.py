"""git_commit(keep_other_staged=True): 지정 파일만 커밋하고 나머지 staged는 그대로 둔다.

요구(2026-10-25): stage를 여러 번 누적한 뒤 그룹별로 나눠 커밋하고 싶다.
안전 규칙:
- expected_paths는 모두 현재 staged여야 한다(하나라도 아니면 거부).
- 지정 파일에 staged 이후 작업 트리 변경이 남아 있으면 거부한다
  (git commit --only는 작업 트리 내용을 커밋하므로 staged 내용과 달라질 수 있음).
- 기본값 False이면 기존처럼 "staged 집합 == expected_paths"를 요구한다.
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
    """a.md, b.md, gone.md 커밋 후 a 수정·new 추가·gone 삭제·b 수정을 모두 staged로 둔다."""
    _git(tmp_path, "init", "-q")
    _git(tmp_path, "config", "user.email", "t@example.com")
    _git(tmp_path, "config", "user.name", "t")
    for name in ("a.md", "b.md", "gone.md"):
        (tmp_path / name).write_text(name + "\n", encoding="utf-8")
    _git(tmp_path, "add", "a.md", "b.md", "gone.md")
    _git(tmp_path, "commit", "-q", "-m", "init")
    monkeypatch.setattr(gm, "PROJECT_ROOT", tmp_path)
    (tmp_path / "a.md").write_text("a2\n", encoding="utf-8")
    (tmp_path / "b.md").write_text("b2\n", encoding="utf-8")
    (tmp_path / "new.md").write_text("new\n", encoding="utf-8")
    (tmp_path / "gone.md").unlink()
    _git(tmp_path, "add", "a.md", "b.md", "new.md")
    _git(tmp_path, "add", "--update", "gone.md")
    return tmp_path


def _last_commit_files(repo: Path) -> list[str]:
    return sorted(_git(repo, "show", "--name-only", "--format=", "HEAD").split())


def test_partial_commit_keeps_other_staged(repo):
    result = gm.git_commit("part1", ["a.md", "new.md"], dry_run=False, keep_other_staged=True)
    assert result["committed_paths"] == ["a.md", "new.md"]
    assert _last_commit_files(repo) == ["a.md", "new.md"]
    assert result["remaining_staged_paths"] == ["b.md", "gone.md"]


def test_partial_commit_with_staged_delete(repo):
    gm.git_commit("del", ["gone.md"], dry_run=False, keep_other_staged=True)
    assert _last_commit_files(repo) == ["gone.md"]
    assert gm._staged_paths() == ["a.md", "b.md", "new.md"]


def test_partial_commit_dry_run_changes_nothing(repo):
    head_before = _git(repo, "rev-parse", "HEAD")
    result = gm.git_commit("x", ["a.md"], dry_run=True, keep_other_staged=True)
    assert result["would_commit"] is True
    assert result["would_remain_staged"] == ["b.md", "gone.md", "new.md"]
    assert _git(repo, "rev-parse", "HEAD") == head_before


def test_successive_partial_commits_split_groups(repo):
    gm.git_commit("g1", ["a.md"], dry_run=False, keep_other_staged=True)
    gm.git_commit("g2", ["b.md", "gone.md"], dry_run=False, keep_other_staged=True)
    gm.git_commit("g3", ["new.md"], dry_run=False)  # 마지막은 기존 방식(정확 일치)
    assert gm._staged_paths() == []
    assert _last_commit_files(repo) == ["new.md"]


# ---- 잘못된 입력 ----

def test_partial_commit_rejects_not_staged_path(repo):
    (repo / "c.md").write_text("c\n", encoding="utf-8")
    with pytest.raises(ValueError, match="not staged"):
        gm.git_commit("bad", ["a.md", "c.md"], dry_run=True, keep_other_staged=True)


def test_partial_commit_rejects_unstaged_worktree_change(repo):
    """staged 이후 작업 트리가 또 바뀐 파일은 staged 내용과 달라지므로 거부."""
    (repo / "a.md").write_text("a3-not-staged\n", encoding="utf-8")
    with pytest.raises(ValueError, match="unstaged changes"):
        gm.git_commit("bad", ["a.md"], dry_run=True, keep_other_staged=True)


def test_default_still_requires_exact_match(repo):
    with pytest.raises(ValueError, match="do not exactly match"):
        gm.git_commit("bad", ["a.md"], dry_run=True)

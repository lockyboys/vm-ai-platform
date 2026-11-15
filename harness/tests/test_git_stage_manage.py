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


# =============================================================================
# uncommit (2026-11-14, LuckyBoys 요청): 커밋을 풀어 스테이징 상태로 되돌리기
# -----------------------------------------------------------------------------
# 배경: 다른 세션이 기능을 섞어 커밋해(a7c2fca 등) 다시 나눠 커밋해야 하는데 푸는 도구가 없었다.
#       MCP 도구 수를 늘리지 않으려고 git_stage_manage의 동작(action)으로 넣는다.
# 기대: git reset --soft <target_commit> 과 같다 — 파일 내용은 그대로, 커밋만 풀려 staged가 된다.
#       풀기 전 HEAD는 백업 ref(config.GIT_UNCOMMIT_BACKUP_REF_PREFIX-날짜)에 남겨 되돌릴 수 있게 한다.
# =============================================================================
@pytest.fixture()
def history(tmp_path, monkeypatch):
    """init → c1(x.md) → c2(y.md 추가, x.md 수정) 커밋, index 비어 있음. 커밋 해시 목록을 돌려준다."""
    _git(tmp_path, "init", "-q")
    _git(tmp_path, "config", "user.email", "t@example.com")
    _git(tmp_path, "config", "user.name", "t")
    shas = []
    for name, body in (("base.md", "base\n"), ("x.md", "x1\n"), ("y.md", "y1\n")):
        if name == "y.md":
            (tmp_path / "x.md").write_text("x2\n", encoding="utf-8")
            _git(tmp_path, "add", "x.md")
        (tmp_path / name).write_text(body, encoding="utf-8")
        _git(tmp_path, "add", name)
        _git(tmp_path, "commit", "-q", "-m", f"add {name}")
        shas.append(_git(tmp_path, "rev-parse", "HEAD").strip())
    monkeypatch.setattr(gm, "PROJECT_ROOT", tmp_path)
    return tmp_path, shas


def test_reproduce_uncommit_two_commits_to_staged(history):
    """재현: 커밋 2개를 풀면 HEAD가 기준 커밋으로 가고, 두 커밋의 파일이 staged, 파일 내용은 그대로."""
    repo, (base, c1, c2) = history
    result = gm.git_stage_manage("uncommit", target_commit=base, dry_run=False)
    assert _git(repo, "rev-parse", "HEAD").strip() == base
    assert result["staged_after"] == ["x.md", "y.md"]
    assert [c["sha"] for c in result["uncommitted"]] == [c2, c1]
    assert (repo / "x.md").read_text(encoding="utf-8") == "x2\n"   # 작업 파일은 안 바뀜
    assert _git(repo, "rev-parse", result["backup_ref"]).strip() == c2  # 되돌릴 수 있게 보존


def test_uncommit_dry_run_changes_nothing(history):
    """dry-run은 계획만: HEAD·index 그대로, 풀릴 커밋과 파일 목록만 돌려준다."""
    repo, (base, c1, c2) = history
    plan = gm.git_stage_manage("uncommit", target_commit=base[:10], dry_run=True)
    assert plan["dry_run"] is True and plan["would_stage"] == ["x.md", "y.md"]
    assert len(plan["uncommitted"]) == 2
    assert _git(repo, "rev-parse", "HEAD").strip() == c2
    assert _git(repo, "diff", "--cached", "--name-only").strip() == ""


@pytest.mark.parametrize("bad", [None, "", "HEAD", "HEAD~1", "zzzzzzz", "abc12", "a" * 41, "main"])
def test_uncommit_rejects_bad_target(history, bad):
    """잘못된 입력: 7~40자리 16진수 커밋 id만 받는다(HEAD~1·브랜치 이름·짧은 값 거부)."""
    with pytest.raises(ValueError):
        gm.git_stage_manage("uncommit", target_commit=bad, dry_run=True)


def test_uncommit_rejects_unknown_and_head(history):
    """없는 커밋, 지금 HEAD 자체는 거부."""
    _repo, (_base, _c1, c2) = history
    with pytest.raises(ValueError, match="Unknown commit"):
        gm.git_stage_manage("uncommit", target_commit="0123456789abcdef", dry_run=True)
    with pytest.raises(ValueError, match="nothing to uncommit"):
        gm.git_stage_manage("uncommit", target_commit=c2, dry_run=True)


def test_uncommit_rejects_non_ancestor(history):
    """HEAD의 조상이 아닌 커밋(다른 갈래)으로는 풀지 않는다."""
    repo, (base, _c1, c2) = history
    _git(repo, "checkout", "-q", "-b", "side", base)
    (repo / "s.md").write_text("s\n", encoding="utf-8")
    _git(repo, "add", "s.md")
    _git(repo, "commit", "-q", "-m", "side")
    side = _git(repo, "rev-parse", "HEAD").strip()
    _git(repo, "checkout", "-q", "-")
    with pytest.raises(ValueError, match="ancestor"):
        gm.git_stage_manage("uncommit", target_commit=side, dry_run=True)


def test_uncommit_rejects_when_index_not_empty(history):
    """이미 staged 파일이 있으면 섞이지 않게 거부(먼저 unstage)."""
    repo, (base, _c1, _c2) = history
    (repo / "base.md").write_text("changed\n", encoding="utf-8")
    _git(repo, "add", "base.md")
    with pytest.raises(ValueError, match="Index must be empty"):
        gm.git_stage_manage("uncommit", target_commit=base, dry_run=True)


def test_uncommit_rejects_over_limit(history, monkeypatch):
    """한 번에 풀 수 있는 커밋 수(config.GIT_UNCOMMIT_MAX_COMMITS)를 넘으면 거부."""
    _repo, (base, _c1, _c2) = history
    monkeypatch.setattr(gm.project_config, "GIT_UNCOMMIT_MAX_COMMITS", 1)
    with pytest.raises(ValueError, match="limit"):
        gm.git_stage_manage("uncommit", target_commit=base, dry_run=True)


def test_uncommit_rejects_pushed_commits(history, tmp_path_factory):
    """원격에 이미 올라간(push된) 커밋은 풀지 않는다(공유 기록 보호)."""
    repo, (base, _c1, _c2) = history
    remote = tmp_path_factory.mktemp("remote")
    _git(remote, "init", "-q", "--bare")
    _git(repo, "remote", "add", "origin", str(remote))
    _git(repo, "push", "-q", "origin", "HEAD:refs/heads/main")
    _git(repo, "fetch", "-q", "origin")
    with pytest.raises(ValueError, match="pushed"):
        gm.git_stage_manage("uncommit", target_commit=base, dry_run=True)


def test_uncommit_takes_no_paths(history):
    """uncommit은 paths를 받지 않는다(파일 일부만 푸는 기능이 아님)."""
    _repo, (base, _c1, _c2) = history
    with pytest.raises(ValueError, match="does not take paths"):
        gm.git_stage_manage("uncommit", ["x.md"], target_commit=base, dry_run=True)

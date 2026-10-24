"""Regression tests for explicit Harness deletion, deletion staging, and test paths."""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from harness.mcp.tools import git_mutation_tools, patch_tools, pytest_tools


def _completed(returncode: int = 0, stdout: str = "", stderr: str = ""):
    return subprocess.CompletedProcess([], returncode, stdout, stderr)


def test_source_delete_is_dry_run_then_deletes_one_tracked_file(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    target = tmp_path / "utils.py"
    target.write_text("logger = object()\n", encoding="utf-8")
    monkeypatch.setattr(patch_tools, "PROJECT_ROOT", tmp_path)
    monkeypatch.setattr(
        patch_tools.subprocess,
        "run",
        lambda *args, **kwargs: _completed(),
    )

    preview = patch_tools.source_delete("utils.py")
    assert preview["would_delete"] is True
    assert target.exists()

    result = patch_tools.source_delete("utils.py", dry_run=False)
    assert result["deleted"] is True
    assert not target.exists()


def test_source_delete_rejects_untracked_file(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    target = tmp_path / "scratch.py"
    target.write_text("pass\n", encoding="utf-8")
    monkeypatch.setattr(patch_tools, "PROJECT_ROOT", tmp_path)
    monkeypatch.setattr(
        patch_tools.subprocess,
        "run",
        lambda *args, **kwargs: _completed(returncode=1),
    )

    with pytest.raises(ValueError, match="tracked"):
        patch_tools.source_delete("scratch.py")


def test_git_stage_delete_rejects_existing_file(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    target = tmp_path / "utils.py"
    target.write_text("pass\n", encoding="utf-8")
    monkeypatch.setattr(git_mutation_tools, "PROJECT_ROOT", tmp_path)

    with pytest.raises(ValueError, match="already-deleted"):
        git_mutation_tools.git_stage_delete(["utils.py"])


def test_git_stage_delete_allows_one_missing_tracked_file(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setattr(git_mutation_tools, "PROJECT_ROOT", tmp_path)
    calls: list[list[str]] = []

    def fake_run(arguments: list[str]):
        calls.append(arguments)
        if arguments[0] == "ls-files":
            return _completed(stdout="utils.py\n")
        if arguments[0] == "diff":
            return _completed(stdout="utils.py\n")
        return _completed()

    monkeypatch.setattr(git_mutation_tools, "_run_git", fake_run)

    result = git_mutation_tools.git_stage_delete(["utils.py"], dry_run=True)
    assert result["requested_paths"] == ["utils.py"]
    assert result["staged_paths"] == ["utils.py"]
    assert ["add", "--update", "--dry-run", "--verbose", "--", "utils.py"] in calls


def test_pytest_verification_accepts_only_tests_directory(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    test_path = tmp_path / "tests" / "test_sample.py"
    test_path.parent.mkdir()
    test_path.write_text("def test_sample():\n    assert True\n", encoding="utf-8")
    monkeypatch.setattr(pytest_tools, "PROJECT_ROOT", tmp_path)

    assert pytest_tools._validate_test_paths(["tests/test_sample.py"]) == [
        "tests/test_sample.py"
    ]
    with pytest.raises(ValueError, match="Only tests/"):
        pytest_tools._validate_test_paths(["harness/mcp/tools/patch_tools.py"])


def test_pytest_verification_runs_in_fresh_subprocess(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    test_path = tmp_path / "tests" / "test_async_sample.py"
    test_path.parent.mkdir()
    test_path.write_text(
        "import asyncio\n\n"
        "def test_asyncio_run_isolated():\n"
        "    assert asyncio.run(_answer()) == 42\n\n"
        "async def _answer():\n"
        "    return 42\n",
        encoding="utf-8",
    )
    monkeypatch.setattr(pytest_tools, "PROJECT_ROOT", tmp_path)

    result = pytest_tools.run_pytest_verification(
        ["tests/test_async_sample.py"],
        title="Fresh subprocess verification",
    )

    assert result["success"] is True
    assert result["exit_code"] == 0
    assert len(result["results"]) == 1
    assert result["results"][0]["status"] == "PASSED"
    assert result["results"][0]["node_id"].endswith(
        "test_asyncio_run_isolated")
    assert "asyncio.run() cannot be called" not in result["raw_stdout"]


def _git(repo: Path, *arguments: str, input_text: str | None = None) -> subprocess.CompletedProcess[str]:
    """격리 저장소에서 Git 명령을 실행하고 실패 원인을 테스트에 그대로 남긴다."""
    return subprocess.run(
        ["git", *arguments],
        cwd=repo,
        input=input_text,
        text=True,
        capture_output=True,
        check=True,
    )


def _partial_stage_repository(tmp_path: Path) -> tuple[Path, str]:
    """서로 떨어진 두 변경 중 첫 hunk만 선택할 수 있는 저장소를 만든다."""
    _git(tmp_path, "init")
    _git(tmp_path, "config", "user.email", "test@example.com")
    _git(tmp_path, "config", "user.name", "SPS Test")
    target = tmp_path / "sample.py"
    target.write_text("first = 1\nkeep_a = 1\nkeep_b = 1\nlast = 1\n", encoding="utf-8")
    _git(tmp_path, "add", "sample.py")
    _git(tmp_path, "commit", "-m", "baseline")
    target.write_text("first = 2\nkeep_a = 1\nkeep_b = 1\nlast = 2\n", encoding="utf-8")
    selected_patch = (
        "--- a/sample.py\n"
        "+++ b/sample.py\n"
        "@@ -1 +1 @@\n"
        "-first = 1\n"
        "+first = 2\n"
    )
    return target, selected_patch


def test_git_apply_cached_patch_stages_only_selected_hunk(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """선택 patch만 index에 반영하고 작업 파일의 나머지 변경은 보존해야 한다."""
    target, selected_patch = _partial_stage_repository(tmp_path)
    monkeypatch.setattr(git_mutation_tools, "PROJECT_ROOT", tmp_path)
    original_worktree = target.read_text(encoding="utf-8")

    preview = git_mutation_tools.git_apply_cached_patch(
        selected_patch, ["sample.py"], dry_run=True)
    assert preview["applicable"] is True
    assert _git(tmp_path, "diff", "--cached").stdout == ""

    result = git_mutation_tools.git_apply_cached_patch(
        selected_patch, ["sample.py"], dry_run=False)
    staged = _git(tmp_path, "diff", "--cached", "--", "sample.py").stdout
    unstaged = _git(tmp_path, "diff", "--", "sample.py").stdout
    assert result["staged"] is True
    assert "+first = 2" in staged and "+last = 2" not in staged
    assert "+last = 2" in unstaged
    assert target.read_text(encoding="utf-8") == original_worktree


def test_git_apply_cached_patch_rejects_unrelated_or_invented_changes(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """예상 경로가 다르거나 worktree에 없는 변경은 index를 오염시키지 않는다."""
    _, selected_patch = _partial_stage_repository(tmp_path)
    monkeypatch.setattr(git_mutation_tools, "PROJECT_ROOT", tmp_path)

    with pytest.raises(ValueError, match="expected_paths"):
        git_mutation_tools.git_apply_cached_patch(
            selected_patch, ["other.py"], dry_run=False)
    invented_patch = selected_patch.replace("+first = 2", "+first = 999")
    with pytest.raises(ValueError, match="working tree"):
        git_mutation_tools.git_apply_cached_patch(
            invented_patch, ["sample.py"], dry_run=False)
    assert _git(tmp_path, "diff", "--cached").stdout == ""

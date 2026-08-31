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
    assert result["results"][0].status == "PASSED"
    assert "asyncio.run() cannot be called" not in result["raw_stdout"]

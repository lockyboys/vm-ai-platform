"""Regression tests for the explicit Harness source rename tool."""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from harness.mcp.tools import patch_tools


def _completed(returncode: int = 0):
    return subprocess.CompletedProcess([], returncode, "", "")


def test_source_rename_is_dry_run_then_preserves_content(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    source = tmp_path / "utils.py"
    destination = tmp_path / "utils_backup_20260830.py"
    source.write_text("logger = object()\n", encoding="utf-8")
    monkeypatch.setattr(patch_tools, "PROJECT_ROOT", tmp_path)
    monkeypatch.setattr(
        patch_tools.subprocess,
        "run",
        lambda *args, **kwargs: _completed(),
    )

    preview = patch_tools.source_rename(
        "utils.py",
        "utils_backup_20260830.py",
    )
    assert preview["would_rename"] is True
    assert source.exists()
    assert not destination.exists()

    result = patch_tools.source_rename(
        "utils.py",
        "utils_backup_20260830.py",
        dry_run=False,
    )
    assert result["renamed"] is True
    assert result["content_preserved"] is True
    assert result["before_sha256"] == result["after_sha256"]
    assert not source.exists()
    assert destination.read_text(encoding="utf-8") == "logger = object()\n"


def test_source_rename_rejects_existing_destination(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    source = tmp_path / "utils.py"
    destination = tmp_path / "utils_backup_20260830.py"
    source.write_text("source\n", encoding="utf-8")
    destination.write_text("existing\n", encoding="utf-8")
    monkeypatch.setattr(patch_tools, "PROJECT_ROOT", tmp_path)

    with pytest.raises(ValueError, match="already exists"):
        patch_tools.source_rename(
            "utils.py",
            "utils_backup_20260830.py",
        )

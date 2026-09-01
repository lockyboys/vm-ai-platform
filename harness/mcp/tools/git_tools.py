# =============================================================================
# File Name   : harness/mcp/tools/git_tools.py
# Purpose     : 지금 바뀐 파일과 차이점을 확인하는 Git 조회 도구
# =============================================================================
# CHANGE HISTORY
# =============================================================================
# 20260902 | Codex | Harness 표준 파일 헤더와 미커밋 변경 보존 역할을 보강했음
# =============================================================================
# 이 파일은 무엇을 하나요?
# - git_status는 어떤 파일이 바뀌었는지 보여 줍니다.
# - git_diff는 파일에서 무엇이 달라졌는지 보여 줍니다.
# 주의: 이 파일은 읽기만 하며, 파일을 저장하거나 커밋하지 않습니다.
from __future__ import annotations

import subprocess
from pathlib import Path
from harness.mcp.formatters import format_git_status


PROJECT_ROOT = Path("/data/vm_project")

DEFAULT_MAX_LINES = 500
MAX_ALLOWED_LINES = 2000


def git_status() -> dict:
    """Return the current Git working tree status."""

    result = subprocess.run(
        [
            "git",
            "status",
            "--short",
        ],
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    if result.returncode != 0:
        raise RuntimeError(
            result.stderr.strip()
            or "git status failed."
        )

    status_result = {
        "status": result.stdout.splitlines(),
    }

    status_result["pretty_output"] = format_git_status(
        status_result
    )

    return status_result


def git_diff(
    path: str | None = None,
    staged: bool = False,
    max_lines: int = DEFAULT_MAX_LINES,
) -> dict:
    """Return the current Git diff for the project or one path."""

    normalized_max_lines = max(
        1,
        min(max_lines, MAX_ALLOWED_LINES),
    )

    command = [
        "git",
        "diff",
        "--no-ext-diff",
        "--no-color",
    ]

    if staged:
        command.append("--cached")

    normalized_path: str | None = None

    if path is not None:
        normalized_path = path.strip()

        if not normalized_path:
            normalized_path = None

    if normalized_path is not None:
        requested_path = (
            PROJECT_ROOT
            / normalized_path
        ).resolve()

        project_root = PROJECT_ROOT.resolve()

        if (
            requested_path != project_root
            and project_root not in requested_path.parents
        ):
            raise ValueError(
                "The requested path is outside the project root."
            )

        command.extend(
            [
                "--",
                normalized_path,
            ]
        )

    result = subprocess.run(
        command,
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    if result.returncode != 0:
        raise RuntimeError(
            result.stderr.strip()
            or "git diff failed."
        )

    diff_lines = result.stdout.splitlines()
    truncated = len(diff_lines) > normalized_max_lines

    return {
        "path": normalized_path,
        "staged": staged,
        "total_lines": len(diff_lines),
        "returned_lines": min(
            len(diff_lines),
            normalized_max_lines,
        ),
        "truncated": truncated,
        "diff": diff_lines[:normalized_max_lines],
    }
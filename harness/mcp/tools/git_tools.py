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

# Git queries must fail promptly instead of pinning an MCP request indefinitely.
GIT_TIMEOUT_SECONDS = 30
MAX_HISTORY_COMMITS = 100
MAX_BLAME_LINES = 200


def _run_git(command: list[str]) -> subprocess.CompletedProcess[str]:
    """Run a read-only Git query with a hard timeout and actionable errors."""
    try:
        return subprocess.run(
            command,
            cwd=PROJECT_ROOT,
            capture_output=True,
            text=True,
            check=False,
            timeout=GIT_TIMEOUT_SECONDS,
        )
    except subprocess.TimeoutExpired as exc:
        raise TimeoutError(
            f"Git query exceeded {GIT_TIMEOUT_SECONDS} seconds."
        ) from exc


def _validate_repo_file(path: str) -> str:
    """Accept only an existing file within the configured repository root."""
    normalized = path.strip()
    if not normalized:
        raise ValueError("A non-empty repository-relative file path is required.")
    requested = (PROJECT_ROOT / normalized).resolve()
    root = PROJECT_ROOT.resolve()
    if requested == root or root not in requested.parents or not requested.is_file():
        raise ValueError("The requested path must be an existing file inside the project root.")
    return requested.relative_to(root).as_posix()


def git_status() -> dict:
    """Return the current Git working tree status."""

    result = _run_git(["git", "status", "--short"])

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


def git_log(path: str | None = None, limit: int = 20) -> dict:
    """Return bounded recent commit summaries, optionally for one repo file."""
    normalized_limit = max(1, min(int(limit), MAX_HISTORY_COMMITS))
    command = [
        "git", "log", "--no-color", "--date=iso-strict",
        "--format=%H%x09%an%x09%ad%x09%s", f"-n{normalized_limit}",
    ]
    normalized_path = None
    if path is not None:
        normalized_path = _validate_repo_file(path)
        command.extend(["--", normalized_path])
    result = _run_git(command)
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or "git log failed.")
    commits = result.stdout.splitlines()
    return {"path": normalized_path, "limit": normalized_limit, "commits": commits}


def git_blame(path: str, start_line: int = 1, end_line: int | None = None) -> dict:
    """Return attribution for a bounded line range in one repository file."""
    normalized_path = _validate_repo_file(path)
    if start_line < 1 or (end_line is not None and end_line < start_line):
        raise ValueError("Blame line range must be positive and ordered.")
    normalized_end = end_line if end_line is not None else start_line + MAX_BLAME_LINES - 1
    if normalized_end - start_line + 1 > MAX_BLAME_LINES:
        raise ValueError(f"Blame range cannot exceed {MAX_BLAME_LINES} lines.")
    result = _run_git([
        "git", "blame", "--date=short", "-L", f"{start_line},{normalized_end}",
        "--", normalized_path,
    ])
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or "git blame failed.")
    lines = result.stdout.splitlines()
    return {"path": normalized_path, "start_line": start_line,
            "end_line": normalized_end, "returned_lines": len(lines), "blame": lines}


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

    result = _run_git(command)

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
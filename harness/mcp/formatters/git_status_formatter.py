from __future__ import annotations

from collections.abc import Mapping, Sequence
from typing import Any

from src.common.formatter import PrettyOutput


def format_git_status(result: Mapping[str, Any]) -> str:
    """
    git status --short 결과를 PrettyOutput 형식으로 변환한다.

    입력 예:
        {
            "status": [
                " M .gitignore",
                "?? src/common/formatter/pretty_output.py",
            ]
        }
    """

    status_lines = _normalize_status_lines(
        result.get("status")
    )

    rows: list[list[str]] = []

    staged_count = 0
    modified_count = 0
    untracked_count = 0
    deleted_count = 0
    renamed_count = 0
    conflicted_count = 0

    for line in status_lines:
        status_code, file_name = _parse_status_line(line)

        rows.append(
            [
                status_code,
                file_name,
            ]
        )

        index_status = (
            status_code[0]
            if len(status_code) >= 1
            else " "
        )

        worktree_status = (
            status_code[1]
            if len(status_code) >= 2
            else " "
        )

        if status_code == "??":
            untracked_count += 1
            continue

        if index_status not in {" ", "?"}:
            staged_count += 1

        if "M" in status_code:
            modified_count += 1

        if "D" in status_code:
            deleted_count += 1

        if "R" in status_code:
            renamed_count += 1

        if (
            "U" in status_code
            or status_code in {
                "AA",
                "DD",
            }
        ):
            conflicted_count += 1

    output = PrettyOutput("Git Status").summary(
        Files=len(status_lines),
        Staged=staged_count,
        Modified=modified_count,
        Untracked=untracked_count,
        Deleted=deleted_count,
        Renamed=renamed_count,
        Conflicted=conflicted_count,
    )

    if rows:
        output.table(
            columns=[
                "Status",
                "File",
            ],
            rows=rows,
        )
    else:
        output.body(
            "Working tree clean."
        )

    return output.success().render()


def _normalize_status_lines(
    value: Any,
) -> list[str]:
    if value is None:
        return []

    if isinstance(value, str):
        return [
            line
            for line in value.splitlines()
            if line.strip()
        ]

    if isinstance(value, Sequence):
        return [
            str(line)
            for line in value
            if str(line).strip()
        ]

    raise TypeError(
        "Git status result must be a string or sequence."
    )


def _parse_status_line(
    line: str,
) -> tuple[str, str]:
    """
    git status --short 한 줄을 상태 코드와 파일명으로 분리한다.

    예:
        ' M file.py'   -> (' M', 'file.py')
        'M  file.py'   -> ('M ', 'file.py')
        '?? file.py'   -> ('??', 'file.py')
    """

    if len(line) < 3:
        return (
            line.strip() or "-",
            "-",
        )

    status_code = line[:2]
    file_name = line[3:].strip()

    return (
        status_code,
        file_name or "-",
    )

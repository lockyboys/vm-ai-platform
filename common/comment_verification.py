"""Reusable helpers for database table and column COMMENT reviews."""

from __future__ import annotations

from typing import Any


def review_status(current_comment: str | None, proposed_comment: str | None) -> str:
    """Return whether a proposed COMMENT changes the current COMMENT."""
    return "UNCHANGED" if current_comment == proposed_comment else "REVIEW_REQUIRED"


def is_current_table_comment_preserved(
    current_comment: str | None,
    proposed_comment: str | None,
) -> bool:
    """Return True when the proposed table COMMENT starts with the current text."""
    current = current_comment or ""
    proposed = proposed_comment or ""
    return proposed.startswith(current)


def summarize_comment_review(
    column_rows: list[dict[str, Any]],
    table_rows: list[dict[str, Any]],
) -> dict[str, Any]:
    """Summarize a read-only COMMENT review result."""
    changed_columns = [
        f"{row['table_name']}.{row['target_name']}"
        for row in column_rows
        if row.get("review_status") == "REVIEW_REQUIRED"
    ]
    unpreserved_tables = [
        str(row["table_name"])
        for row in table_rows
        if row.get("preserved_current_comment_yn") not in (None, "Y")
    ]
    return {
        "changed_column_targets": changed_columns,
        "changed_column_count": len(changed_columns),
        "unpreserved_table_targets": unpreserved_tables,
        "table_comment_preserved": not unpreserved_tables,
    }


def assert_column_comments_applied(column_rows: list[dict[str, Any]]) -> None:
    """Raise when a post-apply review does not match every proposed column COMMENT."""
    pending = [
        f"{row['table_name']}.{row['target_name']}"
        for row in column_rows
        if row.get("review_status") != "UNCHANGED"
    ]
    if pending:
        raise RuntimeError(f"COMMENT post-verification failed: {', '.join(pending)}")

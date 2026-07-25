"""Compatibility imports for legacy COMMENT verification callers."""

from common.common_function import (
    assert_column_comments_applied,
    comment_review_status,
    is_current_table_comment_preserved,
    summarize_comment_review,
)

__all__ = [
    "assert_column_comments_applied",
    "comment_review_status",
    "is_current_table_comment_preserved",
    "summarize_comment_review",
]

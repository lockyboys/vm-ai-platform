"""여러 도구에서 공통으로 사용하는 COMMENT 검토·검증 함수 모음."""

from __future__ import annotations

from typing import Any


def comment_review_status(current_comment: str | None, proposed_comment: str | None) -> str:
    """
    현재 COMMENT와 변경 제안 COMMENT가 같은지 판정한다.

    Args:
        current_comment: information_schema에서 읽은 현재 COMMENT.
        proposed_comment: 적용하려는 COMMENT.

    Returns:
        두 문구가 같으면 UNCHANGED, 다르면 REVIEW_REQUIRED.
    """
    return "UNCHANGED" if current_comment == proposed_comment else "REVIEW_REQUIRED"


def is_current_table_comment_preserved(
    current_comment: str | None,
    proposed_comment: str | None,
) -> bool:
    """
    제안 테이블 COMMENT가 현재 COMMENT 전체를 앞부분에 그대로 보존하는지 확인한다.

    테이블 COMMENT 변경은 기존 문구를 삭제·요약하지 않고 Runtime 설명을 뒤에
    추가해야 하므로, 승인 전 검토 단계에서 이 함수를 사용한다.
    """
    return (proposed_comment or "").startswith(current_comment or "")


def summarize_comment_review(
    column_rows: list[dict[str, Any]],
    table_rows: list[dict[str, Any]],
) -> dict[str, Any]:
    """
    COMMENT 검토 SQL의 컬럼·테이블 결과를 사람이 확인하기 쉬운 요약으로 만든다.

    Args:
        column_rows: 현재·제안 컬럼 COMMENT 비교 결과.
        table_rows: 현재·제안 테이블 COMMENT 비교 결과.

    Returns:
        변경 대상 컬럼 목록·개수와 기존 테이블 COMMENT 보존 여부를 담은 사전.
    """
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
    """
    COMMENT 적용 후 모든 대상 컬럼이 제안 문구와 일치하는지 강제 검증한다.

    하나라도 UNCHANGED가 아니면 예외를 발생시켜 적용 도구가 성공으로
    종료되지 않게 한다. 이 함수는 DB 변경 후 사후검증에만 사용한다.
    """
    pending = [
        f"{row['table_name']}.{row['target_name']}"
        for row in column_rows
        if row.get("review_status") != "UNCHANGED"
    ]
    if pending:
        raise RuntimeError(f"COMMENT post-verification failed: {', '.join(pending)}")

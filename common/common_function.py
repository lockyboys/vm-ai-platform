"""Story Programming에서 여러 Runtime과 도구가 공유하는 공통 함수."""

from __future__ import annotations

import json
import re
from typing import Any


def load_rule_common_code_contract(
    common_database: Any,
    rule_code: str,
) -> dict[str, Any]:
    """활성 Rule Action이 선택한 ACTION_TYPE 공통코드 계약을 읽는다."""
    row = common_database.fetch_one(
        """
        SELECT r.rule_id,
               r.rule_code,
               a.rule_action_id,
               a.action_type_code,
               c.common_code_json
        FROM rl_rule r
        JOIN rl_rule_action a
          ON a.rule_id = r.rule_id
         AND a.status_code = 'ACTIVE'
         AND a.deleted_dt IS NULL
        JOIN cm_common_code c
          ON c.group_code = 'ACTION_TYPE'
         AND c.code = a.action_type_code
         AND c.status_code = 'ACTIVE'
         AND c.deleted_dt IS NULL
        WHERE r.rule_code = %s
          AND r.status_code = 'ACTIVE'
          AND r.deleted_dt IS NULL
        ORDER BY a.sort_no, a.rule_action_id
        LIMIT 1
        """,
        (rule_code,),
    )
    if not row:
        raise ValueError(f"Active Rule common-code contract not found: {rule_code}")

    try:
        contract = json.loads(row.get("common_code_json") or "")
    except (TypeError, json.JSONDecodeError) as exc:
        raise ValueError(
            "ACTION_TYPE common_code_json must be valid JSON. "
            f"rule_code={rule_code}, action_type_code={row['action_type_code']}"
        ) from exc
    if not isinstance(contract, dict) or not contract:
        raise ValueError(
            "ACTION_TYPE common-code contract is empty. "
            f"rule_code={rule_code}, action_type_code={row['action_type_code']}"
        )
    return {**dict(row), **contract}


def validate_common_code_value(
    common_database: Any,
    group_code: str,
    code: str,
) -> str:
    """활성 공통코드 값인지 검증하고 정규화된 Code를 반환한다."""
    row = common_database.fetch_one(
        """
        SELECT code
        FROM cm_common_code
        WHERE group_code = %s
          AND code = %s
          AND status_code = 'ACTIVE'
          AND deleted_dt IS NULL
        """,
        (group_code, code),
    )
    if not row:
        raise ValueError(
            f"Active common code not found: group_code={group_code}, code={code}"
        )
    return str(row["code"])


def physical_name_to_english_name(physical_name: str) -> str:
    """snake_case 물리명을 사람이 읽는 표준 영문명으로 변환한다."""
    words = [word for word in re.split(r"_+", physical_name.strip()) if word]
    return " ".join(
        word.upper() if len(word) <= 2 else word.capitalize()
        for word in words
    )


def resolve_attribute_names(
    column_name: str,
    column_comment: str | None,
) -> tuple[str, str, str]:
    """물리 Column에서 한글명·영문명·물리명을 공통 방식으로 구성한다."""
    physical_name = column_name.strip()
    comment = (column_comment or "").strip()
    korean_name = re.split(r"[.。\n]", comment, maxsplit=1)[0].strip() or physical_name
    return korean_name, physical_name_to_english_name(physical_name), physical_name


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
        변경 대상 컬럼·테이블 목록과 기존 테이블 COMMENT 보존 여부를 담은 사전.
    """
    changed_columns = [
        f"{row['table_name']}.{row['target_name']}"
        for row in column_rows
        if row.get("review_status") == "REVIEW_REQUIRED"
    ]
    changed_tables = [
        str(row["table_name"])
        for row in table_rows
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
        "changed_table_targets": changed_tables,
        "changed_table_count": len(changed_tables),
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

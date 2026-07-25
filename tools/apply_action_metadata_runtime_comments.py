"""Apply approved Action Metadata Runtime column and table COMMENT changes with post-verification."""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from common.common_function import (
    assert_column_comments_applied,
    summarize_comment_review,
)
from common.database import CommonDatabase
from tools.run_action_metadata_runtime_registration import split_statements

REVIEW_SQL_PATH = PROJECT_ROOT / "sql/runtime/03-0_verify_action_metadata_runtime_comments_20260725.sql"
APPLY_SQL_PATH = PROJECT_ROOT / "sql/runtime/03_action_metadata_runtime_comment_20260725.sql"
IDENTIFIER_PATTERN = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


def run_selects(database: CommonDatabase, sql_path: Path) -> list[list[dict[str, object]]]:
    """실행 전후 COMMENT 검토 SQL의 결과 집합을 읽는다."""
    with database.connection.cursor() as cursor:
        result_sets: list[list[dict[str, object]]] = []
        for statement in split_statements(sql_path.read_text(encoding="utf-8")):
            cursor.execute(statement)
            result_sets.append(list(cursor.fetchall()))
    return result_sets


def apply_column_comments(database: CommonDatabase) -> int:
    """승인된 Runtime 관련 컬럼 COMMENT DDL만 실행한다."""
    with database.connection.cursor() as cursor:
        statements = split_statements(APPLY_SQL_PATH.read_text(encoding="utf-8"))
        for statement in statements:
            cursor.execute(statement)
    return len(statements)


def apply_table_comments(
    database: CommonDatabase,
    table_rows: list[dict[str, object]],
) -> int:
    """검토 결과가 제안한 기존 COMMENT 보존본만 테이블 COMMENT로 적용한다."""
    with database.connection.cursor() as cursor:
        for row in table_rows:
            schema_name = str(row["table_schema"])
            table_name = str(row["table_name"])
            proposed_comment = str(row["proposed_comment"])
            if not IDENTIFIER_PATTERN.fullmatch(schema_name) or not IDENTIFIER_PATTERN.fullmatch(table_name):
                raise ValueError(f"Unsafe table identifier: {schema_name}.{table_name}")
            if row["preserved_current_comment_yn"] != "Y":
                raise ValueError(f"Existing table COMMENT is not preserved: {schema_name}.{table_name}")
            cursor.execute(
                f"ALTER TABLE {chr(96)}{schema_name}{chr(96)}.{chr(96)}{table_name}{chr(96)} COMMENT = %s",
                (proposed_comment,),
            )
    return len(table_rows)


def review_summary(review_result_sets: list[list[dict[str, object]]]) -> dict[str, object]:
    """컬럼과 테이블 COMMENT 검토 결과를 하나의 요약으로 만든다."""
    return summarize_comment_review(review_result_sets[0], review_result_sets[1])


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true")
    parser.add_argument(
        "--approved",
        action="store_true",
        help="Confirms that the current_comment and proposed_comment review was approved.",
    )
    args = parser.parse_args()

    if not REVIEW_SQL_PATH.is_file() or not APPLY_SQL_PATH.is_file():
        raise FileNotFoundError("Required COMMENT review or apply SQL file is missing.")

    database = CommonDatabase(database_role="COMMON")
    try:
        before = run_selects(database, REVIEW_SQL_PATH)
        if not args.apply:
            print(json.dumps(
                {
                    "status": "DRY_RUN",
                    "mode": "READ_ONLY_COMMENT_REVIEW",
                    "review_summary": review_summary(before),
                    "review": before,
                    "next_command": (
                        "python tools/apply_action_metadata_runtime_comments.py "
                        "--apply --approved"
                    ),
                },
                ensure_ascii=False,
                default=str,
            ))
            return

        if not args.approved:
            raise PermissionError("--apply requires explicit --approved confirmation.")

        column_statement_count = apply_column_comments(database)
        table_statement_count = apply_table_comments(database, before[1])
        database.commit()

        after = run_selects(database, REVIEW_SQL_PATH)
        assert_column_comments_applied(after[0])
        after_summary = review_summary(after)
        if after_summary["changed_column_count"] or after_summary["changed_table_count"]:
            raise RuntimeError("COMMENT post-verification did not reach UNCHANGED state.")

        print(json.dumps(
            {
                "status": "SUCCESS",
                "mode": "APPROVED_COMMENT_APPLY",
                "column_statement_count": column_statement_count,
                "table_statement_count": table_statement_count,
                "before_summary": review_summary(before),
                "after_summary": after_summary,
                "before_review": before,
                "after_review": after,
            },
            ensure_ascii=False,
            default=str,
        ))
    finally:
        database.close()


if __name__ == "__main__":
    main()

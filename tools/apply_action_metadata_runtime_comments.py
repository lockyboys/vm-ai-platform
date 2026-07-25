"""Apply approved Action Metadata Runtime column COMMENT changes with post-verification."""

from __future__ import annotations

import argparse
import json
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


def run_selects(database: CommonDatabase, sql_path: Path) -> list[list[dict[str, object]]]:
    with database.connection.cursor() as cursor:
        result_sets: list[list[dict[str, object]]] = []
        for statement in split_statements(sql_path.read_text(encoding="utf-8")):
            cursor.execute(statement)
            result_sets.append(list(cursor.fetchall()))
    return result_sets


def apply_comments(database: CommonDatabase) -> int:
    with database.connection.cursor() as cursor:
        statements = split_statements(APPLY_SQL_PATH.read_text(encoding="utf-8"))
        for statement in statements:
            cursor.execute(statement)
    return len(statements)


def review_summary(review_result_sets: list[list[dict[str, object]]]) -> dict[str, object]:
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

        statement_count = apply_comments(database)
        database.commit()
        after = run_selects(database, REVIEW_SQL_PATH)
        assert_column_comments_applied(after[0])
        print(json.dumps(
            {
                "status": "SUCCESS",
                "mode": "APPROVED_COMMENT_APPLY",
                "statement_count": statement_count,
                "before_summary": review_summary(before),
                "after_summary": review_summary(after),
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

"""Run the read-only Action Metadata Runtime COMMENT review query."""

from __future__ import annotations

import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from common.common_function import summarize_comment_review
from common.database import CommonDatabase
from tools.run_action_metadata_runtime_registration import split_statements

REVIEW_SQL_PATH = PROJECT_ROOT / "sql/runtime/03-0_verify_action_metadata_runtime_comments_20260725.sql"


def main() -> None:
    if not REVIEW_SQL_PATH.is_file():
        raise FileNotFoundError(f"COMMENT review SQL not found: {REVIEW_SQL_PATH}")

    statements = split_statements(REVIEW_SQL_PATH.read_text(encoding="utf-8"))
    database = CommonDatabase(database_role="COMMON")
    try:
        result_sets: list[list[dict[str, object]]] = []
        with database.connection.cursor() as cursor:
            for statement in statements:
                cursor.execute(statement)
                result_sets.append(list(cursor.fetchall()))
    finally:
        database.close()

    review_summary = summarize_comment_review(result_sets[0], result_sets[1])
    print(
        json.dumps(
            {
                "status": "SUCCESS",
                "mode": "READ_ONLY_COMMENT_REVIEW",
                "sql_path": str(REVIEW_SQL_PATH.relative_to(PROJECT_ROOT)),
                "review_summary": review_summary,
                "result_sets": result_sets,
            },
            ensure_ascii=False,
            default=str,
        )
    )


if __name__ == "__main__":
    main()

# =============================================================================
# File Name : tools/run_repository_data_type_patch_20260720.py
# Purpose   : Execute the one-time hardcoded Repository Data Type SQL Patch
# =============================================================================

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from common.database import CommonDatabase


DATABASE_ROLE = "COMMON"
DEFAULT_PATCH_FILE = (
    PROJECT_ROOT / "sql/runtime/repository_data_type_patch_all_20260720.sql"
)


def resolve_patch_file() -> Path:
    if len(sys.argv) == 1:
        return DEFAULT_PATCH_FILE
    if len(sys.argv) != 2:
        raise SystemExit(
            "Usage: python tools/run_repository_data_type_patch_20260720.py "
            "[project-relative-sql-path]"
        )
    candidate = (PROJECT_ROOT / sys.argv[1]).resolve()
    if PROJECT_ROOT not in candidate.parents:
        raise SystemExit("Patch file must be inside the project.")
    return candidate


PATCH_FILE = resolve_patch_file()


def load_statements() -> list[str]:
    sql_text = PATCH_FILE.read_text(encoding="utf-8")
    sql_text = re.sub(r"/\*.*?\*/", "", sql_text, flags=re.DOTALL)
    sql_text = re.sub(r"(?m)^\s*--.*$", "", sql_text)
    return [
        statement.strip()
        for statement in sql_text.split(";")
        if statement.strip()
    ]


def main() -> None:
    database = CommonDatabase(database_role=DATABASE_ROLE)
    results = []
    try:
        for statement_no, statement in enumerate(load_statements(), start=1):
            keyword = statement.split(None, 1)[0].upper()

            if keyword == "START":
                database.begin()
                results.append(
                    {"statement_no": statement_no, "type": "TRANSACTION", "status": "STARTED"}
                )
                continue

            if keyword == "COMMIT":
                database.commit()
                results.append(
                    {"statement_no": statement_no, "type": "TRANSACTION", "status": "COMMITTED"}
                )
                continue

            if keyword in {"SELECT", "SHOW"}:
                rows = database.fetch_all(statement)
                results.append(
                    {
                        "statement_no": statement_no,
                        "type": keyword,
                        "row_count": len(rows),
                        "rows": rows,
                    }
                )
                continue

            affected_rows = database.execute(statement)
            results.append(
                {
                    "statement_no": statement_no,
                    "type": keyword,
                    "affected_rows": affected_rows,
                    "status": "SUCCESS",
                }
            )

        database.commit()
        print(
            json.dumps(
                {
                    "status": "SUCCESS",
                    "database_role": DATABASE_ROLE,
                    "patch_file": str(PATCH_FILE.relative_to(PROJECT_ROOT)),
                    "statement_count": len(results),
                    "results": results,
                },
                ensure_ascii=False,
                indent=2,
                default=str,
            )
        )
    except Exception as error:
        try:
            database.rollback()
        except Exception:
            pass
        print(
            json.dumps(
                {
                    "status": "FAILED",
                    "database_role": DATABASE_ROLE,
                    "patch_file": str(PATCH_FILE.relative_to(PROJECT_ROOT)),
                    "error_type": type(error).__name__,
                    "error": str(error),
                    "completed_results": results,
                },
                ensure_ascii=False,
                indent=2,
                default=str,
            )
        )
        raise
    finally:
        database.close()


if __name__ == "__main__":
    main()

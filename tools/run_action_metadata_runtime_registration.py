"""Execute the Action Metadata registration batches through CommonDatabase."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from common.database import CommonDatabase
from engine.runtime.action_metadata_registration_manifest import ACTION_METADATA_REGISTRATION_BATCHES


def load_batches() -> list[dict[str, object]]:
    batches = ACTION_METADATA_REGISTRATION_BATCHES
    if not batches:
        raise ValueError("Action Metadata registration manifest has no batches.")
    return sorted(batches, key=lambda batch: int(batch["order"]))


def split_statements(sql_text: str) -> list[str]:
    delimiter = ";"
    buffer: list[str] = []
    statements: list[str] = []

    for line in sql_text.splitlines():
        stripped = line.strip()
        if stripped.upper().startswith("DELIMITER "):
            delimiter = stripped.split(maxsplit=1)[1]
            continue

        buffer.append(line)
        if stripped.endswith(delimiter):
            statement = "\n".join(buffer).strip()[: -len(delimiter)].strip()
            if statement:
                statements.append(statement)
            buffer = []

    remainder = "\n".join(buffer).strip()
    if remainder:
        statements.append(remainder)
    return statements


def execute_batch(database: CommonDatabase, batch: dict[str, object], client_ip: str | None) -> dict[str, object]:
    relative_path = str(batch["path"])
    batch_path = (PROJECT_ROOT / relative_path).resolve()
    if PROJECT_ROOT not in batch_path.parents or not batch_path.is_file():
        raise FileNotFoundError(f"Registration batch not found: {relative_path}")

    statements = split_statements(batch_path.read_text(encoding="utf-8"))
    with database.connection.cursor() as cursor:
        if client_ip:
            cursor.execute("SET @client_ip = %s", (client_ip,))
        for statement in statements:
            cursor.execute(statement)

    return {"path": relative_path, "statement_count": len(statements)}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--client-ip")
    args = parser.parse_args()
    batches = load_batches()

    if not args.apply:
        print({"status": "DRY_RUN", "batches": batches})
        return

    database = CommonDatabase(database_role="COMMON")
    results: list[dict[str, object]] = []
    try:
        for batch in batches:
            results.append(execute_batch(database, batch, args.client_ip))
        database.commit()
    except Exception:
        database.rollback()
        raise
    finally:
        database.close()

    print({"status": "SUCCESS", "batches": results})


if __name__ == "__main__":
    main()

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from common.database import CommonDatabase
from engine.generator.metadata_generator import MetadataGenerator
from tools.register_column_suffix_metadata import ensure_metadata_identifier_sequence

METADATA_TYPE_CODE = "DATA_TYPE"
PROGRAM_ID = "upsert_column_suffix_metadata_20260719"
ACTOR_ID = "SYSTEM"
CLIENT_IP = "127.0.0.1"

STANDARDS: tuple[dict[str, Any], ...] = (
    {
        "suffix": "_id",
        "sql_type": "VARCHAR(99)",
        "data_type": "VARCHAR",
        "length": 99,
        "meaning": "Level 4 Record Identifier",
        "object_level": 4,
        "reset_policy_code": "DAILY",
        "sequence_length": 5,
        "identifier_generation": "IDENTIFIER_ENGINE",
    },
    {"suffix": "_code", "sql_type": "VARCHAR(99)", "data_type": "VARCHAR", "length": 99, "meaning": "Code"},
    {"suffix": "_name", "sql_type": "VARCHAR(150)", "data_type": "VARCHAR", "length": 150, "meaning": "Name"},
    {"suffix": "_description", "sql_type": "VARCHAR(2000)", "data_type": "VARCHAR", "length": 2000, "meaning": "Description"},
    {"suffix": "_json", "sql_type": "LONGTEXT", "data_type": "LONGTEXT", "validation": "JSON_VALID", "meaning": "JSON Document"},
    {"suffix": "_text", "sql_type": "TEXT", "data_type": "TEXT", "meaning": "Text"},
    {"suffix": "_email", "sql_type": "VARCHAR(500)", "data_type": "VARCHAR", "length": 500, "meaning": "Email Address"},
    {"suffix": "_no", "sql_type": "INT", "data_type": "INT", "meaning": "Ordinal Number"},
    {"suffix": "_num", "sql_type": "VARCHAR(99)", "data_type": "VARCHAR", "length": 99, "meaning": "Logical Number"},
    {"suffix": "_dt", "sql_type": "DATETIME", "data_type": "DATETIME", "meaning": "Date Time"},
    {"suffix": "_yn", "sql_type": "CHAR(1)", "data_type": "CHAR", "length": 1, "meaning": "Yes or No"},
    {"suffix": "_by", "sql_type": "VARCHAR(99)", "data_type": "VARCHAR", "length": 99, "meaning": "Actor Identifier"},
    {"suffix": "_ip", "sql_type": "VARCHAR(99)", "data_type": "VARCHAR", "length": 99, "meaning": "IP Address"},
    {"suffix": "_value", "sql_type": "VARCHAR(2000)", "data_type": "VARCHAR", "length": 2000, "meaning": "Value"},
    {"suffix": "_date", "sql_type": "DATETIME", "data_type": "DATETIME", "meaning": "Legacy Date Time", "match_type": "SUFFIX", "match_key": "_date", "rename_suffix": "_dt", "priority": 800},
    {"suffix": "_time", "sql_type": "TIME", "data_type": "TIME", "meaning": "Time"},
    {"suffix": "_count", "sql_type": "INT", "data_type": "INT", "meaning": "Count"},
    {"suffix": "_length", "sql_type": "INT", "data_type": "INT", "meaning": "Length"},
    {"suffix": "_size", "sql_type": "BIGINT", "data_type": "BIGINT", "meaning": "Size"},
    {"suffix": "_rate", "sql_type": "DECIMAL(10,4)", "data_type": "DECIMAL", "precision": 10, "scale": 4, "meaning": "Rate"},
    {"suffix": "_amount", "sql_type": "DECIMAL(18,2)", "data_type": "DECIMAL", "precision": 18, "scale": 2, "meaning": "Amount"},
    {"suffix": "_url", "sql_type": "VARCHAR(2000)", "data_type": "VARCHAR", "length": 2000, "meaning": "URL"},
    {"suffix": "_path", "sql_type": "VARCHAR(2000)", "data_type": "VARCHAR", "length": 2000, "meaning": "Path"},
)


def metadata_payload(standard: dict[str, Any]) -> str:
    payload = {
        "category": "COLUMN_SUFFIX_STANDARD",
        "requirement": "REQUIRED",
        "negative_metadata": True,
        **standard,
        "hardcoding_allowed": False,
    }
    return json.dumps(payload, ensure_ascii=False, separators=(",", ":"))


def resolve_metadata_object(database: CommonDatabase) -> dict[str, Any]:
    row = database.fetch_one(
        """
        SELECT object_id, object_code, object_level
        FROM sp_object
        WHERE object_code = 'METADATA'
          AND deleted_dt IS NULL
        ORDER BY object_level DESC, created_dt
        LIMIT 1
        """
    )
    if not row:
        raise RuntimeError("Active METADATA Object was not found in sp_object.")
    return dict(row)


def load_existing(database: CommonDatabase, target_id: str) -> dict[str, dict[str, Any]]:
    keys = tuple(item["suffix"] for item in STANDARDS)
    placeholders = ", ".join(["%s"] * len(keys))
    rows = database.fetch_all(
        f"""
        SELECT metadata_id, metadata_type_code, metadata_key,
               metadata_value, metadata_value_type_code, metadata_json,
               enabled_yn, sort_no
        FROM sp_metadata
        WHERE target_type_code = 'COLUMN'
          AND target_id = %s
          AND metadata_key IN ({placeholders})
          AND deleted_dt IS NULL
        """,
        (target_id, *keys),
    )
    return {str(row["metadata_key"]): dict(row) for row in (rows or [])}


def update_existing(
    database: CommonDatabase,
    target_id: str,
    existing: dict[str, dict[str, Any]],
) -> int:
    updated = 0
    try:
        database.begin()
        for sort_no, standard in enumerate(STANDARDS, start=1):
            suffix = standard["suffix"]
            if suffix not in existing:
                continue
            updated += database.execute(
                """
                UPDATE sp_metadata
                SET metadata_type_code = %s,
                    metadata_value = %s,
                    metadata_value_type_code = 'STRING',
                    metadata_json = %s,
                    enabled_yn = 'Y',
                    sort_no = %s,
                    updated_by = %s,
                    updated_dt = CURRENT_TIMESTAMP,
                    deleted_by = NULL,
                    deleted_dt = NULL,
                    client_ip = %s,
                    program_id = %s
                WHERE target_type_code = 'COLUMN'
                  AND target_id = %s
                  AND metadata_key = %s
                  AND deleted_dt IS NULL
                """,
                (
                    METADATA_TYPE_CODE,
                    standard["sql_type"],
                    metadata_payload(standard),
                    sort_no * 10,
                    ACTOR_ID,
                    CLIENT_IP,
                    PROGRAM_ID,
                    target_id,
                    suffix,
                ),
            )
        database.commit()
    except Exception:
        database.rollback()
        raise
    return updated


def build_missing_requests(
    target_id: str,
    existing: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    requests: list[dict[str, Any]] = []
    for sort_no, standard in enumerate(STANDARDS, start=1):
        if standard["suffix"] in existing:
            continue
        requests.append(
            {
                "target_type_code": "COLUMN",
                "target_id": target_id,
                "metadata_type_code": METADATA_TYPE_CODE,
                "metadata_key": standard["suffix"],
                "metadata_value": standard["sql_type"],
                "metadata_value_type_code": "STRING",
                "metadata_json": metadata_payload(standard),
                "enabled_yn": "Y",
                "sort_no": sort_no * 10,
                "created_by": ACTOR_ID,
                "updated_by": ACTOR_ID,
                "client_ip": CLIENT_IP,
                "program_id": PROGRAM_ID,
            }
        )
    return requests


def verify(database: CommonDatabase, target_id: str) -> list[dict[str, Any]]:
    saved = load_existing(database, target_id)
    errors: list[str] = []
    for standard in STANDARDS:
        suffix = standard["suffix"]
        row = saved.get(suffix)
        if not row:
            errors.append(f"{suffix}: missing")
            continue
        if row["metadata_type_code"] != METADATA_TYPE_CODE:
            errors.append(f"{suffix}: metadata_type_code mismatch")
        if row["metadata_value_type_code"] != "STRING":
            errors.append(f"{suffix}: metadata_value_type_code mismatch")
        if row["metadata_value"] != standard["sql_type"]:
            errors.append(
                f"{suffix}: expected {standard['sql_type']}, got {row['metadata_value']}"
            )
        try:
            payload = json.loads(row["metadata_json"])
        except (TypeError, json.JSONDecodeError):
            errors.append(f"{suffix}: invalid metadata_json")
            continue
        if payload.get("sql_type") != standard["sql_type"]:
            errors.append(f"{suffix}: metadata_json sql_type mismatch")
    if errors:
        raise RuntimeError("Column suffix metadata verification failed: " + "; ".join(errors))
    return [saved[item["suffix"]] for item in STANDARDS]


def main() -> int:
    database = CommonDatabase(database_role="STORY_PLATFORM")
    try:
        metadata_object = resolve_metadata_object(database)
        target_id = str(metadata_object["object_id"])

        sequence_result = ensure_metadata_identifier_sequence(database)
        existing = load_existing(database, target_id)
        updated_count = update_existing(database, target_id, existing)

        missing_requests = build_missing_requests(target_id, existing)
        inserted_count = 0
        generator_result: dict[str, Any] = {"status": "SKIPPED"}

        if missing_requests:
            generator_result = MetadataGenerator(database).create_batch(missing_requests)
            if not generator_result.get("success"):
                raise RuntimeError(
                    "MetadataGenerator failed: "
                    + str(generator_result.get("status"))
                )
            inserted_count = int(generator_result.get("metadata_count") or 0)

        rows = verify(database, target_id)

        print("=" * 78)
        print("SPS Column Suffix Metadata Upsert SUCCESS")
        print("=" * 78)
        print(f"Target Object : {target_id}")
        print(f"Standards     : {len(STANDARDS)}")
        print(f"Existing      : {len(existing)}")
        print(f"Updated       : {updated_count}")
        print(f"Inserted      : {inserted_count}")
        print(f"Verified      : {len(rows)}")
        print(f"Sequence      : {sequence_result.get('status')}")
        print(f"Generator     : {generator_result.get('status')}")
        print("=" * 78)
        for row in rows:
            print(f"{row['metadata_key']:<14} {row['metadata_value']}")
        return 0
    finally:
        database.close()


if __name__ == "__main__":
    raise SystemExit(main())

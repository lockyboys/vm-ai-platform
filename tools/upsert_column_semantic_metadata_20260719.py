"""Register SPS column semantic matching Metadata.

This idempotent batch adds exact-name, suffix, root-token, and prefix-semantic
rules without altering physical application tables.
"""

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

PROGRAM_ID = "upsert_column_semantic_metadata_20260719"
ACTOR_ID = "SYSTEM"
CLIENT_IP = "127.0.0.1"

TYPE_STANDARD_RULES: tuple[dict[str, Any], ...] = (
    # Compound and general suffix rules.
    {"match_type": "COMPOUND_SUFFIX", "match_key": "_ip_address", "sql_type": "VARCHAR(50)", "semantic_role": "IP_ADDRESS", "rename_suffix": "_ip", "priority": 900},
    {"match_type": "SUFFIX", "match_key": "_message", "sql_type": "TEXT", "semantic_role": "MESSAGE", "priority": 700},
    {"match_type": "SUFFIX", "match_key": "_summary", "sql_type": "VARCHAR(2000)", "semantic_role": "SUMMARY", "priority": 700},
    {"match_type": "SUFFIX", "match_key": "_score", "sql_type": "DECIMAL(10,4)", "semantic_role": "SCORE", "precision": 10, "scale": 4, "priority": 700},
    {"match_type": "SUFFIX", "match_key": "_title", "sql_type": "VARCHAR(500)", "semantic_role": "TITLE", "length": 500, "priority": 700},
    {"match_type": "SUFFIX", "match_key": "_content", "sql_type": "TEXT", "semantic_role": "CONTENT", "priority": 700},
    {"match_type": "SUFFIX", "match_key": "_note", "sql_type": "TEXT", "semantic_role": "NOTE", "priority": 700},
    {"match_type": "SUFFIX", "match_key": "_comment", "sql_type": "VARCHAR(2000)", "semantic_role": "COMMENT", "length": 2000, "priority": 700},
    {"match_type": "SUFFIX", "match_key": "_story", "sql_type": "VARCHAR(2000)", "semantic_role": "STORY", "length": 2000, "priority": 700},
    {"match_type": "SUFFIX", "match_key": "_days", "sql_type": "INT", "semantic_role": "DURATION_DAYS", "priority": 700},
    {"match_type": "SUFFIX", "match_key": "_order", "sql_type": "INT", "semantic_role": "SORT_ORDER", "rename_suffix": "_no", "priority": 700},
    {"match_type": "SUFFIX", "match_key": "_step", "sql_type": "VARCHAR(99)", "semantic_role": "STEP", "length": 99, "priority": 700},
    {"match_type": "SUFFIX", "match_key": "_status", "sql_type": "VARCHAR(99)", "semantic_role": "STATUS", "rename_suffix": "_status_code", "priority": 700},
    {"match_type": "SUFFIX", "match_key": "_identifier", "sql_type": "VARCHAR(99)", "semantic_role": "IDENTIFIER", "length": 99, "priority": 700},
    {"match_type": "SUFFIX", "match_key": "_prefix", "sql_type": "VARCHAR(99)", "semantic_role": "IDENTIFIER_PREFIX", "length": 99, "priority": 700},
    {"match_type": "SUFFIX", "match_key": "_field", "sql_type": "VARCHAR(99)", "semantic_role": "FIELD_IDENTIFIER", "length": 99, "priority": 700},
    {"match_type": "SUFFIX", "match_key": "_cardinality", "sql_type": "INT", "semantic_role": "CARDINALITY", "priority": 700},
    {"match_type": "SUFFIX", "match_key": "_host", "sql_type": "VARCHAR(500)", "semantic_role": "CONNECTION_HOST", "length": 500, "priority": 700},
    {"match_type": "SUFFIX", "match_key": "_address", "sql_type": "VARCHAR(500)", "semantic_role": "ADDRESS", "length": 500, "priority": 700},
    {"match_type": "SUFFIX", "match_key": "_agent", "sql_type": "VARCHAR(500)", "semantic_role": "USER_AGENT", "length": 500, "priority": 700},
    {"match_type": "SUFFIX", "match_key": "_codes", "sql_type": "VARCHAR(2000)", "semantic_role": "CODE_LIST", "length": 2000, "priority": 700},
    {"match_type": "SUFFIX", "match_key": "_goal", "sql_type": "VARCHAR(2000)", "semantic_role": "GOAL", "length": 2000, "priority": 700},
    {"match_type": "SUFFIX", "match_key": "_collection", "sql_type": "VARCHAR(150)", "semantic_role": "COLLECTION_NAME", "length": 150, "priority": 700},
    {"match_type": "SUFFIX", "match_key": "_database", "sql_type": "VARCHAR(150)", "semantic_role": "DATABASE_NAME", "length": 150, "priority": 700},
    {"match_type": "SUFFIX", "match_key": "_table", "sql_type": "VARCHAR(150)", "semantic_role": "TABLE_NAME", "length": 150, "priority": 700},

    # Exact-name rules override every suffix, prefix, and root rule.
    {"match_type": "EXACT", "match_key": "code", "sql_type": "VARCHAR(99)", "semantic_role": "CODE", "length": 99, "priority": 1000},
    {"match_type": "EXACT", "match_key": "description", "sql_type": "VARCHAR(2000)", "semantic_role": "DESCRIPTION", "length": 2000, "priority": 1000},
    {"match_type": "EXACT", "match_key": "email", "sql_type": "VARCHAR(500)", "semantic_role": "EMAIL", "length": 500, "priority": 1000},
    {"match_type": "EXACT", "match_key": "message", "sql_type": "TEXT", "semantic_role": "MESSAGE", "priority": 1000},
    {"match_type": "EXACT", "match_key": "summary", "sql_type": "VARCHAR(2000)", "semantic_role": "SUMMARY", "length": 2000, "priority": 1000},
    {"match_type": "EXACT", "match_key": "remark", "sql_type": "VARCHAR(2000)", "semantic_role": "REMARK", "length": 2000, "priority": 1000},
    {"match_type": "EXACT", "match_key": "address", "sql_type": "VARCHAR(500)", "semantic_role": "ADDRESS", "length": 500, "priority": 1000},
    {"match_type": "EXACT", "match_key": "phone", "sql_type": "VARCHAR(50)", "semantic_role": "PHONE", "length": 50, "priority": 1000},
    {"match_type": "EXACT", "match_key": "doi", "sql_type": "VARCHAR(500)", "semantic_role": "DOI", "length": 500, "priority": 1000},
    {"match_type": "EXACT", "match_key": "pmid", "sql_type": "VARCHAR(99)", "semantic_role": "PMID", "length": 99, "priority": 1000},
    {"match_type": "EXACT", "match_key": "created_at", "sql_type": "DATETIME", "semantic_role": "CREATED_DATETIME", "rename_to": "created_dt", "priority": 1100},
    {"match_type": "EXACT", "match_key": "updated_at", "sql_type": "DATETIME", "semantic_role": "UPDATED_DATETIME", "rename_to": "updated_dt", "priority": 1100},
    {"match_type": "EXACT", "match_key": "disposed_at", "sql_type": "DATETIME", "semantic_role": "DISPOSED_DATETIME", "rename_to": "disposed_dt", "priority": 1100},
    {"match_type": "EXACT", "match_key": "executed_at", "sql_type": "DATETIME", "semantic_role": "EXECUTED_DATETIME", "rename_to": "executed_dt", "priority": 1100},
    {"match_type": "EXACT", "match_key": "sequence_date", "sql_type": "DATE", "semantic_role": "SEQUENCE_DATE", "priority": 1100},
    {"match_type": "EXACT", "match_key": "generated_identifier", "sql_type": "VARCHAR(99)", "semantic_role": "GENERATED_IDENTIFIER", "length": 99, "priority": 1100},
    {"match_type": "EXACT", "match_key": "knowledge_identifier", "sql_type": "VARCHAR(99)", "semantic_role": "KNOWLEDGE_IDENTIFIER", "length": 99, "priority": 1100},
    {"match_type": "EXACT", "match_key": "identifier_prefix", "sql_type": "VARCHAR(99)", "semantic_role": "IDENTIFIER_PREFIX", "length": 99, "priority": 1100},
    {"match_type": "EXACT", "match_key": "metadata_key", "sql_type": "VARCHAR(150)", "semantic_role": "METADATA_KEY", "length": 150, "priority": 1100},
    {"match_type": "EXACT", "match_key": "target_identifier_field", "sql_type": "VARCHAR(99)", "semantic_role": "TARGET_IDENTIFIER_FIELD", "length": 99, "priority": 1100},
    {"match_type": "EXACT", "match_key": "sequence_date_rule", "sql_type": "VARCHAR(99)", "semantic_role": "SEQUENCE_DATE_RULE_CODE", "rename_to": "sequence_date_rule_code", "length": 99, "priority": 1100},

    # Root-token rules are fallback rules. They never use substring matching.
    {"match_type": "ROOT", "match_key": "message", "sql_type": "TEXT", "semantic_role": "MESSAGE", "priority": 300},
    {"match_type": "ROOT", "match_key": "summary", "sql_type": "VARCHAR(2000)", "semantic_role": "SUMMARY", "length": 2000, "priority": 300},
    {"match_type": "ROOT", "match_key": "remark", "sql_type": "VARCHAR(2000)", "semantic_role": "REMARK", "length": 2000, "priority": 300},
    {"match_type": "ROOT", "match_key": "score", "sql_type": "DECIMAL(10,4)", "semantic_role": "SCORE", "precision": 10, "scale": 4, "priority": 300},
    {"match_type": "ROOT", "match_key": "days", "sql_type": "INT", "semantic_role": "DURATION_DAYS", "priority": 300},
    {"match_type": "ROOT", "match_key": "cardinality", "sql_type": "INT", "semantic_role": "CARDINALITY", "priority": 300},
    {"match_type": "ROOT", "match_key": "identifier", "sql_type": "VARCHAR(99)", "semantic_role": "IDENTIFIER", "length": 99, "priority": 300},
    {"match_type": "ROOT", "match_key": "status", "sql_type": "VARCHAR(99)", "semantic_role": "STATUS", "length": 99, "priority": 300},
    {"match_type": "ROOT", "match_key": "title", "sql_type": "VARCHAR(500)", "semantic_role": "TITLE", "length": 500, "priority": 300},
    {"match_type": "ROOT", "match_key": "content", "sql_type": "TEXT", "semantic_role": "CONTENT", "priority": 300},
    {"match_type": "ROOT", "match_key": "note", "sql_type": "TEXT", "semantic_role": "NOTE", "priority": 300},
    {"match_type": "ROOT", "match_key": "comment", "sql_type": "VARCHAR(2000)", "semantic_role": "COMMENT", "length": 2000, "priority": 300},
)

PREFIX_SEMANTIC_RULES: tuple[dict[str, Any], ...] = (
    {"match_type": "PREFIX", "match_key": "source_", "semantic_role": "SOURCE", "priority": 200},
    {"match_type": "PREFIX", "match_key": "target_", "semantic_role": "TARGET", "priority": 200},
    {"match_type": "PREFIX", "match_key": "parent_", "semantic_role": "PARENT", "priority": 200},
    {"match_type": "PREFIX", "match_key": "created_", "semantic_role": "CREATED_AUDIT", "priority": 200},
    {"match_type": "PREFIX", "match_key": "updated_", "semantic_role": "UPDATED_AUDIT", "priority": 200},
    {"match_type": "PREFIX", "match_key": "deleted_", "semantic_role": "DELETED_AUDIT", "priority": 200},
    {"match_type": "PREFIX", "match_key": "mongodb_", "semantic_role": "MONGODB", "priority": 200},
    {"match_type": "PREFIX", "match_key": "storage_", "semantic_role": "STORAGE", "priority": 200},
    {"match_type": "PREFIX", "match_key": "sequence_", "semantic_role": "SEQUENCE", "priority": 200},
)


def metadata_type_code(rule: dict[str, Any]) -> str:
    if "sql_type" not in rule:
        return "COLUMN_PREFIX_SEMANTIC"
    return f"COLUMN_{rule['match_type']}_STANDARD"


def metadata_key(rule: dict[str, Any]) -> str:
    if rule["match_type"] in {"SUFFIX", "COMPOUND_SUFFIX"}:
        return str(rule["match_key"])
    return f"{rule['match_type']}:{rule['match_key']}"


def metadata_payload(rule: dict[str, Any]) -> str:
    payload = {
        "category": "COLUMN_NAMING_AND_DATA_TYPE_STANDARD",
        "requirement": "REQUIRED",
        "match_type": rule["match_type"],
        "match_key": rule["match_key"],
        "sql_type": rule.get("sql_type"),
        "semantic_role": rule.get("semantic_role"),
        "priority": int(rule.get("priority") or 0),
        "rename_to": rule.get("rename_to"),
        "rename_suffix": rule.get("rename_suffix"),
        "token_match_only": rule["match_type"] == "ROOT",
        "hardcoding_allowed": False,
        **{
            key: value
            for key, value in rule.items()
            if key
            not in {
                "match_type",
                "match_key",
                "sql_type",
                "semantic_role",
                "priority",
                "rename_to",
                "rename_suffix",
            }
        },
    }
    return json.dumps(payload, ensure_ascii=False, separators=(",", ":"))


def resolve_metadata_target(database: CommonDatabase) -> str:
    row = database.fetch_one(
        """
        SELECT object_id
        FROM sp_object
        WHERE object_code = 'METADATA'
          AND deleted_dt IS NULL
        ORDER BY object_level DESC, created_dt
        LIMIT 1
        """
    )
    if not row:
        raise RuntimeError("Active METADATA Object was not found.")
    return str(row["object_id"])


def load_existing(
    database: CommonDatabase,
    target_id: str,
    keys: tuple[str, ...],
) -> set[str]:
    placeholders = ", ".join(["%s"] * len(keys))
    rows = database.fetch_all(
        f"""
        SELECT metadata_key
        FROM sp_metadata
        WHERE target_type_code = 'COLUMN'
          AND target_id = %s
          AND metadata_key IN ({placeholders})
          AND deleted_dt IS NULL
        """,
        (target_id, *keys),
    )
    return {str(row["metadata_key"]) for row in (rows or [])}


def update_existing(
    database: CommonDatabase,
    target_id: str,
    rules: tuple[dict[str, Any], ...],
    existing_keys: set[str],
) -> int:
    updated = 0
    try:
        database.begin()
        for sort_no, rule in enumerate(rules, start=1):
            key = metadata_key(rule)
            if key not in existing_keys:
                continue
            updated += database.execute(
                """
                UPDATE sp_metadata
                SET metadata_type_code = %s,
                    metadata_value = %s,
                    metadata_value_type_code = 'JSON',
                    metadata_json = %s,
                    enabled_yn = 'Y',
                    sort_no = %s,
                    updated_by = %s,
                    updated_dt = CURRENT_TIMESTAMP,
                    client_ip = %s,
                    program_id = %s
                WHERE target_type_code = 'COLUMN'
                  AND target_id = %s
                  AND metadata_key = %s
                  AND deleted_dt IS NULL
                """,
                (
                    metadata_type_code(rule),
                    rule.get("sql_type") or rule.get("semantic_role"),
                    metadata_payload(rule),
                    1000 + sort_no * 10,
                    ACTOR_ID,
                    CLIENT_IP,
                    PROGRAM_ID,
                    target_id,
                    key,
                ),
            )
        database.commit()
    except Exception:
        database.rollback()
        raise
    return updated


def build_missing_requests(
    target_id: str,
    rules: tuple[dict[str, Any], ...],
    existing_keys: set[str],
) -> list[dict[str, Any]]:
    requests: list[dict[str, Any]] = []
    for sort_no, rule in enumerate(rules, start=1):
        key = metadata_key(rule)
        if key in existing_keys:
            continue
        requests.append(
            {
                "target_type_code": "COLUMN",
                "target_id": target_id,
                "metadata_type_code": metadata_type_code(rule),
                "metadata_key": key,
                "metadata_value": (
                    rule.get("sql_type")
                    or rule.get("semantic_role")
                ),
                "metadata_value_type_code": "JSON",
                "metadata_json": metadata_payload(rule),
                "enabled_yn": "Y",
                "sort_no": 1000 + sort_no * 10,
                "created_by": ACTOR_ID,
                "updated_by": ACTOR_ID,
                "client_ip": CLIENT_IP,
                "program_id": PROGRAM_ID,
            }
        )
    return requests


def verify(
    database: CommonDatabase,
    target_id: str,
    rules: tuple[dict[str, Any], ...],
) -> list[dict[str, Any]]:
    keys = tuple(metadata_key(rule) for rule in rules)
    placeholders = ", ".join(["%s"] * len(keys))
    rows = database.fetch_all(
        f"""
        SELECT
            metadata_id,
            metadata_type_code,
            metadata_key,
            metadata_value,
            metadata_json,
            enabled_yn
        FROM sp_metadata
        WHERE target_type_code = 'COLUMN'
          AND target_id = %s
          AND metadata_key IN ({placeholders})
          AND deleted_dt IS NULL
        ORDER BY sort_no, metadata_key
        """,
        (target_id, *keys),
    )
    saved = {str(row["metadata_key"]): dict(row) for row in (rows or [])}
    errors: list[str] = []

    for rule in rules:
        key = metadata_key(rule)
        row = saved.get(key)
        if not row:
            errors.append(f"{key}: missing")
            continue
        if row["metadata_type_code"] != metadata_type_code(rule):
            errors.append(f"{key}: metadata_type_code mismatch")
        try:
            payload = json.loads(row["metadata_json"])
        except (TypeError, json.JSONDecodeError):
            errors.append(f"{key}: invalid metadata_json")
            continue
        if payload.get("match_type") != rule["match_type"]:
            errors.append(f"{key}: match_type mismatch")
        if payload.get("match_key") != rule["match_key"]:
            errors.append(f"{key}: match_key mismatch")

    if errors:
        raise RuntimeError(
            "Column semantic Metadata verification failed: "
            + "; ".join(errors)
        )
    return [saved[key] for key in keys]


def main() -> int:
    database = CommonDatabase(database_role="STORY_PLATFORM")
    rules = TYPE_STANDARD_RULES + PREFIX_SEMANTIC_RULES
    try:
        target_id = resolve_metadata_target(database)
        sequence_result = ensure_metadata_identifier_sequence(database)
        keys = tuple(metadata_key(rule) for rule in rules)
        existing_keys = load_existing(database, target_id, keys)
        updated_count = update_existing(
            database,
            target_id,
            rules,
            existing_keys,
        )
        requests = build_missing_requests(
            target_id,
            rules,
            existing_keys,
        )

        inserted_count = 0
        generator_status = "SKIPPED"
        if requests:
            result = MetadataGenerator(database).create_batch(requests)
            if not result.get("success"):
                raise RuntimeError(
                    "MetadataGenerator failed: "
                    + str(result.get("status"))
                )
            inserted_count = int(result.get("metadata_count") or 0)
            generator_status = str(result.get("status"))

        saved_rows = verify(database, target_id, rules)

        print("=" * 80)
        print("SPS Column Semantic Metadata Upsert SUCCESS")
        print("=" * 80)
        print(f"Target Object : {target_id}")
        print(f"Rules         : {len(rules)}")
        print(f"Updated       : {updated_count}")
        print(f"Inserted      : {inserted_count}")
        print(f"Verified      : {len(saved_rows)}")
        print(f"Sequence      : {sequence_result.get('status')}")
        print(f"Generator     : {generator_status}")
        print("=" * 80)
        return 0
    finally:
        database.close()


if __name__ == "__main__":
    raise SystemExit(main())

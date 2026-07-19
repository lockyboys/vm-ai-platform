from __future__ import annotations

import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parents[1]

if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from common.database import CommonDatabase
from engine.generator.metadata_generator import MetadataGenerator
from engine.identifier_engine import IdentifierEngine


TARGET_ID = "SP_MT_METADATA_20260714_00001"
METADATA_TYPE_CODE = "DATA_TYPE"

STANDARDS = (
    ("_id", "VARCHAR(99)", "VARCHAR", 99, "Identifier"),
    ("_code", "VARCHAR(99)", "VARCHAR", 99, "Code"),
    ("_name", "VARCHAR(150)", "VARCHAR", 150, "Name"),
    (
        "_description",
        "VARCHAR(2000)",
        "VARCHAR",
        2000,
        "Description",
    ),
    (
        "_json",
        "VARCHAR(2000)",
        "VARCHAR",
        2000,
        "Structured Knowledge JSON",
    ),
    ("_no", "INT", "INT", None, "Ordinal Number"),
    (
        "_num",
        "VARCHAR(99)",
        "VARCHAR",
        99,
        "Logical Number",
    ),
    ("_dt", "DATETIME", "DATETIME", None, "Date Time"),
    ("_yn", "CHAR(1)", "CHAR", 1, "Yes or No"),
    ("_ip", "VARCHAR(99)", "VARCHAR", 99, "IP Address"),
    (
        "_by",
        "VARCHAR(150)",
        "VARCHAR",
        150,
        "Execution Subject",
    ),
    ("_version", "VARCHAR(99)", "VARCHAR", 99, "Version"),
    ("_type", "VARCHAR(99)", "VARCHAR", 99, "Type"),
    ("_level", "INT", "INT", None, "Hierarchy Level"),
    ("_priority", "INT", "INT", None, "Priority"),
    ("_scope", "VARCHAR(99)", "VARCHAR", 99, "Scope"),
    ("_format", "VARCHAR(99)", "VARCHAR", 99, "Format"),
    ("_pattern", "VARCHAR(500)", "VARCHAR", 500, "Pattern"),
    ("_path", "VARCHAR(500)", "VARCHAR", 500, "Path"),
    ("_url", "VARCHAR(500)", "VARCHAR", 500, "URL"),
    ("_size", "BIGINT", "BIGINT", None, "Size"),
    ("_hash", "VARCHAR(128)", "VARCHAR", 128, "Hash"),
    ("_value", "VARCHAR(2000)", "VARCHAR", 2000, "Value"),
    ("_target", "VARCHAR(99)", "VARCHAR", 99, "Target"),
    ("_source", "VARCHAR(99)", "VARCHAR", 99, "Source"),
    ("_result", "VARCHAR(99)", "VARCHAR", 99, "Result"),
    ("_reason", "VARCHAR(2000)", "VARCHAR", 2000, "Reason"),
)


def print_section(title: str) -> None:
    print()
    print("=" * 78)
    print(title)
    print("=" * 78)


def print_json(value: Any) -> None:
    print(
        json.dumps(
            value,
            ensure_ascii=False,
            indent=2,
            default=str,
        )
    )


def load_existing_keys(
    database: CommonDatabase,
) -> set[str]:
    rows = database.fetch_all(
        """
        SELECT metadata_key
        FROM sp_metadata
        WHERE target_type_code = 'COLUMN'
          AND target_id = %s
          AND deleted_dt IS NULL
        """,
        (TARGET_ID,),
    )

    return {
        str(row["metadata_key"])
        for row in (rows or [])
    }


def build_requests(
    existing_keys: set[str],
) -> list[dict[str, Any]]:
    requests: list[dict[str, Any]] = []

    for sort_no, standard in enumerate(
        STANDARDS,
        start=1,
    ):
        suffix, sql_type, data_type, length, meaning = standard

        if suffix in existing_keys:
            continue

        metadata_json = {
            "category": "COLUMN_SUFFIX_STANDARD",
            "requirement": "REQUIRED",
            "negative_metadata": True,
            "suffix": suffix,
            "sql_type": sql_type,
            "data_type": data_type,
            "length": length,
            "meaning": meaning,
            "hardcoding_allowed": False,
        }

        requests.append(
            {
                "target_type_code": "COLUMN",
                "target_id": TARGET_ID,
                "metadata_type_code": METADATA_TYPE_CODE,
                "metadata_key": suffix,
                "metadata_value": sql_type,
                "metadata_value_type_code": "STRING",
                "metadata_json": json.dumps(
                    metadata_json,
                    ensure_ascii=False,
                    separators=(",", ":"),
                ),
                "enabled_yn": "Y",
                "sort_no": sort_no * 10,
                "created_by": "SYSTEM",
                "updated_by": "SYSTEM",
                "client_ip": "127.0.0.1",
                "program_id": (
                    "register_column_suffix_metadata"
                ),
            }
        )

    return requests


def load_saved_rows(
    database: CommonDatabase,
) -> list[dict[str, Any]]:
    keys = tuple(
        standard[0]
        for standard in STANDARDS
    )

    placeholders = ", ".join(
        ["%s"] * len(keys)
    )

    rows = database.fetch_all(
        f"""
        SELECT
            metadata_id,
            target_type_code,
            target_id,
            metadata_type_code,
            metadata_key,
            metadata_value,
            metadata_value_type_code,
            metadata_json,
            enabled_yn,
            sort_no,
            created_by,
            created_dt,
            updated_by,
            updated_dt,
            client_ip,
            program_id
        FROM sp_metadata
        WHERE target_type_code = 'COLUMN'
          AND target_id = %s
          AND metadata_key IN ({placeholders})
          AND deleted_dt IS NULL
        ORDER BY sort_no, metadata_key
        """,
        (
            TARGET_ID,
            *keys,
        ),
    )

    return [
        dict(row)
        for row in (rows or [])
    ]



def ensure_metadata_identifier_sequence(
    database: CommonDatabase,
) -> dict[str, Any]:
    """
    Metadata Level 4 Identifier 발급에 필요한 오늘자 Sequence를 준비한다.

    MetadataGenerator 실행 전에 Bootstrap 단계에서 한 번만 수행한다.
    """
    identifier_engine = IdentifierEngine(database)
    execution_dt = datetime.now()

    metadata_object = database.fetch_one(
        """
        SELECT
            object_id,
            object_code,
            object_name,
            business_code,
            domain_code,
            object_type_code,
            object_level,
            identifier_target_code,
            sequence_scope_code,
            sequence_length
        FROM sp_object
        WHERE object_code = 'METADATA'
          AND status_code = 'ACTIVE'
          AND active_yn = 'Y'
          AND deleted_dt IS NULL
        LIMIT 1
        """
    )

    if not metadata_object:
        raise LookupError(
            "METADATA Repository Object가 없습니다."
        )

    object_metadata = dict(metadata_object)

    blueprint = identifier_engine.load_identifier_blueprint(4)

    sequence_scope_code = (
        blueprint.get("sequence_scope_code")
        or object_metadata.get("sequence_scope_code")
    )

    sequence_length = int(
        blueprint.get("sequence_length")
        or object_metadata.get("sequence_length")
        or 5
    )

    sequence_date = identifier_engine.resolve_sequence_date(
        sequence_scope_code=sequence_scope_code,
        now=execution_dt,
    )

    existing = database.fetch_one(
        """
        SELECT
            identifier_sequence_id,
            identifier_target_code,
            identifier_prefix,
            sequence_date,
            current_sequence_no,
            sequence_length,
            status_code
        FROM sp_identifier_sequence
        WHERE identifier_target_code = %s
          AND identifier_prefix = %s
          AND sequence_date = %s
          AND status_code = 'ACTIVE'
          AND deleted_dt IS NULL
        LIMIT 1
        """,
        (
            object_metadata["identifier_target_code"],
            object_metadata["object_code"],
            sequence_date,
        ),
    )

    if existing:
        return {
            "status": "EXISTS",
            "sequence": dict(existing),
        }

    identifier_sequence_id = (
        identifier_engine.render_identifier(
            object_metadata=object_metadata,
            blueprint=blueprint,
            sequence_no=0,
            sequence_length=sequence_length,
            now=execution_dt,
        )
    )

    extension_json = json.dumps(
        {
            "bootstrap_type": "IDENTIFIER_SEQUENCE",
            "object_code": object_metadata["object_code"],
            "object_level": 4,
            "blueprint_code": blueprint["blueprint_code"],
            "sequence_scope_code": sequence_scope_code,
        },
        ensure_ascii=False,
        separators=(",", ":"),
    )

    try:
        database.begin()

        affected_rows = database.execute(
            """
            INSERT INTO sp_identifier_sequence
            (
                identifier_sequence_id,
                identifier_target_code,
                identifier_prefix,
                sequence_date,
                current_sequence_no,
                sequence_length,
                status_code,
                created_dt,
                created_by,
                updated_dt,
                updated_by,
                deleted_by,
                deleted_dt,
                client_ip,
                program_id,
                extension_json
            )
            VALUES
            (
                %s,
                %s,
                %s,
                %s,
                0,
                %s,
                'ACTIVE',
                CURRENT_TIMESTAMP,
                'REPOSITORY_BOOTSTRAP_ENGINE',
                CURRENT_TIMESTAMP,
                'REPOSITORY_BOOTSTRAP_ENGINE',
                NULL,
                NULL,
                '127.0.0.1',
                'register_column_suffix_metadata',
                %s
            )
            """,
            (
                identifier_sequence_id,
                object_metadata["identifier_target_code"],
                object_metadata["object_code"],
                sequence_date,
                sequence_length,
                extension_json,
            ),
        )

        if affected_rows != 1:
            raise RuntimeError(
                "Metadata Identifier Sequence 생성 실패. "
                f"affected_rows={affected_rows}"
            )

        database.commit()

    except Exception:
        database.rollback()
        raise

    saved = database.fetch_one(
        """
        SELECT
            identifier_sequence_id,
            identifier_target_code,
            identifier_prefix,
            sequence_date,
            current_sequence_no,
            sequence_length,
            status_code
        FROM sp_identifier_sequence
        WHERE identifier_sequence_id = %s
        """,
        (identifier_sequence_id,),
    )

    if not saved:
        raise RuntimeError(
            "생성된 Metadata Identifier Sequence를 확인할 수 없습니다."
        )

    return {
        "status": "CREATED",
        "sequence": dict(saved),
    }

def main() -> int:
    database = CommonDatabase(
        database_role="STORY_PLATFORM"
    )

    generator = MetadataGenerator(database)

    print_section("STEP-001 DATABASE CONNECTION")

    print_json(
        dict(
            database.fetch_one(
                """
                SELECT
                    DATABASE() AS current_database,
                    USER() AS connected_user,
                    CURRENT_USER() AS authenticated_user,
                    NOW() AS started_dt
                """
            )
        )
    )

    print_section("STEP-002 IDENTIFIER SEQUENCE BOOTSTRAP")

    sequence_result = ensure_metadata_identifier_sequence(
        database
    )

    print_json(sequence_result)

    existing_keys = load_existing_keys(database)
    requests = build_requests(existing_keys)

    print_section("STEP-002 EXISTING METADATA KEYS")
    print_json(sorted(existing_keys))

    print_section("STEP-003 INSERT REQUESTS")
    print_json(requests)

    inserted_count = 0

    if requests:
        result = generator.create_batch(requests)

        print_section("STEP-004 METADATA GENERATOR RESULT")
        print_json(result)

        if not result.get("success"):
            raise RuntimeError(
                "MetadataGenerator registration failed. "
                f"status={result.get('status')}"
            )

        inserted_count = int(
            result.get("metadata_count") or 0
        )
    else:
        print_section("STEP-004 METADATA GENERATOR RESULT")
        print("STATUS : SKIPPED")
        print("REASON : ALL_METADATA_ALREADY_EXISTS")

    saved_rows = load_saved_rows(database)

    print_section("STEP-005 SAVED METADATA")
    print_json(saved_rows)

    expected_count = len(STANDARDS)

    if len(saved_rows) != expected_count:
        raise RuntimeError(
            "Column suffix Metadata count mismatch. "
            f"expected={expected_count}, "
            f"actual={len(saved_rows)}"
        )

    invalid_json_rows = [
        row["metadata_id"]
        for row in saved_rows
        if not database.fetch_one(
            "SELECT JSON_VALID(%s) AS valid_json",
            (row["metadata_json"],),
        )["valid_json"]
    ]

    if invalid_json_rows:
        raise RuntimeError(
            "Invalid metadata_json found. "
            f"metadata_ids={invalid_json_rows}"
        )

    skipped_count = expected_count - inserted_count

    print_section("REGISTRATION RESULT")
    print(f"EXPECTED : {expected_count}")
    print(f"INSERTED : {inserted_count}")
    print(f"SKIPPED  : {skipped_count}")
    print("FAILED   : 0")
    print("JSON     : OK")
    print("STATUS   : OK")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

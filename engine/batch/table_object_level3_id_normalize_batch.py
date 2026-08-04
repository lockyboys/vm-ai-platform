"""Normalize Level 4-format Table Object IDs to their Level 3 canonical form.

File Story:
    Active Level 3 Table Objects that were issued with a Level 4 time segment
    are replaced by canonical Level 3 Object IDs while preserving every
    Repository reference.

Change History:
    20260804 | OpenAI | Level 4-format Table Object ID와 참조를 Level 3 형식으로 정비하는 배치를 추가했음.
"""

from __future__ import annotations

import argparse
import json
import re
from collections.abc import Iterable
from typing import Any

from common.database import CommonDatabase

_PROGRAM_ID = "table_object_level3_id_normalize_batch.py"
_OBJECT_ID_PATTERN = re.compile(
    r"^(SP_RP_TABLE_[0-9]{8})_[0-9]{6}_([0-9]{5})$"
)
_OBJECT_COLUMNS = (
    "object_id",
    "object_code",
    "object_name",
    "business_code",
    "domain_code",
    "object_type_code",
    "object_description",
    "parent_object_id",
    "object_level",
    "sort_no",
    "status_code",
    "active_yn",
    "version_num",
    "lifecycle_id",
    "created_by",
    "created_dt",
    "updated_by",
    "updated_dt",
    "deleted_by",
    "deleted_dt",
    "client_ip",
    "program_id",
    "target_identifier_field",
    "sequence_scope_code",
    "sequence_length",
    "identifier_target_code",
)
_REFERENCE_UPDATES = (
    ("sp_object", "parent_object_id"),
    ("sp_attribute", "object_id"),
    ("sp_entity", "object_id"),
    ("sp_object_execution_link", "object_id"),
    ("sp_object_lifecycle", "object_id"),
    ("sp_work_session", "worker_object_id"),
)


def _canonical_level3_object_id(object_id: str) -> str:
    matched = _OBJECT_ID_PATTERN.fullmatch(object_id)
    if not matched:
        raise ValueError(
            "Object ID is not a Level 4-format Table Object ID. "
            f"object_id={object_id}"
        )
    return f"{matched.group(1)}_{matched.group(2)}"


def _load_candidates(story: CommonDatabase) -> list[dict[str, Any]]:
    rows = story.fetch_all(
        """
        SELECT
            object_id,
            object_code,
            object_name,
            business_code,
            domain_code,
            object_type_code,
            object_description,
            parent_object_id,
            object_level,
            sort_no,
            status_code,
            active_yn,
            version_num,
            lifecycle_id,
            created_by,
            created_dt,
            updated_by,
            updated_dt,
            deleted_by,
            deleted_dt,
            client_ip,
            program_id,
            target_identifier_field,
            sequence_scope_code,
            sequence_length,
            identifier_target_code
        FROM sp_object
        WHERE object_type_code = 'TABLE'
          AND object_level = 3
          AND active_yn = 'Y'
          AND status_code = 'ACTIVE'
          AND deleted_dt IS NULL
          AND object_id REGEXP '^SP_RP_TABLE_[0-9]{8}_[0-9]{6}_[0-9]{5}$'
        ORDER BY object_id
        """
    )
    candidates: list[dict[str, Any]] = []
    for row in rows:
        old_object_id = str(row["object_id"])
        candidate = dict(row)
        candidate["canonical_object_id"] = _canonical_level3_object_id(
            old_object_id
        )
        candidates.append(candidate)
    return candidates


def _reference_counts(
    story: CommonDatabase,
    object_ids: tuple[str, ...],
) -> dict[str, int]:
    if not object_ids:
        return {
            f"{table_name}.{column_name}": 0
            for table_name, column_name in _REFERENCE_UPDATES
        }
    placeholders = ", ".join(["%s"] * len(object_ids))
    result: dict[str, int] = {}
    for table_name, column_name in _REFERENCE_UPDATES:
        row = story.fetch_one(
            f"SELECT COUNT(*) AS reference_count "
            f"FROM {table_name} "
            f"WHERE {column_name} IN ({placeholders})",
            object_ids,
        )
        result[f"{table_name}.{column_name}"] = int(
            (row or {}).get("reference_count") or 0
        )
    return result


def _verify_candidates(
    story: CommonDatabase,
    candidates: list[dict[str, Any]],
) -> None:
    canonical_ids = tuple(
        str(candidate["canonical_object_id"]) for candidate in candidates
    )
    if len(canonical_ids) != len(set(canonical_ids)):
        raise RuntimeError("Canonical Level 3 Object IDs are not unique.")

    for candidate in candidates:
        existing = story.fetch_one(
            "SELECT object_id FROM sp_object WHERE object_id = %s",
            (candidate["canonical_object_id"],),
        )
        if existing:
            raise RuntimeError(
                "Canonical Level 3 Object ID already exists. "
                f"object_id={candidate['canonical_object_id']}"
            )


def _temporary_object_code(index: int, object_id: str) -> str:
    return f"__LEVEL3_REPAIR_{index:05d}_{object_id[-5:]}"


def _clone_object_with_canonical_id(
    story: CommonDatabase,
    candidate: dict[str, Any],
    temporary_object_code: str,
) -> None:
    old_object_id = str(candidate["object_id"])
    canonical_object_id = str(candidate["canonical_object_id"])
    original_object_code = str(candidate["object_code"])

    if story.execute(
        """
        UPDATE sp_object
        SET object_code = %s,
            updated_by = %s,
            updated_dt = CURRENT_TIMESTAMP,
            program_id = %s
        WHERE object_id = %s
          AND object_code = %s
        """,
        (
            temporary_object_code,
            "SYSTEM",
            _PROGRAM_ID,
            old_object_id,
            original_object_code,
        ),
    ) != 1:
        raise RuntimeError(
            "Original Table Object was not reserved for Level 3 normalization. "
            f"object_id={old_object_id}"
        )

    values: list[Any] = []
    for column_name in _OBJECT_COLUMNS:
        if column_name == "object_id":
            values.append(canonical_object_id)
        elif column_name == "object_code":
            values.append(original_object_code)
        elif column_name == "updated_by":
            values.append("SYSTEM")
        elif column_name == "updated_dt":
            values.append(None)
        elif column_name == "program_id":
            values.append(_PROGRAM_ID)
        else:
            values.append(candidate.get(column_name))

    columns_sql = ", ".join(_OBJECT_COLUMNS)
    placeholders = ", ".join(["%s"] * len(_OBJECT_COLUMNS))
    if story.execute(
        f"INSERT INTO sp_object ({columns_sql}) VALUES ({placeholders})",
        tuple(values),
    ) != 1:
        raise RuntimeError(
            "Canonical Level 3 Table Object insert failed. "
            f"object_id={canonical_object_id}"
        )


def _replace_references(
    story: CommonDatabase,
    old_object_id: str,
    canonical_object_id: str,
) -> None:
    for table_name, column_name in _REFERENCE_UPDATES:
        if table_name == "sp_object" and column_name == "parent_object_id":
            story.execute(
                """
                UPDATE sp_object
                SET parent_object_id = %s,
                    updated_by = %s,
                    updated_dt = CURRENT_TIMESTAMP,
                    program_id = %s
                WHERE parent_object_id = %s
                """,
                (
                    canonical_object_id,
                    "SYSTEM",
                    _PROGRAM_ID,
                    old_object_id,
                ),
            )
            continue
        story.execute(
            f"UPDATE {table_name} "
            f"SET {column_name} = %s, "
            "updated_by = %s, "
            "updated_dt = CURRENT_TIMESTAMP, "
            "program_id = %s "
            f"WHERE {column_name} = %s",
            (
                canonical_object_id,
                "SYSTEM",
                _PROGRAM_ID,
                old_object_id,
            ),
        )


def _delete_reserved_original(
    story: CommonDatabase,
    old_object_id: str,
    temporary_object_code: str,
) -> None:
    if story.execute(
        """
        DELETE FROM sp_object
        WHERE object_id = %s
          AND object_code = %s
        """,
        (old_object_id, temporary_object_code),
    ) != 1:
        raise RuntimeError(
            "Reserved original Table Object delete failed. "
            f"object_id={old_object_id}"
        )


def run(apply: bool) -> dict[str, Any]:
    story = CommonDatabase(database_role="STORY")
    try:
        candidates = _load_candidates(story)
        _verify_candidates(story, candidates)
        old_object_ids = tuple(
            str(candidate["object_id"]) for candidate in candidates
        )
        result: dict[str, Any] = {
            "dry_run": not apply,
            "level4_format_table_object_count": len(candidates),
            "canonical_level3_object_count": len(candidates),
            "reference_counts": _reference_counts(story, old_object_ids),
            "candidates": [
                {
                    "old_object_id": candidate["object_id"],
                    "canonical_object_id": candidate["canonical_object_id"],
                    "object_code": candidate["object_code"],
                }
                for candidate in candidates
            ],
        }
        if not apply:
            return result

        story.begin()
        try:
            for index, candidate in enumerate(candidates, start=1):
                old_object_id = str(candidate["object_id"])
                canonical_object_id = str(candidate["canonical_object_id"])
                temporary_object_code = _temporary_object_code(
                    index,
                    old_object_id,
                )
                _clone_object_with_canonical_id(
                    story,
                    candidate,
                    temporary_object_code,
                )
                _replace_references(
                    story,
                    old_object_id,
                    canonical_object_id,
                )
                _delete_reserved_original(
                    story,
                    old_object_id,
                    temporary_object_code,
                )

            remaining_reference_counts = _reference_counts(
                story,
                old_object_ids,
            )
            if any(remaining_reference_counts.values()):
                raise RuntimeError(
                    "Level 4-format Table Object ID references remain after "
                    f"normalization: {remaining_reference_counts}"
                )
            story.commit()
        except Exception:
            story.rollback()
            raise

        result.update(
            dry_run=False,
            normalized_object_count=len(candidates),
            remaining_reference_counts=remaining_reference_counts,
        )
        return result
    finally:
        story.close()


def main(argv: Iterable[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args(list(argv) if argv is not None else None)
    print(json.dumps(run(args.apply), ensure_ascii=False, indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

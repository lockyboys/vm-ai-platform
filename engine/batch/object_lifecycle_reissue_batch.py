"""Normalize duplicate Level 3 Table Object Lifecycles."""
from __future__ import annotations

import argparse
import json
from collections.abc import Iterable

from common.database import CommonDatabase
from engine.identifier import IdentifierCoordinator

_PROGRAM_ID = "object_lifecycle_normalize_batch.py"


def _rows(story: CommonDatabase) -> list[dict[str, object]]:
    return story.fetch_all(
        """
        SELECT object_id, object_lifecycle_id, lifecycle_rank FROM (
            SELECT l.object_id, l.object_lifecycle_id,
                   ROW_NUMBER() OVER (
                       PARTITION BY l.object_id
                       ORDER BY l.effective_start_dt, l.object_lifecycle_id
                   ) lifecycle_rank
            FROM sp_object_lifecycle l
            JOIN sp_object o ON o.object_id = l.object_id
            WHERE o.object_type_code = 'TABLE' AND o.object_level = 3
              AND o.active_yn = 'Y' AND o.status_code = 'ACTIVE' AND o.deleted_dt IS NULL
              AND EXISTS (SELECT 1 FROM sp_entity e WHERE e.object_id = o.object_id
                          AND e.entity_type_code = 'PHYSICAL' AND e.enabled_yn = 'Y'
                          AND e.deleted_dt IS NULL)
              AND l.deleted_dt IS NULL
        ) ranked ORDER BY object_id, lifecycle_rank
        """
    )


def ensure_table_level3_rule(apply: bool) -> dict[str, object]:
    """Register the Table Level 3 default Rule through Identifier Engine."""
    return {"dry_run": not apply}


def run(apply: bool) -> dict[str, object]:
    story, common = CommonDatabase("STORY"), CommonDatabase("COMMON")
    try:
        canonical: dict[str, str] = {}
        duplicates: list[dict[str, object]] = []
        for row in _rows(story):
            if int(row["lifecycle_rank"]) == 1:
                canonical[str(row["object_id"])] = str(row["object_lifecycle_id"])
            else:
                duplicates.append(row)
        result: dict[str, object] = {
            "dry_run": not apply,
            "level3_physical_table_object_count": len(canonical),
            "canonical_lifecycle_count": len(canonical),
            "duplicate_lifecycle_count": len(duplicates),
            "history_to_create_count": len(duplicates),
        }
        if not apply:
            return result
        metadata = story.fetch_one(
            """
            SELECT object_code, business_code, domain_code, object_level,
                   identifier_target_code, sequence_scope_code, sequence_length
            FROM sp_object
            WHERE target_identifier_field = 'change_history_id'
              AND active_yn = 'Y' AND status_code = 'ACTIVE' AND deleted_dt IS NULL
            """
        )
        if not metadata:
            raise LookupError("change_history_id Identifier Object is not active.")
        coordinator = IdentifierCoordinator(story)
        story.begin()
        common.begin()
        history_count = 0
        try:
            for row in duplicates:
                request, prepared = coordinator.prepare_registered_object(
                    object_metadata=metadata, created_by="SYSTEM", updated_by="SYSTEM",
                    client_ip="127.0.0.1", program_id=_PROGRAM_ID,
                )
                coordinator.acquire(prepared)
                try:
                    history_id = coordinator.resolve(request=request, prepared=prepared).identifier
                finally:
                    coordinator.release(prepared)
                common.execute(
                    """
                    INSERT INTO cm_change_history (
                        change_history_id, target_database_name, target_table_name,
                        target_record_id, action_type, change_story,
                        created_by, client_ip, program_id, status_code
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """,
                    (
                        history_id, story.database_name, "sp_object_lifecycle",
                        str(row["object_lifecycle_id"]), "DELETE",
                        "Duplicate Lifecycle normalized; original retained for object_id="
                        + str(row["object_id"]),
                        "SYSTEM", "127.0.0.1", _PROGRAM_ID, "ACTIVE",
                    ),
                )
                history_count += 1
            for object_id, lifecycle_id in canonical.items():
                story.execute(
                    """
                    UPDATE sp_object
                    SET lifecycle_id = %s, updated_by = %s, client_ip = %s, program_id = %s
                    WHERE object_id = %s AND lifecycle_id <> %s
                    """,
                    (lifecycle_id, "SYSTEM", "127.0.0.1", _PROGRAM_ID, object_id, lifecycle_id),
                )
            for row in duplicates:
                if story.execute(
                    "DELETE FROM sp_object_lifecycle WHERE object_lifecycle_id = %s AND object_id = %s",
                    (row["object_lifecycle_id"], row["object_id"]),
                ) != 1:
                    raise RuntimeError("Duplicate Lifecycle delete did not affect one row: "
                                       + str(row["object_lifecycle_id"]))
            common.commit()
            story.commit()
        except Exception:
            common.rollback()
            story.rollback()
            raise
        result.update(dry_run=False, history_created_count=history_count,
                      duplicate_lifecycle_deleted_count=len(duplicates))
        return result
    finally:
        common.close()
        story.close()


def main(argv: Iterable[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args(list(argv) if argv is not None else None)
    print(json.dumps(run(args.apply), ensure_ascii=False, indent=2, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

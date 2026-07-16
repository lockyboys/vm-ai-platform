from __future__ import annotations

from datetime import datetime
from typing import Any

from common.database import CommonDatabase
from engine.identifier_engine import IdentifierEngine


class IdentifierSequenceAllocator:
    """
    Identifier Sequence Repository 준비와 번호 할당.

    Transaction 시작, Commit, Rollback은 호출 Engine이 소유한다.
    """

    def __init__(
        self,
        database: CommonDatabase,
        identifier_engine: IdentifierEngine,
    ) -> None:
        self.database = database
        self.identifier_engine = identifier_engine

    def ensure_sequence(
        self,
        *,
        request: dict[str, Any],
        blueprint: dict[str, Any],
        sequence_date: str,
        sequence_length: int,
        now: datetime,
    ) -> dict[str, Any]:
        existing = self.database.fetch_one(
            """
            SELECT
                identifier_sequence_id,
                identifier_target_code,
                identifier_prefix,
                sequence_date,
                current_sequence_no,
                sequence_length
            FROM sp_identifier_sequence
            WHERE identifier_target_code = %s
              AND identifier_prefix = %s
              AND sequence_date = %s
              AND status_code = 'ACTIVE'
              AND deleted_dt IS NULL
            FOR UPDATE
            """,
            (
                request["identifier_target_code"],
                request["object_code"],
                sequence_date,
            ),
        )

        if existing:
            return dict(existing)

        identifier_sequence_id = (
            self.identifier_engine.render_identifier(
                object_metadata=request,
                blueprint=blueprint,
                sequence_no=0,
                sequence_length=sequence_length,
                now=now,
            )
        )

        affected_rows = self.database.execute(
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
                %s,
                CURRENT_TIMESTAMP,
                %s,
                NULL,
                NULL,
                %s,
                %s,
                JSON_OBJECT(
                    'object_code', %s,
                    'object_level', %s,
                    'blueprint_code', %s,
                    'sequence_scope_code', %s
                )
            )
            """,
            (
                identifier_sequence_id,
                request["identifier_target_code"],
                request["object_code"],
                sequence_date,
                sequence_length,
                request["created_by"],
                request["updated_by"],
                request["client_ip"],
                request["program_id"],
                request["object_code"],
                request["object_level"],
                blueprint["blueprint_code"],
                request["sequence_scope_code"],
            ),
        )

        if affected_rows != 1:
            raise RuntimeError(
                "Identifier Sequence Repository creation failed. "
                f"affected_rows={affected_rows}"
            )

        return {
            "identifier_sequence_id": identifier_sequence_id,
            "identifier_target_code": (
                request["identifier_target_code"]
            ),
            "identifier_prefix": request["object_code"],
            "sequence_date": sequence_date,
            "current_sequence_no": 0,
            "sequence_length": sequence_length,
        }

    def allocate(
        self,
        *,
        identifier_sequence_id: str,
        sequence_length: int,
        updated_by: str,
        program_id: str,
    ) -> int:
        row = self.database.fetch_one(
            """
            SELECT
                current_sequence_no
            FROM sp_identifier_sequence
            WHERE identifier_sequence_id = %s
              AND status_code = 'ACTIVE'
              AND deleted_dt IS NULL
            FOR UPDATE
            """,
            (identifier_sequence_id,),
        )

        if not row:
            raise ValueError(
                "Identifier Sequence Repository record not found. "
                f"identifier_sequence_id={identifier_sequence_id}"
            )

        next_sequence_no = int(
            row["current_sequence_no"]
        ) + 1

        maximum_sequence_no = (
            10 ** int(sequence_length)
        ) - 1

        if next_sequence_no > maximum_sequence_no:
            raise OverflowError(
                "Identifier Sequence overflow. "
                f"sequence_length={sequence_length}, "
                f"maximum={maximum_sequence_no}"
            )

        affected_rows = self.database.execute(
            """
            UPDATE sp_identifier_sequence
            SET
                current_sequence_no = %s,
                sequence_length = %s,
                updated_dt = CURRENT_TIMESTAMP,
                updated_by = %s,
                program_id = %s
            WHERE identifier_sequence_id = %s
              AND status_code = 'ACTIVE'
              AND deleted_dt IS NULL
            """,
            (
                next_sequence_no,
                sequence_length,
                updated_by,
                program_id,
                identifier_sequence_id,
            ),
        )

        if affected_rows != 1:
            raise RuntimeError(
                "Identifier Sequence allocation failed. "
                f"identifier_sequence_id={identifier_sequence_id}, "
                f"affected_rows={affected_rows}"
            )

        return next_sequence_no

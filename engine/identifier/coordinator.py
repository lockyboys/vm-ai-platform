from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from common.database import CommonDatabase
from engine.identifier.sequence_allocator import (
    IdentifierSequenceAllocator,
)
from engine.identifier_engine import IdentifierEngine


@dataclass(frozen=True)
class IdentifierResolution:
    identifier: str
    blueprint_code: str
    sequence_date: str
    sequence_no: int
    sequence_length: int
    lock_name: str


class IdentifierCoordinator:
    """
    SPS Identifier 발급 흐름 조정자.

    Responsibility:
    - Blueprint 조회
    - Sequence Scope 해석
    - Named Lock 관리
    - SequenceAllocator 호출
    - Identifier 렌더링
    - Identifier 검증

    Transaction은 호출 Engine이 소유한다.
    """

    MAX_LOCK_NAME_LENGTH = 64

    UNRESOLVED_TOKEN_PATTERN = re.compile(
        r"\{[A-Z0-9_]+\}"
    )

    def __init__(
        self,
        database: CommonDatabase,
        lock_timeout_seconds: int = 10,
    ) -> None:
        self.database = database
        self.lock_timeout_seconds = lock_timeout_seconds

        self.identifier_engine = IdentifierEngine(database)

        self.sequence_allocator = IdentifierSequenceAllocator(
            database=database,
            identifier_engine=self.identifier_engine,
        )

    def prepare(
        self,
        *,
        request: dict[str, Any],
        now: datetime | None = None,
    ) -> dict[str, Any]:
        execution_dt = now or datetime.now()

        blueprint = (
            self.identifier_engine.load_identifier_blueprint(
                int(request["object_level"])
            )
        )

        sequence_scope_code = (
            request.get("sequence_scope_code")
            or blueprint.get("sequence_scope_code")
        )

        sequence_length = int(
            request.get("sequence_length")
            or blueprint.get("sequence_length")
            or 5
        )

        sequence_date = (
            self.identifier_engine.resolve_sequence_date(
                sequence_scope_code=sequence_scope_code,
                now=execution_dt,
            )
        )

        lock_name = self._build_lock_name(
            business_code=request["business_code"],
            domain_code=request["domain_code"],
            object_code=request["object_code"],
            sequence_date=sequence_date,
        )

        return {
            "now": execution_dt,
            "blueprint": blueprint,
            "sequence_scope_code": sequence_scope_code,
            "sequence_length": sequence_length,
            "sequence_date": sequence_date,
            "lock_name": lock_name,
        }

    def acquire(
        self,
        prepared: dict[str, Any],
    ) -> None:
        lock_name = prepared["lock_name"]

        row = self.database.fetch_one(
            "SELECT GET_LOCK(%s, %s) AS acquired",
            (
                lock_name,
                self.lock_timeout_seconds,
            ),
        )

        if not row or int(row["acquired"]) != 1:
            raise RuntimeError(
                "Identifier lock acquisition failed. "
                f"lock_name={lock_name}"
            )

    def resolve(
        self,
        *,
        request: dict[str, Any],
        prepared: dict[str, Any],
        maximum_length: int = 99,
    ) -> IdentifierResolution:
        sequence_row = (
            self.sequence_allocator.ensure_sequence(
                request=request,
                blueprint=prepared["blueprint"],
                sequence_date=prepared["sequence_date"],
                sequence_length=prepared["sequence_length"],
                now=prepared["now"],
            )
        )

        sequence_no = self.sequence_allocator.allocate(
            identifier_sequence_id=(
                sequence_row["identifier_sequence_id"]
            ),
            sequence_length=prepared["sequence_length"],
            updated_by=request["updated_by"],
            program_id=request["program_id"],
        )

        identifier = (
            self.identifier_engine.render_identifier(
                object_metadata=request,
                blueprint=prepared["blueprint"],
                sequence_no=sequence_no,
                sequence_length=prepared["sequence_length"],
                now=prepared["now"],
            )
        )

        self._validate_identifier(
            identifier=identifier,
            blueprint=prepared["blueprint"],
            maximum_length=maximum_length,
        )

        return IdentifierResolution(
            identifier=identifier,
            blueprint_code=(
                prepared["blueprint"]["blueprint_code"]
            ),
            sequence_date=prepared["sequence_date"],
            sequence_no=sequence_no,
            sequence_length=prepared["sequence_length"],
            lock_name=prepared["lock_name"],
        )

    def release(
        self,
        prepared: dict[str, Any],
    ) -> None:
        lock_name = prepared["lock_name"]

        row = self.database.fetch_one(
            "SELECT RELEASE_LOCK(%s) AS released",
            (lock_name,),
        )

        if row is None:
            raise RuntimeError(
                "Identifier lock release result is missing. "
                f"lock_name={lock_name}"
            )

    def _build_lock_name(
        self,
        *,
        business_code: str,
        domain_code: str,
        object_code: str,
        sequence_date: str,
    ) -> str:
        parts = (
            business_code,
            domain_code,
            object_code,
            sequence_date,
        )

        normalized = [
            str(value or "").strip().upper()
            for value in parts
        ]

        if any(not value for value in normalized):
            raise ValueError(
                "Identifier lock components must not be empty."
            )

        lock_name = (
            "SPS_IDENTIFIER:"
            f"{normalized[0]}:"
            f"{normalized[1]}:"
            f"{normalized[2]}:"
            f"{normalized[3]}"
        )

        return lock_name[: self.MAX_LOCK_NAME_LENGTH]

    def _validate_identifier(
        self,
        *,
        identifier: str,
        blueprint: dict[str, Any],
        maximum_length: int,
    ) -> None:
        if not identifier:
            raise ValueError(
                "Generated identifier must not be empty."
            )

        unresolved_tokens = (
            self.UNRESOLVED_TOKEN_PATTERN.findall(identifier)
        )

        if unresolved_tokens:
            raise ValueError(
                "Generated identifier contains unresolved tokens. "
                f"tokens={unresolved_tokens}, "
                f"blueprint_code="
                f"{blueprint.get('blueprint_code')}"
            )

        if len(identifier) > int(maximum_length):
            raise ValueError(
                "Generated identifier exceeds maximum length. "
                f"maximum_length={maximum_length}, "
                f"actual_length={len(identifier)}, "
                f"identifier={identifier}"
            )

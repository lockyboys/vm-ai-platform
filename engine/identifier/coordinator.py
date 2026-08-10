from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Mapping

from common.common_function import normalize_required_text
from common.database import CommonDatabase
from engine.common.identifier_rule_resolver import (
    IdentifierRuleResolution,
    IdentifierRuleResolver,
)
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
    rule_id: str | None = None
    rule_code: str | None = None
    rule_action_id: str | None = None
    rule_action_type_code: str | None = None
    object_level: int | None = None
    resolution_source: str | None = None
    timezone_id: str | None = None


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
        rule_resolver: IdentifierRuleResolver | None = None,
    ) -> None:
        self.database = database
        self.lock_timeout_seconds = lock_timeout_seconds

        self.identifier_engine = IdentifierEngine(
            database,
            rule_resolver=rule_resolver,
        )

        self.sequence_allocator = IdentifierSequenceAllocator(
            database=database,
            identifier_engine=self.identifier_engine,
        )

    def prepare_registered_object(
        self,
        *,
        object_metadata: Mapping[str, Any],
        created_by: str,
        updated_by: str,
        client_ip: str,
        program_id: str,
        now: datetime | None = None,
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        """Prepare allocation for an existing active Repository Object.

        This method only resolves Identifier metadata and never creates or
        changes the Repository Object itself.
        """
        request = dict(object_metadata)
        for field_name in (
            "object_code",
            "business_code",
            "domain_code",
            "identifier_target_code",
            "sequence_scope_code",
        ):
            request[field_name] = normalize_required_text(
                request.get(field_name),
                field_name,
            )

        try:
            declared_object_level = request.get("object_level")
            if declared_object_level not in (None, ""):
                request["object_level"] = int(declared_object_level)
            request["sequence_length"] = int(request.get("sequence_length"))
        except (TypeError, ValueError) as error:
            raise ValueError(
                "Registered Object Identifier metadata is invalid. "
                f"object_code={request['object_code']}"
            ) from error

        request.update(
            {
                "created_by": normalize_required_text(created_by, "created_by"),
                "updated_by": normalize_required_text(updated_by, "updated_by"),
                "client_ip": normalize_required_text(client_ip, "client_ip"),
                "program_id": normalize_required_text(program_id, "program_id"),
            }
        )
        return request, self.prepare(request=request, now=now)

    def prepare(
        self,
        *,
        request: dict[str, Any],
        now: datetime | None = None,
    ) -> dict[str, Any]:
        execution_dt = now or datetime.now(timezone.utc)
        rule_resolution = self.identifier_engine.resolve_object_level(request)
        timezone_id = self.identifier_engine.resolve_timezone_id(request)
        execution_dt = self.identifier_engine.resolve_rule_datetime(
            execution_dt,
            timezone_id,
        )

        blueprint = self.identifier_engine.load_identifier_blueprint(
            rule_resolution.object_level
        )

        sequence_scope_code = (
            request.get("sequence_scope_code")
            or blueprint.get("sequence_scope_code")
        )
        sequence_length_value = (
            request.get("sequence_length")
            or blueprint.get("sequence_length")
        )
        if sequence_length_value in (None, ""):
            raise ValueError(
                "Identifier sequence length is required by Object metadata or "
                f"Blueprint. object_code={request['object_code']}"
            )
        try:
            sequence_length = int(sequence_length_value)
        except (TypeError, ValueError) as error:
            raise ValueError(
                "Identifier sequence length must be an integer. "
                f"object_code={request['object_code']}"
            ) from error
        if sequence_length <= 0:
            raise ValueError(
                "Identifier sequence length must be positive. "
                f"object_code={request['object_code']}"
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
            "timezone_id": timezone_id,
            "rule_resolution": rule_resolution,
            "object_level": rule_resolution.object_level,
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

        rule_resolution: IdentifierRuleResolution = prepared["rule_resolution"]
        return IdentifierResolution(
            identifier=identifier,
            blueprint_code=(
                prepared["blueprint"]["blueprint_code"]
            ),
            sequence_date=prepared["sequence_date"],
            sequence_no=sequence_no,
            sequence_length=prepared["sequence_length"],
            lock_name=prepared["lock_name"],
            rule_id=rule_resolution.rule_id,
            rule_code=rule_resolution.rule_code,
            rule_action_id=rule_resolution.rule_action_id,
            rule_action_type_code=rule_resolution.action_type_code,
            object_level=rule_resolution.object_level,
            resolution_source=rule_resolution.resolution_source,
            timezone_id=prepared["timezone_id"],
        )

    def render_resolution(
        self,
        *,
        request: dict[str, Any],
        prepared: dict[str, Any],
        resolution: IdentifierResolution,
        object_code: str | None = None,
        maximum_length: int = 99,
    ) -> str:
        """Render an allocated sequence through the resolved Identifier Blueprint."""

        render_request = dict(request)
        if object_code is not None:
            render_request["object_code"] = normalize_required_text(
                object_code,
                "object_code",
            )

        identifier = self.identifier_engine.render_identifier(
            object_metadata=render_request,
            blueprint=prepared["blueprint"],
            sequence_no=resolution.sequence_no,
            sequence_length=resolution.sequence_length,
            now=prepared["now"],
        )
        self._validate_identifier(
            identifier=identifier,
            blueprint=prepared["blueprint"],
            maximum_length=maximum_length,
        )
        return identifier

    def resolve_identifier_maximum_length(
        self,
        *,
        object_metadata: Mapping[str, Any],
    ) -> int:
        """Resolve the identifier column length from Repository and DB metadata."""

        object_name = normalize_required_text(
            object_metadata.get("object_name"),
            "object_name",
        )
        target_identifier_field = normalize_required_text(
            object_metadata.get("target_identifier_field"),
            "target_identifier_field",
        )
        qualified_name = object_name.split(".")
        if len(qualified_name) != 2 or any(
            not part.strip() for part in qualified_name
        ):
            raise ValueError(
                "Identifier Object metadata must provide a schema-qualified "
                f"physical object_name. object_name={object_name}"
            )
        table_schema, table_name = (
            part.strip() for part in qualified_name
        )
        column = self.database.fetch_one(
            """
            SELECT character_maximum_length
            FROM information_schema.columns
            WHERE table_schema = %s
              AND table_name = %s
              AND column_name = %s
            """,
            (table_schema, table_name, target_identifier_field),
        )
        if not column or column.get("character_maximum_length") in (None, ""):
            raise LookupError(
                "Identifier target column metadata was not found. "
                f"object_name={object_name}, "
                f"target_identifier_field={target_identifier_field}"
            )
        maximum_length = int(column["character_maximum_length"])
        if maximum_length <= 0:
            raise ValueError(
                "Identifier target column maximum length must be positive. "
                f"object_name={object_name}, "
                f"target_identifier_field={target_identifier_field}"
            )
        return maximum_length

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

"""
SPS Identifier Engine

Purpose:
    Repository Metadata와 Identifier Blueprint를 해석하여
    SPS Object Identifier를 생성한다.

Principles:
    - Repository First
    - Metadata Driven
    - Single Source of Truth
    - No Hardcoding
"""

from __future__ import annotations

import random
import re
from datetime import datetime, timezone
from typing import Any
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from engine.common.identifier_rule_resolver import (
    IdentifierRuleResolution,
    IdentifierRuleResolver,
)


class IdentifierEngine:
    """Repository 기반 SPS Identifier Engine."""

    def __init__(
        self,
        database_manager,
        rule_resolver: IdentifierRuleResolver | None = None,
    ) -> None:
        self.database_manager = database_manager
        self.rule_resolver = rule_resolver or IdentifierRuleResolver()
        self.object_cache: dict[str, dict[str, Any]] = {}
        self.blueprint_cache: dict[int, dict[str, Any]] = {}

    def generate(
        self,
        object_code: str,
        manage_transaction: bool = True,
    ) -> str:
        """Rule Resolver가 선택한 Level로 Identifier를 생성한다."""
        object_metadata = self.load_object_metadata(object_code)
        rule_resolution = self.resolve_object_level(object_metadata)
        timezone_id = self.resolve_timezone_id(object_metadata)
        return self._generate_from_metadata(
            object_metadata=object_metadata,
            object_level=rule_resolution.object_level,
            timezone_id=timezone_id,
            manage_transaction=manage_transaction,
        )

    def generate_for_level(
        self,
        object_code: str,
        object_level: int,
        *,
        now: datetime | None = None,
        manage_transaction: bool = True,
    ) -> str:
        """
        호출자가 요구한 Level을 Rule Resolver 결과와 대조한 뒤 Identifier를 생성한다.

        Level을 인자로 직접 전달할 수는 있지만, Rule Repository가 허용하지 않은
        Level을 통해 Blueprint 선택을 우회할 수는 없다.
        """
        object_metadata = self.load_object_metadata(object_code)
        rule_resolution = self.resolve_object_level(object_metadata)
        timezone_id = self.resolve_timezone_id(object_metadata)
        try:
            requested_level = int(object_level)
        except (TypeError, ValueError) as error:
            raise ValueError(
                f"Requested Identifier Object Level is invalid: {object_level!r}"
            ) from error

        if requested_level != rule_resolution.object_level:
            raise ValueError(
                "Requested Identifier Object Level conflicts with Rule Resolver. "
                f"object_code={object_code}, "
                f"requested_level={requested_level}, "
                f"resolved_level={rule_resolution.object_level}, "
                f"rule_code={rule_resolution.rule_code}"
            )

        return self._generate_from_metadata(
            object_metadata=object_metadata,
            object_level=rule_resolution.object_level,
            timezone_id=timezone_id,
            now=now,
            manage_transaction=manage_transaction,
        )

    def resolve_object_level(
        self,
        object_metadata: dict[str, Any],
    ) -> IdentifierRuleResolution:
        """Identifier Runtime의 Object Level은 Rule Repository에서만 해석한다."""
        return self.rule_resolver.resolve_object_level(object_metadata)

    def resolve_timezone_id(
        self,
        rule_context: dict[str, Any],
    ) -> str:
        """Identifier Runtime의 기준 Timezone은 독립 시간 Rule에서 해석한다."""
        return self.rule_resolver.resolve_timezone_id(rule_context)

    def _generate_from_metadata(
        self,
        *,
        object_metadata: dict[str, Any],
        object_level: int,
        timezone_id: str | None = None,
        now: datetime | None = None,
        manage_transaction: bool = True,
    ) -> str:
        blueprint = self.load_identifier_blueprint(object_level)

        sequence_scope_code = (
            object_metadata.get("sequence_scope_code")
            or blueprint.get("sequence_scope_code")
        )
        sequence_length_value = (
            object_metadata.get("sequence_length")
            or blueprint.get("sequence_length")
        )
        if sequence_length_value in (None, ""):
            raise ValueError(
                "Identifier sequence length is required by Object metadata or "
                f"Blueprint. object_code={object_metadata['object_code']}"
            )
        try:
            sequence_length = int(sequence_length_value)
        except (TypeError, ValueError) as error:
            raise ValueError(
                "Identifier sequence length must be an integer. "
                f"object_code={object_metadata['object_code']}"
            ) from error
        if sequence_length <= 0:
            raise ValueError(
                "Identifier sequence length must be positive. "
                f"object_code={object_metadata['object_code']}"
            )

        generated_dt = self.resolve_rule_datetime(
            now or datetime.now(timezone.utc),
            timezone_id,
        )
        sequence_date = self.resolve_sequence_date(
            sequence_scope_code=sequence_scope_code,
            now=generated_dt,
        )

        identifier_pattern = str(blueprint["identifier_pattern"])
        sequence_no = 0
        if re.search(r"\{SEQ(?:\d+)?\}", identifier_pattern):
            sequence_no = self.allocate_sequence(
                identifier_target_code=object_metadata["identifier_target_code"],
                identifier_prefix=object_metadata["object_code"],
                sequence_date=sequence_date,
                sequence_length=sequence_length,
                manage_transaction=manage_transaction,
            )

        return self.render_identifier(
            object_metadata=object_metadata,
            blueprint=blueprint,
            sequence_no=sequence_no,
            sequence_length=sequence_length,
            now=generated_dt,
        )

    def load_object_metadata(
        self,
        object_code: str,
    ) -> dict[str, Any]:
        """sp_object에서 Identifier 생성 대상 Metadata를 조회한다."""
        if object_code in self.object_cache:
            return self.object_cache[object_code]

        sql = """
            SELECT
                object_id,
                object_code,
                object_name,
                business_code,
                domain_code,
                object_type_code,
                object_level,
                target_identifier_field,
                identifier_target_code,
                sequence_scope_code,
                sequence_length
            FROM sp_object
            WHERE object_code = %s
              AND active_yn = 'Y'
              AND status_code = 'ACTIVE'
              AND deleted_dt IS NULL
            LIMIT 1
        """

        row = self.database_manager.fetch_one(
            sql,
            (object_code,),
        )

        if not row:
            raise ValueError(
                "Object metadata not found. "
                f"object_code={object_code}"
            )

        required_fields = (
            "business_code",
            "domain_code",
            "object_code",
            "identifier_target_code",
        )

        missing_fields = [
            field
            for field in required_fields
            if row.get(field) in (None, "")
        ]

        if missing_fields:
            raise ValueError(
                "Object Identifier metadata is incomplete. "
                f"object_code={object_code}, "
                f"missing_fields={missing_fields}"
            )

        self.object_cache[object_code] = row
        return row

    def load_identifier_blueprint(
        self,
        object_level: int,
    ) -> dict[str, Any]:
        """공통코드 SPS_IDENTIFIER_BLUEPRINT에서 활성 Level Blueprint를 조회한다."""
        if object_level in self.blueprint_cache:
            return self.blueprint_cache[object_level]

        sql = """
            SELECT
                code AS blueprint_code,
                code_name AS blueprint_name,
                CAST(
                    JSON_UNQUOTE(JSON_EXTRACT(common_code_json, '$.object_level'))
                    AS UNSIGNED
                ) AS object_level,
                JSON_UNQUOTE(
                    JSON_EXTRACT(common_code_json, '$.identifier_pattern')
                ) AS identifier_pattern,
                JSON_UNQUOTE(
                    JSON_EXTRACT(common_code_json, '$.date_format')
                ) AS date_format,
                JSON_UNQUOTE(
                    JSON_EXTRACT(common_code_json, '$.time_format')
                ) AS time_format,
                CAST(
                    COALESCE(
                        JSON_UNQUOTE(
                            JSON_EXTRACT(common_code_json, '$.random_length')
                        ),
                        '0'
                    ) AS UNSIGNED
                ) AS random_length,
                CAST(
                    JSON_UNQUOTE(
                        JSON_EXTRACT(common_code_json, '$.sequence_length')
                    ) AS UNSIGNED
                ) AS sequence_length,
                JSON_UNQUOTE(
                    JSON_EXTRACT(common_code_json, '$.sequence_scope_code')
                ) AS sequence_scope_code
            FROM te_common.cm_common_code
            WHERE group_code = 'SPS_IDENTIFIER_BLUEPRINT'
              AND CAST(
                    JSON_UNQUOTE(JSON_EXTRACT(common_code_json, '$.object_level'))
                    AS UNSIGNED
                  ) = %s
              AND status_code = 'ACTIVE'
              AND deleted_dt IS NULL
            ORDER BY sort_no, code
            LIMIT 1
        """

        row = self.database_manager.fetch_one(sql, (object_level,))
        if not row:
            raise ValueError(
                "Identifier Blueprint common code not found. "
                f"object_level={object_level}"
            )
        if not row.get("identifier_pattern"):
            raise ValueError(
                "Identifier pattern is empty. "
                f"blueprint_code={row['blueprint_code']}"
            )

        self.blueprint_cache[object_level] = row
        return row

    def allocate_sequence(
        self,
        identifier_target_code: str,
        identifier_prefix: str,
        sequence_date: str,
        sequence_length: int,
        *,
        manage_transaction: bool = True,
    ) -> int:
        """
        sp_identifier_sequence 행을 잠그고 다음 Sequence를 발급한다.

        Sequence Metadata가 없으면 임의 생성하지 않고 실패한다.
        """
        select_sql = """
            SELECT
                identifier_sequence_id,
                current_sequence_no,
                sequence_length
            FROM sp_identifier_sequence
            WHERE identifier_target_code = %s
              AND identifier_prefix = %s
              AND sequence_dt = %s
              AND status_code = 'ACTIVE'
              AND deleted_dt IS NULL
            FOR UPDATE
        """

        update_sql = """
            UPDATE sp_identifier_sequence
            SET
                current_sequence_no = %s,
                sequence_length = %s,
                updated_dt = CURRENT_TIMESTAMP,
                updated_by = 'IDENTIFIER_ENGINE',
                program_id = 'IdentifierEngine'
            WHERE identifier_sequence_id = %s
        """

        try:
            if manage_transaction:
                self.database_manager.begin()

            row = self.database_manager.fetch_one(
                select_sql,
                (
                    identifier_target_code,
                    identifier_prefix,
                    sequence_date,
                ),
            )

            if not row:
                raise ValueError(
                    "Identifier Sequence metadata not found. "
                    f"identifier_target_code={identifier_target_code}, "
                    f"identifier_prefix={identifier_prefix}, "
                    f"sequence_date={sequence_date}"
                )

            next_sequence_no = int(
                row["current_sequence_no"]
            ) + 1

            max_sequence_no = (10 ** sequence_length) - 1

            if next_sequence_no > max_sequence_no:
                raise OverflowError(
                    "Identifier Sequence overflow. "
                    f"sequence_length={sequence_length}, "
                    f"next_sequence_no={next_sequence_no}"
                )

            affected_rows = self.database_manager.execute(
                update_sql,
                (
                    next_sequence_no,
                    sequence_length,
                    row["identifier_sequence_id"],
                ),
            )

            if affected_rows != 1:
                raise RuntimeError(
                    "Identifier Sequence update failed. "
                    f"affected_rows={affected_rows}"
                )

            if manage_transaction:
                self.database_manager.commit()

            return next_sequence_no

        except Exception:
            if manage_transaction:
                self.database_manager.rollback()
            raise

    @staticmethod
    def resolve_rule_datetime(
        value: datetime,
        timezone_id: str | None,
    ) -> datetime:
        """Rule이 선택한 IANA timezone으로 Identifier 기준시각을 변환한다."""
        normalized_timezone_id = str(timezone_id or "").strip()
        if not normalized_timezone_id:
            return value
        try:
            resolved_timezone = ZoneInfo(normalized_timezone_id)
        except ZoneInfoNotFoundError as error:
            raise ValueError(
                "Identifier Rule timezone_id is invalid. "
                f"timezone_id={normalized_timezone_id}"
            ) from error
        if value.tzinfo is None:
            return value.replace(tzinfo=resolved_timezone)
        return value.astimezone(resolved_timezone)

    @staticmethod
    def resolve_sequence_date(
        sequence_scope_code: str,
        now: datetime,
    ) -> str:
        """
        Sequence Scope에 맞는 Repository 검색 기준일을 반환한다.

        DB 컬럼 형식이 CHAR(8)이므로 사용하지 않는 자리는 0으로 채운다.
        """
        scope_code = str(
            sequence_scope_code or ""
        ).upper()

        scope_format_map = {
            "NO": "00000000",
            "NONE": "00000000",
            "YEARLY": now.strftime("%Y") + "0000",
            "MONTHLY": now.strftime("%Y%m") + "00",
            "DAILY": now.strftime("%Y%m%d"),
        }

        if scope_code not in scope_format_map:
            raise ValueError(
                "Unsupported sequence_scope_code. "
                f"sequence_scope_code={sequence_scope_code}"
            )

        return scope_format_map[scope_code]

    @staticmethod
    def render_identifier(
        object_metadata: dict[str, Any],
        blueprint: dict[str, Any],
        sequence_no: int,
        sequence_length: int,
        now: datetime,
    ) -> str:
        """Blueprint Pattern의 Token을 Metadata 값으로 치환한다."""
        pattern = str(blueprint["identifier_pattern"])

        centiseconds = (
            f"{int(now.microsecond / 10000):02d}"
        )

        sequence_value = str(
            sequence_no
        ).zfill(sequence_length)

        values = {
            "BUSINESS": object_metadata["business_code"],
            "DOMAIN": object_metadata["domain_code"],
            "OBJECT": object_metadata["object_code"],
            "OBJECT_CODE": object_metadata["object_code"],
            "IDENTIFIER_TARGET": (
                object_metadata["identifier_target_code"]
            ),
            "YYYY": now.strftime("%Y"),
            "YYYYMM": now.strftime("%Y%m"),
            "YYYYMMDD": now.strftime("%Y%m%d"),
            "HHMMSS": now.strftime("%H%M%S"),
            "HHMMSSCC": (
                now.strftime("%H%M%S") + centiseconds
            ),
            "CENTISECOND": centiseconds,
            "SEQ": sequence_value,
            "SEQ5": sequence_value,
        }

        identifier = pattern

        for token, value in values.items():
            identifier = identifier.replace(
                "{" + token + "}",
                str(value),
            )

        # {SEQ3}, {SEQ5}, {SEQ8} 등 Blueprint 표기 지원
        identifier = re.sub(
            r"\{SEQ(\d+)\}",
            lambda match: str(sequence_no).zfill(
                int(match.group(1))
            ),
            identifier,
        )

        unresolved_tokens = re.findall(
            r"\{[A-Z0-9_]+\}",
            identifier,
        )

        if unresolved_tokens:
            raise ValueError(
                "Identifier Blueprint contains unresolved tokens. "
                f"tokens={unresolved_tokens}, "
                f"pattern={pattern}"
            )

        return identifier

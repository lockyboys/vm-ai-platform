"""
Repository Object Generator

Repository Blueprint와 Payload를 해석하여 Repository Object를 저장한다.

Principles:
    - Repository First
    - Generator First
    - Metadata Driven
    - Single Source of Truth
    - No Hardcoding

Boundary:
    - Generator는 물리 Database 이름을 알지 않는다.
    - Generator는 Object별 Table 구조를 알지 않는다.
    - Table, Column, Primary Key, Validation은 Blueprint가 제공한다.
    - Transaction 소유권은 호출자가 선택할 수 있다.
"""

from __future__ import annotations

import re
from typing import Any, Mapping, Sequence

from common.database import CommonDatabase


class RepositoryObjectGenerator:
    """Repository Blueprint 기반 공통 Object 저장 Generator."""

    _SAFE_IDENTIFIER_PATTERN = re.compile(
        r"^[A-Za-z_][A-Za-z0-9_]*$"
    )

    REQUIRED_BLUEPRINT_FIELDS = (
        "object_code",
        "operation_code",
        "table_name",
        "primary_key",
        "columns",
    )

    def __init__(
        self,
        database: CommonDatabase,
    ) -> None:
        if database is None:
            raise ValueError("database is required.")

        self.database = database

    def execute(
        self,
        blueprint: Mapping[str, Any] | None = None,
        payload: Mapping[str, Any] | None = None,
        *,
        blueprint_code: str | None = None,
        manage_transaction: bool = True,
    ) -> dict[str, Any]:
        """
        Blueprint를 해석하여 Repository Object를 저장한다.

        Flow:
            Blueprint Validation
            → Payload Normalize
            → Required Field Validation
            → INSERT SQL Build
            → Repository Execute
            → Primary Key Resolve
            → Commit
        """
        if blueprint is None:
            if not blueprint_code:
                raise ValueError(
                    "blueprint or blueprint_code is required."
                )

            blueprint = self._load_blueprint(blueprint_code)

        if payload is None:
            raise ValueError("payload is required.")

        normalized_blueprint = self._normalize_blueprint(blueprint)
        normalized_payload = self._normalize_payload(payload)

        self._validate_blueprint(normalized_blueprint)
        self._validate_payload(
            normalized_blueprint,
            normalized_payload,
        )

        sql, params, inserted_columns = self._build_insert_sql(
            normalized_blueprint,
            normalized_payload,
        )

        try:
            if manage_transaction:
                self.database.begin()

            affected_rows = self.database.execute(sql, params)

            primary_key = str(
                normalized_blueprint["primary_key"]
            )

            primary_key_value = normalized_payload.get(primary_key)

            if primary_key_value is None:
                primary_key_value = self.database.last_insert_id()

            if manage_transaction:
                self.database.commit()

            return {
                "success": True,
                "status": "CREATED",
                "generator": self.__class__.__name__,
                "object_code": normalized_blueprint["object_code"],
                "operation_code": normalized_blueprint[
                    "operation_code"
                ],
                "primary_key": primary_key,
                "primary_key_value": primary_key_value,
                "affected_rows": affected_rows,
                "inserted_columns": inserted_columns,
            }

        except Exception:
            if manage_transaction:
                self.database.rollback()
            raise

    def _load_blueprint(
        self,
        blueprint_code: str,
    ) -> dict[str, Any]:
        """
        Repository에서 Blueprint를 조회한다.

        실제 조회 경로는 Repository Metadata 확인 후 연결한다.
        """
        normalized_code = str(blueprint_code).strip().upper()

        if not normalized_code:
            raise ValueError("blueprint_code must not be empty.")

        raise NotImplementedError(
            "Blueprint Repository mapping is not connected yet. "
            f"blueprint_code={normalized_code}"
        )

    def _normalize_blueprint(
        self,
        blueprint: Mapping[str, Any],
    ) -> dict[str, Any]:
        if not isinstance(blueprint, Mapping):
            raise TypeError("blueprint must be a mapping.")

        normalized = dict(blueprint)

        for field in (
            "object_code",
            "operation_code",
        ):
            value = normalized.get(field)

            if value is not None:
                normalized[field] = str(value).strip().upper()

        for field in (
            "table_name",
            "primary_key",
        ):
            value = normalized.get(field)

            if value is not None:
                normalized[field] = str(value).strip()

        columns = normalized.get("columns")

        if isinstance(columns, Sequence) and not isinstance(
            columns,
            (str, bytes),
        ):
            normalized["columns"] = [
                str(column).strip()
                for column in columns
            ]

        required_fields = normalized.get("required_fields", [])

        if isinstance(required_fields, Sequence) and not isinstance(
            required_fields,
            (str, bytes),
        ):
            normalized["required_fields"] = [
                str(field).strip()
                for field in required_fields
            ]

        return normalized

    @staticmethod
    def _normalize_payload(
        payload: Mapping[str, Any],
    ) -> dict[str, Any]:
        if not isinstance(payload, Mapping):
            raise TypeError("payload must be a mapping.")

        return dict(payload)

    def _validate_blueprint(
        self,
        blueprint: Mapping[str, Any],
    ) -> None:
        missing_fields = [
            field
            for field in self.REQUIRED_BLUEPRINT_FIELDS
            if not blueprint.get(field)
        ]

        if missing_fields:
            raise ValueError(
                "Missing required blueprint fields: "
                + ", ".join(missing_fields)
            )

        self._validate_sql_identifier(
            str(blueprint["table_name"]),
            field_name="table_name",
        )

        self._validate_sql_identifier(
            str(blueprint["primary_key"]),
            field_name="primary_key",
        )

        columns = blueprint["columns"]

        if not isinstance(columns, list) or not columns:
            raise ValueError(
                "blueprint.columns must be a non-empty list."
            )

        if len(columns) != len(set(columns)):
            raise ValueError(
                "blueprint.columns contains duplicate columns."
            )

        for column in columns:
            self._validate_sql_identifier(
                str(column),
                field_name="column",
            )

        primary_key = str(blueprint["primary_key"])

        if primary_key not in columns:
            # AUTO_INCREMENT PK는 INSERT Column에서 제외할 수 있다.
            auto_increment_yn = str(
                blueprint.get("auto_increment_yn", "N")
            ).upper()

            if auto_increment_yn != "Y":
                raise ValueError(
                    "primary_key must exist in columns unless "
                    "auto_increment_yn is Y."
                )

        required_fields = blueprint.get("required_fields", [])

        unknown_required_fields = [
            field
            for field in required_fields
            if field not in columns
        ]

        if unknown_required_fields:
            raise ValueError(
                "required_fields not present in columns: "
                + ", ".join(unknown_required_fields)
            )

    @staticmethod
    def _validate_payload(
        blueprint: Mapping[str, Any],
        payload: Mapping[str, Any],
    ) -> None:
        allowed_columns = set(blueprint["columns"])

        unknown_fields = sorted(
            set(payload.keys()) - allowed_columns
        )

        if unknown_fields:
            raise ValueError(
                "Payload contains fields not allowed by blueprint: "
                + ", ".join(unknown_fields)
            )

        missing_fields = [
            field
            for field in blueprint.get("required_fields", [])
            if payload.get(field) is None
        ]

        if missing_fields:
            raise ValueError(
                "Missing required payload fields: "
                + ", ".join(missing_fields)
            )

        if not payload:
            raise ValueError("payload must not be empty.")

    def _build_insert_sql(
        self,
        blueprint: Mapping[str, Any],
        payload: Mapping[str, Any],
    ) -> tuple[str, tuple[Any, ...], list[str]]:
        ordered_columns = [
            column
            for column in blueprint["columns"]
            if column in payload
        ]

        if not ordered_columns:
            raise ValueError(
                "No payload fields match blueprint columns."
            )

        table_name = str(blueprint["table_name"])

        quoted_columns = ",\n                ".join(
            f"`{column}`"
            for column in ordered_columns
        )

        placeholders = ", ".join(
            "%s"
            for _ in ordered_columns
        )

        sql = f"""
            INSERT INTO `{table_name}`
            (
                {quoted_columns}
            )
            VALUES
            (
                {placeholders}
            )
        """

        params = tuple(
            payload[column]
            for column in ordered_columns
        )

        return sql, params, ordered_columns

    def _validate_sql_identifier(
        self,
        identifier: str,
        *,
        field_name: str,
    ) -> None:
        if not self._SAFE_IDENTIFIER_PATTERN.fullmatch(identifier):
            raise ValueError(
                f"Invalid SQL identifier for {field_name}: "
                f"{identifier!r}"
            )

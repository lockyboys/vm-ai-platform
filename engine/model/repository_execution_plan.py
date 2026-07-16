"""
Repository Execution Plan

Repository의 Object, Relationship, Metadata를 해석한 실행 시점 설계도이다.

Principles:
    - Repository First
    - Metadata Driven
    - Single Source of Truth
    - No Hardcoding

Boundary:
    - Repository에 별도 Blueprint로 저장하지 않는다.
    - Runtime 메모리에서만 생성한다.
    - 물리 Database 연결 정보는 포함하지 않는다.
    - Database Role만 관리한다.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Mapping, Sequence


_SAFE_IDENTIFIER_PATTERN = re.compile(
    r"^[A-Za-z_][A-Za-z0-9_]*$"
)


@dataclass(frozen=True, slots=True)
class RepositoryExecutionPlan:
    """Repository Object 저장을 위한 불변 실행 계획."""

    object_id: str
    object_code: str
    operation_code: str

    database_role: str
    table_name: str
    primary_key: str

    columns: tuple[str, ...]
    required_fields: tuple[str, ...] = ()

    identifier_target_code: str | None = None
    auto_increment_yn: str = "N"

    validation_rules: tuple[Mapping[str, Any], ...] = ()
    relationships: tuple[Mapping[str, Any], ...] = ()

    transaction_policy: Mapping[str, Any] = field(
        default_factory=dict
    )
    history_policy: Mapping[str, Any] = field(
        default_factory=dict
    )

    def __post_init__(self) -> None:
        """실행 계획의 구조적 무결성을 검증한다."""
        self._validate_required_text(
            self.object_id,
            "object_id",
        )
        self._validate_required_text(
            self.object_code,
            "object_code",
        )
        self._validate_required_text(
            self.operation_code,
            "operation_code",
        )
        self._validate_required_text(
            self.database_role,
            "database_role",
        )

        self._validate_sql_identifier(
            self.table_name,
            "table_name",
        )
        self._validate_sql_identifier(
            self.primary_key,
            "primary_key",
        )

        if not self.columns:
            raise ValueError(
                "columns must contain at least one column."
            )

        if len(self.columns) != len(set(self.columns)):
            raise ValueError(
                "columns contains duplicate values."
            )

        for column in self.columns:
            self._validate_sql_identifier(
                column,
                "column",
            )

        unknown_required_fields = sorted(
            set(self.required_fields) - set(self.columns)
        )

        if unknown_required_fields:
            raise ValueError(
                "required_fields not present in columns: "
                + ", ".join(unknown_required_fields)
            )

        normalized_auto_increment = (
            str(self.auto_increment_yn).strip().upper()
        )

        if normalized_auto_increment not in {"Y", "N"}:
            raise ValueError(
                "auto_increment_yn must be Y or N."
            )

        if (
            normalized_auto_increment == "N"
            and self.primary_key not in self.columns
        ):
            raise ValueError(
                "primary_key must exist in columns when "
                "auto_increment_yn is N."
            )

    def to_generator_blueprint(self) -> dict[str, Any]:
        """
        기존 RepositoryObjectGenerator가 해석할 수 있는
        Blueprint 호환 Dictionary를 반환한다.

        이 메서드는 기존 Generator를 보존하면서
        Execution Plan을 연결하기 위한 Adapter 역할을 수행한다.
        """
        return {
            "object_code": self.object_code,
            "operation_code": self.operation_code,
            "database_role": self.database_role,
            "table_name": self.table_name,
            "primary_key": self.primary_key,
            "columns": list(self.columns),
            "required_fields": list(self.required_fields),
            "identifier_target_code": (
                self.identifier_target_code
            ),
            "auto_increment_yn": self.auto_increment_yn,
            "validation_rules": [
                dict(rule)
                for rule in self.validation_rules
            ],
            "relationships": [
                dict(relationship)
                for relationship in self.relationships
            ],
            "transaction_policy": dict(
                self.transaction_policy
            ),
            "history_policy": dict(
                self.history_policy
            ),
        }

    @classmethod
    def from_repository(
        cls,
        *,
        object_metadata: Mapping[str, Any],
        operation_code: str,
        repository_metadata: Mapping[str, Any],
        relationships: Sequence[Mapping[str, Any]] = (),
        validation_rules: Sequence[Mapping[str, Any]] = (),
    ) -> "RepositoryExecutionPlan":
        """
        Repository 조회 결과를 실행 계획으로 조립한다.

        Object Metadata:
            object_id
            object_code
            identifier_target_code

        Repository Metadata:
            database_role
            table_name
            primary_key
            columns
            required_fields
            auto_increment_yn
            transaction_policy
            history_policy
        """
        if not isinstance(object_metadata, Mapping):
            raise TypeError(
                "object_metadata must be a mapping."
            )

        if not isinstance(repository_metadata, Mapping):
            raise TypeError(
                "repository_metadata must be a mapping."
            )

        return cls(
            object_id=str(
                object_metadata["object_id"]
            ).strip(),
            object_code=str(
                object_metadata["object_code"]
            ).strip().upper(),
            operation_code=str(
                operation_code
            ).strip().upper(),
            database_role=str(
                repository_metadata["database_role"]
            ).strip().upper(),
            table_name=str(
                repository_metadata["table_name"]
            ).strip(),
            primary_key=str(
                repository_metadata["primary_key"]
            ).strip(),
            columns=tuple(
                str(column).strip()
                for column in repository_metadata["columns"]
            ),
            required_fields=tuple(
                str(field_name).strip()
                for field_name in repository_metadata.get(
                    "required_fields",
                    (),
                )
            ),
            identifier_target_code=(
                str(
                    object_metadata[
                        "identifier_target_code"
                    ]
                ).strip().upper()
                if object_metadata.get(
                    "identifier_target_code"
                )
                else None
            ),
            auto_increment_yn=str(
                repository_metadata.get(
                    "auto_increment_yn",
                    "N",
                )
            ).strip().upper(),
            validation_rules=tuple(
                dict(rule)
                for rule in validation_rules
            ),
            relationships=tuple(
                dict(relationship)
                for relationship in relationships
            ),
            transaction_policy=dict(
                repository_metadata.get(
                    "transaction_policy",
                    {},
                )
            ),
            history_policy=dict(
                repository_metadata.get(
                    "history_policy",
                    {},
                )
            ),
        )

    @staticmethod
    def _validate_required_text(
        value: str,
        field_name: str,
    ) -> None:
        if not str(value).strip():
            raise ValueError(
                f"{field_name} must not be empty."
            )

    @staticmethod
    def _validate_sql_identifier(
        identifier: str,
        field_name: str,
    ) -> None:
        if not _SAFE_IDENTIFIER_PATTERN.fullmatch(identifier):
            raise ValueError(
                f"Invalid SQL identifier for {field_name}: "
                f"{identifier!r}"
            )

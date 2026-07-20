"""
SPS Object Definition Engine

Purpose:
    Object Definition Request를 검증하고 다음 Repository를 생성한다.

    - sp_object
    - sp_identifier_sequence

Principles:
    - Repository First
    - Object First
    - Generator First
    - Metadata Driven
    - Single Source of Truth
    - No Hardcoding
"""

from __future__ import annotations

import re
from datetime import datetime
from typing import Any

from common.database import CommonDatabase
from engine.identifier_engine import IdentifierEngine
from engine.generator.object_definition_generator import ObjectDefinitionGenerator


class ObjectDefinitionIdentifierWorkflow:
    """Object Definition 생성 흐름과 Transaction을 통제한다."""

    REQUIRED_FIELDS = (
        "object_code",
        "object_name",
        "business_code",
        "domain_code",
        "object_type_code",
        "object_level",
        "identifier_target_code",
        "sequence_scope_code",
        "sequence_length",
    )

    ALLOWED_SEQUENCE_SCOPES = {
        "NO",
        "NONE",
        "YEARLY",
        "MONTHLY",
        "DAILY",
    }

    def __init__(
        self,
        database: CommonDatabase | None = None,
    ) -> None:
        self.database = database or CommonDatabase(
            database_role="STORY_PLATFORM"
        )
        self.identifier_engine = IdentifierEngine(self.database)
        self.generator = ObjectDefinitionGenerator(self.database)

    def create(
        self,
        request: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Object Definition을 생성한다.

        Flow:
            Request Normalize
            → Repository Validation
            → Blueprint Load
            → Sequence Metadata Initialize
            → Identifier Allocate
            → sp_object Save
            → Commit
        """
        normalized = self._normalize_request(request)
        self._validate_required_fields(normalized)
        self._validate_repository_metadata(normalized)

        existing = self._find_existing_object(
            normalized["object_code"]
        )

        if existing:
            return {
                "success": False,
                "status": "ALREADY_EXISTS",
                "message": (
                    "Object already exists. "
                    f"object_code={normalized['object_code']}"
                ),
                "object": existing,
            }

        blueprint = self.identifier_engine.load_identifier_blueprint(
            int(normalized["object_level"])
        )

        now = datetime.now()

        sequence_scope_code = (
            normalized.get("sequence_scope_code")
            or blueprint.get("sequence_scope_code")
        )

        sequence_length = int(
            normalized.get("sequence_length")
            or blueprint.get("sequence_length")
            or 5
        )

        sequence_date = self.identifier_engine.resolve_sequence_date(
            sequence_scope_code=sequence_scope_code,
            now=now,
        )

        lock_name = self._build_lock_name(
            normalized=normalized,
            sequence_date=sequence_date,
        )

        lock_acquired = False

        try:
            lock_acquired = self._acquire_lock(lock_name)

            if not lock_acquired:
                raise RuntimeError(
                    "Object Definition lock acquisition failed. "
                    f"lock_name={lock_name}"
                )

            self.database.begin()

            # Lock 획득 후 중복을 다시 확인한다.
            existing = self._find_existing_object(
                normalized["object_code"]
            )

            if existing:
                self.database.rollback()

                return {
                    "success": False,
                    "status": "ALREADY_EXISTS",
                    "message": (
                        "Object already exists. "
                        f"object_code={normalized['object_code']}"
                    ),
                    "object": existing,
                }

            sequence_row = self._ensure_sequence_metadata(
                normalized=normalized,
                blueprint=blueprint,
                sequence_date=sequence_date,
                sequence_length=sequence_length,
                now=now,
            )

            sequence_no = self._allocate_sequence(
                identifier_sequence_id=(
                    sequence_row["identifier_sequence_id"]
                ),
                sequence_length=sequence_length,
            )

            object_id = self.identifier_engine.render_identifier(
                object_metadata=normalized,
                blueprint=blueprint,
                sequence_no=sequence_no,
                sequence_length=sequence_length,
                now=now,
            )

            self._validate_generated_identifier(
                identifier=object_id,
                blueprint=blueprint,
            )

            self.generator.generate(
                object_id=object_id,
                request=normalized,
            )

            self.database.commit()

            saved_object = self._find_existing_object(
                normalized["object_code"]
            )

            return {
                "success": True,
                "status": "CREATED",
                "message": "Object Definition created successfully.",
                "object_id": object_id,
                "object_code": normalized["object_code"],
                "identifier_target_code": (
                    normalized["identifier_target_code"]
                ),
                "object_level": normalized["object_level"],
                "sequence_date": sequence_date,
                "sequence_no": sequence_no,
                "blueprint_code": blueprint["blueprint_code"],
                "object": saved_object,
            }

        except Exception:
            self.database.rollback()
            raise

        finally:
            if lock_acquired:
                self._release_lock(lock_name)

    def _normalize_request(
        self,
        request: dict[str, Any],
    ) -> dict[str, Any]:
        """입력 Request를 Repository 저장 형식으로 정규화한다."""
        if not isinstance(request, dict):
            raise TypeError("request must be a dictionary.")

        normalized = dict(request)

        uppercase_fields = (
            "object_code",
            "business_code",
            "domain_code",
            "object_type_code",
            "identifier_target_code",
            "sequence_scope_code",
            "status_code",
            "active_yn",
        )

        for field in uppercase_fields:
            value = normalized.get(field)

            if value is not None:
                normalized[field] = str(value).strip().upper()

        normalized["object_name"] = str(
            normalized.get("object_name") or ""
        ).strip()

        normalized["object_description"] = (
            str(normalized.get("object_description")).strip()
            if normalized.get("object_description") is not None
            else None
        )

        normalized["object_level"] = int(
            normalized.get("object_level")
        )

        normalized["sequence_length"] = int(
            normalized.get("sequence_length")
        )

        normalized.setdefault("status_code", "ACTIVE")
        normalized.setdefault("active_yn", "Y")
        normalized.setdefault("version_no", "v1.0")
        normalized.setdefault("sort_no", 0)
        normalized.setdefault("created_by", "OBJECT_DEFINITION_GENERATOR")
        normalized.setdefault("updated_by", "OBJECT_DEFINITION_GENERATOR")
        normalized.setdefault("program_id", "ObjectDefinitionGenerator")
        normalized.setdefault("client_ip", "127.0.0.1")
        normalized.setdefault("parent_object_id", None)
        normalized.setdefault("lifecycle_id", None)
        normalized.setdefault("target_identifier_field", None)
        normalized.setdefault("change_reason", "Object Definition Runtime 생성")

        return normalized

    def _validate_required_fields(
        self,
        request: dict[str, Any],
    ) -> None:
        """필수 입력값을 검증한다."""
        missing = [
            field
            for field in self.REQUIRED_FIELDS
            if request.get(field) in (None, "")
        ]

        if missing:
            raise ValueError(
                "Required Object Definition fields are missing. "
                f"missing_fields={missing}"
            )

        if not re.fullmatch(
            r"[A-Z][A-Z0-9_]*",
            request["object_code"],
        ):
            raise ValueError(
                "Invalid object_code. "
                "Only uppercase letters, digits, and underscore are allowed."
            )

        if not 0 <= int(request["object_level"]) <= 4:
            raise ValueError(
                "object_level must be between 0 and 4."
            )

        if not 1 <= int(request["sequence_length"]) <= 20:
            raise ValueError(
                "sequence_length must be between 1 and 20."
            )

        if (
            request["sequence_scope_code"]
            not in self.ALLOWED_SEQUENCE_SCOPES
        ):
            raise ValueError(
                "Unsupported sequence_scope_code. "
                f"value={request['sequence_scope_code']}"
            )

        description = request.get("object_description")

        if description and len(description) > 2000:
            raise ValueError(
                "object_description exceeds VARCHAR(2000). "
                f"length={len(description)}"
            )

    def _validate_repository_metadata(
        self,
        request: dict[str, Any],
    ) -> None:
        """Business, Domain, Object Type, Identifier Target를 검증한다."""
        business = self.database.fetch_one(
            """
            SELECT
                business_code,
                business_name
            FROM sp_business
            WHERE business_code = %s
              AND active_yn = 'Y'
              AND deleted_dt IS NULL
            LIMIT 1
            """,
            (request["business_code"],),
        )

        if not business:
            raise ValueError(
                "Business metadata not found. "
                f"business_code={request['business_code']}"
            )

        domain = self.database.fetch_one(
            """
            SELECT
                domain_code,
                business_code,
                domain_name
            FROM sp_domain
            WHERE domain_code = %s
              AND business_code = %s
              AND active_yn = 'Y'
              AND deleted_dt IS NULL
            LIMIT 1
            """,
            (
                request["domain_code"],
                request["business_code"],
            ),
        )

        if not domain:
            raise ValueError(
                "Domain metadata not found or business mismatch. "
                f"business_code={request['business_code']}, "
                f"domain_code={request['domain_code']}"
            )

        object_type = self.database.fetch_one(
            """
            SELECT
                group_code,
                code,
                code_name
            FROM te_common.cm_common_code
            WHERE group_code IN
            (
                'OBJECT_TYPE',
                'CM_OBJECT_TYPE'
            )
              AND code = %s
              AND status_code = 'ACTIVE'
              AND deleted_dt IS NULL
            ORDER BY
                CASE
                    WHEN group_code = 'OBJECT_TYPE' THEN 1
                    ELSE 2
                END
            LIMIT 1
            """,
            (request["object_type_code"],),
        )

        if not object_type:
            raise ValueError(
                "Object Type metadata not found. "
                f"object_type_code={request['object_type_code']}"
            )

        identifier_target = self.database.fetch_one(
            """
            SELECT
                code,
                code_name
            FROM te_common.cm_common_code
            WHERE group_code = 'SPS_IDENTIFIER_TARGET'
              AND code = %s
              AND status_code = 'ACTIVE'
              AND deleted_dt IS NULL
            LIMIT 1
            """,
            (request["identifier_target_code"],),
        )

        if not identifier_target:
            raise ValueError(
                "Identifier Target metadata not found. "
                f"identifier_target_code="
                f"{request['identifier_target_code']}"
            )

    def _find_existing_object(
        self,
        object_code: str,
    ) -> dict[str, Any] | None:
        """Object Code로 기존 Object를 조회한다."""
        return self.database.fetch_one(
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
                sequence_length,
                status_code,
                active_yn,
                created_dt
            FROM sp_object
            WHERE object_code = %s
              AND deleted_dt IS NULL
            LIMIT 1
            """,
            (object_code,),
        )

    @staticmethod
    def _build_lock_name(
        normalized: dict[str, Any],
        sequence_date: str,
    ) -> str:
        """MariaDB Named Lock 이름을 생성한다."""
        return (
            "SPS_OBJECT_DEFINITION:"
            f"{normalized['business_code']}:"
            f"{normalized['domain_code']}:"
            f"{normalized['object_code']}:"
            f"{sequence_date}"
        )[:64]

    def _acquire_lock(
        self,
        lock_name: str,
    ) -> bool:
        """동일 Object 동시 생성 방지 Lock을 획득한다."""
        row = self.database.fetch_one(
            "SELECT GET_LOCK(%s, 10) AS acquired",
            (lock_name,),
        )

        return bool(row and int(row["acquired"]) == 1)

    def _release_lock(
        self,
        lock_name: str,
    ) -> None:
        """Named Lock을 해제한다."""
        self.database.fetch_one(
            "SELECT RELEASE_LOCK(%s) AS released",
            (lock_name,),
        )

    def _ensure_sequence_metadata(
        self,
        normalized: dict[str, Any],
        blueprint: dict[str, Any],
        sequence_date: str,
        sequence_length: int,
        now: datetime,
    ) -> dict[str, Any]:
        """
        Identifier Sequence Metadata를 준비한다.

        Sequence Metadata ID는 동일 Blueprint를 사용하되
        Sequence 00000을 Repository 기준 행으로 사용한다.
        """
        existing = self.database.fetch_one(
            """
            SELECT
                identifier_sequence_id,
                identifier_target_code,
                identifier_prefix,
                sequence_dt,
                current_sequence_no,
                sequence_length
            FROM sp_identifier_sequence
            WHERE identifier_target_code = %s
              AND identifier_prefix = %s
              AND sequence_dt = %s
              AND status_code = 'ACTIVE'
              AND deleted_dt IS NULL
            FOR UPDATE
            """,
            (
                normalized["identifier_target_code"],
                normalized["object_code"],
                sequence_date,
            ),
        )

        if existing:
            return existing

        identifier_sequence_id = (
            self.identifier_engine.render_identifier(
                object_metadata=normalized,
                blueprint=blueprint,
                sequence_no=0,
                sequence_length=sequence_length,
                now=now,
            )
        )

        affected = self.database.execute(
            """
            INSERT INTO sp_identifier_sequence
            (
                identifier_sequence_id,
                identifier_target_code,
                identifier_prefix,
                sequence_dt,
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
                normalized["identifier_target_code"],
                normalized["object_code"],
                sequence_date,
                sequence_length,
                normalized["created_by"],
                normalized["updated_by"],
                normalized["client_ip"],
                normalized["program_id"],
                normalized["object_code"],
                normalized["object_level"],
                blueprint["blueprint_code"],
                normalized["sequence_scope_code"],
            ),
        )

        if affected != 1:
            raise RuntimeError(
                "Identifier Sequence metadata creation failed. "
                f"affected_rows={affected}"
            )

        return {
            "identifier_sequence_id": identifier_sequence_id,
            "identifier_target_code": (
                normalized["identifier_target_code"]
            ),
            "identifier_prefix": normalized["object_code"],
            "sequence_date": sequence_date,
            "current_sequence_no": 0,
            "sequence_length": sequence_length,
        }

    def _allocate_sequence(
        self,
        identifier_sequence_id: str,
        sequence_length: int,
    ) -> int:
        """현재 트랜잭션 안에서 다음 Sequence를 할당한다."""
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
                "Identifier Sequence metadata not found. "
                f"identifier_sequence_id={identifier_sequence_id}"
            )

        next_sequence_no = int(
            row["current_sequence_no"]
        ) + 1

        maximum = (10 ** sequence_length) - 1

        if next_sequence_no > maximum:
            raise OverflowError(
                "Identifier Sequence overflow. "
                f"sequence_length={sequence_length}"
            )

        affected = self.database.execute(
            """
            UPDATE sp_identifier_sequence
            SET
                current_sequence_no = %s,
                sequence_length = %s,
                updated_dt = CURRENT_TIMESTAMP,
                updated_by = 'OBJECT_DEFINITION_GENERATOR',
                program_id = 'ObjectDefinitionGenerator'
            WHERE identifier_sequence_id = %s
            """,
            (
                next_sequence_no,
                sequence_length,
                identifier_sequence_id,
            ),
        )

        if affected != 1:
            raise RuntimeError(
                "Identifier Sequence allocation failed. "
                f"affected_rows={affected}"
            )

        return next_sequence_no

    @staticmethod
    def _validate_generated_identifier(
        identifier: str,
        blueprint: dict[str, Any],
    ) -> None:
        """생성된 Identifier에 미해결 Token이 없는지 확인한다."""
        if not identifier:
            raise ValueError("Generated identifier is empty.")

        unresolved = re.findall(
            r"\{[A-Z0-9_]+\}",
            identifier,
        )

        if unresolved:
            raise ValueError(
                "Generated identifier contains unresolved tokens. "
                f"tokens={unresolved}, "
                f"blueprint={blueprint['blueprint_code']}"
            )

        if len(identifier) > 99:
            raise ValueError(
                "Generated object_id exceeds VARCHAR(99). "
                f"length={len(identifier)}, "
                f"identifier={identifier}"
            )

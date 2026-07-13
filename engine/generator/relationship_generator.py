"""
SPS Relationship Generator

Purpose:
    Object 간 Relationship을 Repository Metadata 기반으로 검증하고
    Identifier Engine을 통해 Relationship ID를 발급한 뒤
    sp_relationship에 저장한다.

Principles:
    - Repository First
    - Object First
    - Generator First
    - Metadata Driven
    - Single Source of Truth
    - No Hardcoding
"""

from __future__ import annotations

import json
from datetime import datetime
import os
import re
from typing import Any

from common.database import CommonDatabase
from engine.identifier_engine import IdentifierEngine


class RelationshipGenerator:
    """SPS 범용 Object Relationship Generator."""

    OBJECT_CODE = "RELATIONSHIP"
    RELATIONSHIP_SCOPE_CODE = "OBJECT"

    REQUIRED_FIELDS = (
        "source_object_id",
        "source_object_type_code",
        "target_object_id",
        "target_object_type_code",
        "relationship_code",
        "relationship_name",
        "relationship_type_code",
    )

    def __init__(
        self,
        database: CommonDatabase | None = None,
    ) -> None:
        self.database = database or CommonDatabase(
            database_role="STORY_PLATFORM"
        )
        self.identifier_engine = IdentifierEngine(self.database)

    def create_batch(
        self,
        requests: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """
        Relationship 여러 건을 한 트랜잭션으로 생성한다.

        Flow:
            Request 정규화
            → Predicate 검증
            → Object Type 검증
            → Source/Target 존재 검증
            → Relationship ID 발급
            → INSERT
            → COMMIT
        """
        if not isinstance(requests, list) or not requests:
            raise ValueError(
                "Relationship requests must be a non-empty list."
            )

        normalized_requests = [
            self._normalize_request(request)
            for request in requests
        ]

        self._validate_duplicate_request_codes(
            normalized_requests
        )

        existing_rows = self._find_existing_relationships(
            normalized_requests
        )

        if existing_rows:
            return {
                "success": False,
                "status": "ALREADY_EXISTS",
                "message": (
                    "One or more relationships already exist."
                ),
                "existing_relationships": existing_rows,
            }

        for request in normalized_requests:
            self._validate_request(request)
            self._validate_predicate(
                request["relationship_type_code"]
            )
            self._validate_object_type(
                request["source_object_type_code"]
            )
            self._validate_object_type(
                request["target_object_type_code"]
            )
            self._validate_object_exists(
                object_id=request["source_object_id"],
                object_type_code=(
                    request["source_object_type_code"]
                ),
            )
            self._validate_object_exists(
                object_id=request["target_object_id"],
                object_type_code=(
                    request["target_object_type_code"]
                ),
            )

        generated_rows: list[dict[str, Any]] = []
        batch_dt = datetime.now()

        try:
            self.database.begin()

            # Transaction 시작 후 동시 등록 여부를 다시 확인한다.
            existing_rows = self._find_existing_relationships(
                normalized_requests
            )

            if existing_rows:
                self.database.rollback()

                return {
                    "success": False,
                    "status": "ALREADY_EXISTS",
                    "message": (
                        "Relationships were created by another process."
                    ),
                    "existing_relationships": existing_rows,
                }

            # Relationship Identifier 발급과 INSERT를
            # 동일한 Database Transaction 안에서 수행한다.
            for request in normalized_requests:
                relationship_id = (
                    self.identifier_engine.generate_for_level(
                        object_code=self.OBJECT_CODE,
                        object_level=4,
                        now=batch_dt,
                        manage_transaction=False,
                    )
                )

                generated_row = {
                    **request,
                    "relationship_id": relationship_id,
                }

                self._insert_relationship(generated_row)
                generated_rows.append(generated_row)

                if (
                    os.getenv(
                        "SPS_FORCE_RELATIONSHIP_ROLLBACK_TEST",
                        "N",
                    ).strip().upper()
                    == "Y"
                ):
                    raise RuntimeError(
                        "Forced Relationship transaction "
                        "rollback test."
                    )

            self.database.commit()

        except Exception:
            self.database.rollback()
            raise

        saved_rows = self._find_relationships_by_codes(
            [
                row["relationship_code"]
                for row in generated_rows
            ]
        )

        return {
            "success": True,
            "status": "CREATED",
            "message": (
                f"{len(saved_rows)} relationships created successfully."
            ),
            "relationship_count": len(saved_rows),
            "relationships": saved_rows,
        }

    def _normalize_request(
        self,
        request: dict[str, Any],
    ) -> dict[str, Any]:
        """Relationship Request를 정규화한다."""
        if not isinstance(request, dict):
            raise TypeError(
                "Each relationship request must be a dictionary."
            )

        normalized = dict(request)

        uppercase_fields = (
            "source_object_type_code",
            "target_object_type_code",
            "relationship_code",
            "relationship_type_code",
            "identifying_yn",
            "delete_rule_code",
            "update_rule_code",
            "enabled_yn",
        )

        for field in uppercase_fields:
            value = normalized.get(field)

            if value is not None:
                normalized[field] = str(value).strip().upper()

        text_fields = (
            "source_object_id",
            "target_object_id",
            "relationship_name",
            "relationship_description",
        )

        for field in text_fields:
            value = normalized.get(field)

            if value is not None:
                normalized[field] = str(value).strip()

        normalized.setdefault(
            "relationship_scope_code",
            self.RELATIONSHIP_SCOPE_CODE,
        )
        normalized.setdefault("source_min_cardinality", 1)
        normalized.setdefault("source_max_cardinality", 1)
        normalized.setdefault("target_min_cardinality", 1)
        normalized.setdefault("target_max_cardinality", 1)
        normalized.setdefault("identifying_yn", "N")
        normalized.setdefault("delete_rule_code", "RESTRICT")
        normalized.setdefault("update_rule_code", "CASCADE")
        normalized.setdefault("enabled_yn", "Y")
        normalized.setdefault("sort_no", 0)
        normalized.setdefault("created_by", "RELATIONSHIP_GENERATOR")
        normalized.setdefault("updated_by", "RELATIONSHIP_GENERATOR")
        normalized.setdefault("client_ip", "127.0.0.1")
        normalized.setdefault(
            "program_id",
            "RelationshipGenerator",
        )

        normalized["source_min_cardinality"] = int(
            normalized["source_min_cardinality"]
        )
        normalized["source_max_cardinality"] = int(
            normalized["source_max_cardinality"]
        )
        normalized["target_min_cardinality"] = int(
            normalized["target_min_cardinality"]
        )
        normalized["target_max_cardinality"] = int(
            normalized["target_max_cardinality"]
        )
        normalized["sort_no"] = int(normalized["sort_no"])

        return normalized

    def _validate_request(
        self,
        request: dict[str, Any],
    ) -> None:
        """필수값과 문자열 규격을 검증한다."""
        missing = [
            field
            for field in self.REQUIRED_FIELDS
            if request.get(field) in (None, "")
        ]

        if missing:
            raise ValueError(
                "Required Relationship fields are missing. "
                f"missing_fields={missing}"
            )

        if request["relationship_scope_code"] != "OBJECT":
            raise ValueError(
                "RelationshipGenerator supports OBJECT scope only."
            )

        if not re.fullmatch(
            r"[A-Z][A-Z0-9_]*",
            request["relationship_code"],
        ):
            raise ValueError(
                "Invalid relationship_code. "
                f"value={request['relationship_code']}"
            )

        if len(request["relationship_code"]) > 100:
            raise ValueError(
                "relationship_code exceeds VARCHAR(100)."
            )

        if len(request["relationship_name"]) > 150:
            raise ValueError(
                "relationship_name exceeds VARCHAR(150)."
            )

        description = request.get(
            "relationship_description"
        )

        if description and len(description) > 2000:
            raise ValueError(
                "relationship_description exceeds VARCHAR(2000)."
            )

    @staticmethod
    def _validate_duplicate_request_codes(
        requests: list[dict[str, Any]],
    ) -> None:
        """동일 Batch 안의 Relationship Code 중복을 차단한다."""
        codes = [
            request["relationship_code"]
            for request in requests
        ]

        duplicate_codes = sorted(
            {
                code
                for code in codes
                if codes.count(code) > 1
            }
        )

        if duplicate_codes:
            raise ValueError(
                "Duplicate relationship_code in request. "
                f"codes={duplicate_codes}"
            )

    def _validate_predicate(
        self,
        predicate_code: str,
    ) -> None:
        """Relationship Predicate 공통코드를 검증한다."""
        row = self.database.fetch_one(
            """
            SELECT
                code,
                code_name
            FROM te_common.cm_common_code
            WHERE group_code = 'SPS_RELATIONSHIP_PREDICATE'
              AND code = %s
              AND status_code = 'ACTIVE'
              AND deleted_dt IS NULL
            LIMIT 1
            """,
            (predicate_code,),
        )

        if not row:
            raise ValueError(
                "Relationship Predicate metadata not found. "
                f"predicate_code={predicate_code}"
            )

    def _validate_object_type(
        self,
        object_type_code: str,
    ) -> None:
        """Relationship Object Type 공통코드를 검증한다."""
        row = self.database.fetch_one(
            """
            SELECT
                code,
                code_name
            FROM te_common.cm_common_code
            WHERE group_code = 'SPS_RELATIONSHIP_OBJECT_TYPE'
              AND code = %s
              AND status_code = 'ACTIVE'
              AND deleted_dt IS NULL
            LIMIT 1
            """,
            (object_type_code,),
        )

        if not row:
            raise ValueError(
                "Relationship Object Type metadata not found. "
                f"object_type_code={object_type_code}"
            )

    def _load_object_type_metadata(
        self,
        object_type_code: str,
    ) -> dict[str, Any]:
        """Object Type의 Repository 위치 Metadata를 읽는다."""
        row = self.database.fetch_one(
            """
            SELECT
                code,
                common_code_json
            FROM te_common.cm_common_code
            WHERE group_code = 'SPS_RELATIONSHIP_OBJECT_TYPE'
              AND code = %s
              AND status_code = 'ACTIVE'
              AND deleted_dt IS NULL
            LIMIT 1
            """,
            (object_type_code,),
        )

        if not row:
            raise ValueError(
                "Object Type metadata not found. "
                f"object_type_code={object_type_code}"
            )

        raw_json = row.get("common_code_json")

        if isinstance(raw_json, dict):
            metadata = raw_json
        elif isinstance(raw_json, str) and raw_json.strip():
            metadata = json.loads(raw_json)
        else:
            metadata = {}

        required = (
            "database_role",
            "table_name",
            "identifier_column",
        )

        missing = [
            field
            for field in required
            if not metadata.get(field)
        ]

        if missing:
            raise ValueError(
                "Object Type Repository metadata is incomplete. "
                f"object_type_code={object_type_code}, "
                f"missing_fields={missing}"
            )

        return metadata

    def _validate_object_exists(
        self,
        object_id: str,
        object_type_code: str,
    ) -> None:
        """공통코드 JSON이 지정한 Repository에서 Object를 조회한다."""
        metadata = self._load_object_type_metadata(
            object_type_code
        )

        database_role = str(
            metadata["database_role"]
        ).upper()

        database_map = {
            "COMMON": "te_common",
            "STORY_PLATFORM": "te_story_platform",
        }

        database_name = database_map.get(database_role)

        if not database_name:
            raise ValueError(
                "Unsupported Repository database role. "
                f"database_role={database_role}"
            )

        table_name = metadata["table_name"]
        identifier_column = metadata["identifier_column"]

        identifier_pattern = re.compile(
            r"^[a-z][a-z0-9_]*$"
        )

        for identifier in (
            database_name,
            table_name,
            identifier_column,
        ):
            if not identifier_pattern.fullmatch(identifier):
                raise ValueError(
                    "Unsafe Repository identifier metadata. "
                    f"identifier={identifier}"
                )

        sql = (
            f"SELECT {identifier_column} "
            f"FROM {database_name}.{table_name} "
            f"WHERE {identifier_column} = %s "
            f"LIMIT 1"
        )

        row = self.database.fetch_one(
            sql,
            (object_id,),
        )

        if not row:
            raise ValueError(
                "Relationship Source/Target Object not found. "
                f"object_type_code={object_type_code}, "
                f"object_id={object_id}, "
                f"repository={database_name}.{table_name}"
            )

    def _find_existing_relationships(
        self,
        requests: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """요청 Relationship Code와 일치하는 기존 행을 조회한다."""
        codes = [
            request["relationship_code"]
            for request in requests
        ]

        return self._find_relationships_by_codes(codes)

    def _find_relationships_by_codes(
        self,
        relationship_codes: list[str],
    ) -> list[dict[str, Any]]:
        """Relationship Code 목록으로 저장 결과를 조회한다."""
        if not relationship_codes:
            return []

        placeholders = ", ".join(
            ["%s"] * len(relationship_codes)
        )

        sql = f"""
            SELECT
                relationship_id,
                relationship_scope_code,
                source_object_id,
                source_object_type_code,
                relationship_type_code,
                target_object_id,
                target_object_type_code,
                relationship_code,
                relationship_name,
                relationship_description,
                enabled_yn,
                sort_no,
                created_dt
            FROM sp_relationship
            WHERE relationship_code IN ({placeholders})
              AND deleted_dt IS NULL
            ORDER BY sort_no, relationship_code
        """

        rows = self.database.fetch_all(
            sql,
            tuple(relationship_codes),
        )

        return rows or []

    def _insert_relationship(
        self,
        row: dict[str, Any],
    ) -> None:
        """sp_relationship에 Relationship 한 건을 저장한다."""
        affected = self.database.execute(
            """
            INSERT INTO sp_relationship
            (
                relationship_id,
                relationship_scope_code,
                erd_id,
                source_entity_id,
                source_object_id,
                source_object_type_code,
                target_entity_id,
                target_object_id,
                target_object_type_code,
                relationship_code,
                relationship_name,
                relationship_description,
                relationship_type_code,
                source_min_cardinality,
                source_max_cardinality,
                target_min_cardinality,
                target_max_cardinality,
                identifying_yn,
                delete_rule_code,
                update_rule_code,
                enabled_yn,
                sort_no,
                created_by,
                created_dt,
                updated_by,
                updated_dt,
                deleted_by,
                deleted_dt,
                client_ip,
                program_id
            )
            VALUES
            (
                %s,
                'OBJECT',
                NULL,
                NULL,
                %s,
                %s,
                NULL,
                %s,
                %s,
                %s,
                %s,
                %s,
                %s,
                %s,
                %s,
                %s,
                %s,
                %s,
                %s,
                %s,
                %s,
                %s,
                %s,
                CURRENT_TIMESTAMP,
                %s,
                CURRENT_TIMESTAMP,
                NULL,
                NULL,
                %s,
                %s
            )
            """,
            (
                row["relationship_id"],
                row["source_object_id"],
                row["source_object_type_code"],
                row["target_object_id"],
                row["target_object_type_code"],
                row["relationship_code"],
                row["relationship_name"],
                row.get("relationship_description"),
                row["relationship_type_code"],
                row["source_min_cardinality"],
                row["source_max_cardinality"],
                row["target_min_cardinality"],
                row["target_max_cardinality"],
                row["identifying_yn"],
                row.get("delete_rule_code"),
                row.get("update_rule_code"),
                row["enabled_yn"],
                row["sort_no"],
                row["created_by"],
                row["updated_by"],
                row["client_ip"],
                row["program_id"],
            ),
        )

        if affected != 1:
            raise RuntimeError(
                "Relationship Repository save failed. "
                f"relationship_code={row['relationship_code']}, "
                f"affected_rows={affected}"
            )

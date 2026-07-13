"""
SPS Metadata Generator

Purpose:
    Metadata Object의 Identifier를 Repository Metadata로 발급하고
    sp_metadata에 규제 Metadata를 저장한다.

Principles:
    - Repository First
    - Object First
    - Generator First
    - Metadata Driven
    - Single Source of Truth
    - No Hardcoding
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from common.database import CommonDatabase
from engine.identifier_engine import IdentifierEngine


class MetadataGenerator:
    """SPS Metadata Repository Generator."""

    OBJECT_CODE = "METADATA"

    REQUIRED_FIELDS = (
        "target_type_code",
        "target_id",
        "metadata_type_code",
        "metadata_key",
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
        """Metadata 여러 건을 하나의 Transaction으로 생성한다."""
        if not isinstance(requests, list) or not requests:
            raise ValueError(
                "Metadata requests must be a non-empty list."
            )

        normalized_requests = [
            self._normalize_request(request)
            for request in requests
        ]

        self._validate_duplicate_keys(normalized_requests)

        existing_rows = self._find_existing_metadata(
            normalized_requests
        )

        if existing_rows:
            return {
                "success": False,
                "status": "ALREADY_EXISTS",
                "message": (
                    "One or more metadata records already exist."
                ),
                "metadata_count": 0,
                "metadata": existing_rows,
            }

        generated_rows: list[dict[str, Any]] = []
        batch_dt = datetime.now()

        try:
            self.database.begin()

            existing_rows = self._find_existing_metadata(
                normalized_requests
            )

            if existing_rows:
                self.database.rollback()

                return {
                    "success": False,
                    "status": "ALREADY_EXISTS",
                    "message": (
                        "Metadata records were created "
                        "by another process."
                    ),
                    "metadata_count": 0,
                    "metadata": existing_rows,
                }

            for request in normalized_requests:
                metadata_id = (
                    self.identifier_engine.generate_for_level(
                        object_code=self.OBJECT_CODE,
                        object_level=4,
                        now=batch_dt,
                        manage_transaction=False,
                    )
                )

                generated_row = {
                    **request,
                    "metadata_id": metadata_id,
                }

                self._insert_metadata(generated_row)
                generated_rows.append(generated_row)

            self.database.commit()

        except Exception:
            self.database.rollback()
            raise

        saved_rows = self._find_metadata_by_ids(
            [
                row["metadata_id"]
                for row in generated_rows
            ]
        )

        return {
            "success": True,
            "status": "CREATED",
            "message": (
                f"{len(saved_rows)} metadata records "
                "created successfully."
            ),
            "metadata_count": len(saved_rows),
            "metadata": saved_rows,
        }

    def _normalize_request(
        self,
        request: dict[str, Any],
    ) -> dict[str, Any]:
        """Metadata Request를 정규화한다."""
        if not isinstance(request, dict):
            raise TypeError(
                "Each metadata request must be a dictionary."
            )

        normalized = dict(request)

        for field in self.REQUIRED_FIELDS:
            value = normalized.get(field)

            if value is None or not str(value).strip():
                raise ValueError(
                    f"Required metadata field is missing: {field}"
                )

            normalized[field] = str(value).strip()

        uppercase_fields = (
            "target_type_code",
            "metadata_type_code",
            "metadata_value_type_code",
            "enabled_yn",
        )

        for field in uppercase_fields:
            value = normalized.get(field)

            if value is not None:
                normalized[field] = (
                    str(value).strip().upper()
                )

        normalized.setdefault(
            "metadata_value_type_code",
            "STRING",
        )
        normalized.setdefault("enabled_yn", "Y")
        normalized.setdefault("sort_no", 0)
        normalized.setdefault("created_by", "SYSTEM")
        normalized.setdefault("updated_by", "SYSTEM")
        normalized.setdefault(
            "program_id",
            "MetadataGenerator",
        )
        normalized.setdefault("client_ip", "127.0.0.1")

        return normalized

    def _validate_duplicate_keys(
        self,
        requests: list[dict[str, Any]],
    ) -> None:
        """동일 Batch 내부 Metadata Key 중복을 검증한다."""
        keys = [
            (
                request["target_type_code"],
                request["target_id"],
                request["metadata_key"],
            )
            for request in requests
        ]

        if len(keys) != len(set(keys)):
            raise ValueError(
                "Duplicate metadata keys exist in the request."
            )

    def _find_existing_metadata(
        self,
        requests: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """기존 Metadata를 조회한다."""
        rows: list[dict[str, Any]] = []

        sql = """
            SELECT
                metadata_id,
                target_type_code,
                target_id,
                metadata_type_code,
                metadata_key,
                metadata_value,
                metadata_value_type_code,
                metadata_json,
                enabled_yn,
                sort_no
            FROM sp_metadata
            WHERE target_type_code = %s
              AND target_id = %s
              AND metadata_key = %s
              AND deleted_dt IS NULL
        """

        for request in requests:
            row = self.database.fetch_one(
                sql,
                (
                    request["target_type_code"],
                    request["target_id"],
                    request["metadata_key"],
                ),
            )

            if row:
                rows.append(row)

        return rows

    def _insert_metadata(
        self,
        row: dict[str, Any],
    ) -> None:
        """sp_metadata에 Metadata를 저장한다."""
        sql = """
            INSERT INTO sp_metadata
            (
                metadata_id,
                target_type_code,
                target_id,
                metadata_type_code,
                metadata_key,
                metadata_value,
                metadata_value_type_code,
                metadata_json,
                enabled_yn,
                sort_no,
                created_by,
                created_dt,
                updated_by,
                updated_dt,
                client_ip,
                program_id
            )
            VALUES
            (
                %s, %s, %s, %s, %s,
                %s, %s, %s, %s, %s,
                %s, NOW(), %s, NOW(), %s, %s
            )
        """

        affected_rows = self.database.execute(
            sql,
            (
                row["metadata_id"],
                row["target_type_code"],
                row["target_id"],
                row["metadata_type_code"],
                row["metadata_key"],
                row.get("metadata_value"),
                row["metadata_value_type_code"],
                row.get("metadata_json"),
                row["enabled_yn"],
                int(row["sort_no"]),
                row["created_by"],
                row["updated_by"],
                row["client_ip"],
                row["program_id"],
            ),
        )

        if affected_rows != 1:
            raise RuntimeError(
                "Metadata insert failed. "
                f"affected_rows={affected_rows}"
            )

    def _find_metadata_by_ids(
        self,
        metadata_ids: list[str],
    ) -> list[dict[str, Any]]:
        """생성된 Metadata를 조회한다."""
        rows: list[dict[str, Any]] = []

        sql = """
            SELECT
                metadata_id,
                target_type_code,
                target_id,
                metadata_type_code,
                metadata_key,
                metadata_value,
                metadata_value_type_code,
                metadata_json,
                enabled_yn,
                sort_no
            FROM sp_metadata
            WHERE metadata_id = %s
              AND deleted_dt IS NULL
        """

        for metadata_id in metadata_ids:
            row = self.database.fetch_one(
                sql,
                (metadata_id,),
            )

            if row:
                rows.append(row)

        return rows

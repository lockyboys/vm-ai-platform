from __future__ import annotations

import re
from typing import Any


class ObjectDefinitionRequestProcessor:
    """Object Definition 요청 정규화와 입력 형식 검증."""

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

    def normalize(
        self,
        request: dict[str, Any],
    ) -> dict[str, Any]:
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

        description = normalized.get("object_description")
        normalized["object_description"] = (
            str(description).strip()
            if description is not None
            else None
        )

        if normalized.get("object_level") is not None:
            normalized["object_level"] = int(
                normalized["object_level"]
            )

        if normalized.get("sequence_length") is not None:
            normalized["sequence_length"] = int(
                normalized["sequence_length"]
            )

        normalized.setdefault("status_code", "ACTIVE")
        normalized.setdefault("active_yn", "Y")
        normalized.setdefault("version_no", "v1.0")
        normalized.setdefault("sort_no", 0)
        normalized.setdefault(
            "created_by",
            "OBJECT_DEFINITION_ENGINE",
        )
        normalized.setdefault(
            "updated_by",
            "OBJECT_DEFINITION_ENGINE",
        )
        normalized.setdefault(
            "program_id",
            "ObjectDefinitionEngine",
        )
        normalized.setdefault("client_ip", "127.0.0.1")
        normalized.setdefault("parent_object_id", None)
        normalized.setdefault("lifecycle_id", None)
        normalized.setdefault("target_identifier_field", None)
        normalized.setdefault(
            "change_reason",
            "Object Definition Engine 생성",
        )

        return normalized

    def validate(
        self,
        request: dict[str, Any],
    ) -> None:
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

        object_level = int(request["object_level"])
        if object_level < 0 or object_level > 4:
            raise ValueError(
                "object_level must be between 0 and 4."
            )

        sequence_length = int(request["sequence_length"])
        if sequence_length < 1 or sequence_length > 20:
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

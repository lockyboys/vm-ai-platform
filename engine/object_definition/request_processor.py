"""Object Definition 입력 정규화와 형식 검증.

Change History
20260912 | Codex | 단일 Engine 통합 시 구형 버전·선택 Level 입력의 호환성을 보존한다.
"""

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

        if normalized.get("object_level") not in (None, ""):
            normalized["object_level"] = int(normalized["object_level"])
        else:
            normalized.pop("object_level", None)

        if normalized.get("sequence_length") is not None:
            normalized["sequence_length"] = int(
                normalized["sequence_length"]
            )

        normalized.setdefault("status_code", "ACTIVE")
        normalized.setdefault("active_yn", "Y")
        # 실제 저장 컬럼은 version_num이다. 구형 별칭은 한 번만 변환한다.
        legacy_version = normalized.pop("version_no", None)
        version_num = normalized.get("version_num")
        if (
            legacy_version not in (None, "")
            and version_num not in (None, "")
            and legacy_version != version_num
        ):
            raise ValueError("version_no and version_num must agree.")
        normalized["version_num"] = version_num or legacy_version or "v1.0"
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

        if request.get("object_level") is not None:
            object_level = int(request["object_level"])
            # 허용 Level의 상한은 코드가 아닌 활성 Rule·Blueprint가 결정한다.
            # 여기서는 입력 형식만 검사하고, 실제 저장 Level은 prepare에서 확정한다.
            if object_level < 0:
                raise ValueError("object_level must be non-negative.")

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

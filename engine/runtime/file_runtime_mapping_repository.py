"""Repository-driven File Runtime extension mapping."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping

from common.common_function import normalize_required_text
from common.database import CommonDatabase


class FileRuntimeMappingRepository:
    """Resolve file extension to Object and Analyzer from Common Repository metadata."""

    def __init__(self, common_database: CommonDatabase, *, group_code: str) -> None:
        self._common_database = common_database
        self._group_code = normalize_required_text(group_code, "group_code")

    def resolve(self, source_file: Path) -> dict[str, Any] | None:
        extension = source_file.suffix.lower()
        mappings = self.load_active_mappings()
        for mapping in mappings:
            if extension in mapping["extensions"]:
                return mapping

        defaults = [mapping for mapping in mappings if mapping["default_yn"] == "Y"]
        if len(defaults) > 1:
            raise ValueError(
                "File Runtime mapping must define at most one active default contract."
            )
        return defaults[0] if defaults else None

    def load_active_mappings(self) -> list[dict[str, Any]]:
        rows = self._common_database.fetch_all(
            """
            SELECT code, code_name, common_code_json
            FROM cm_common_code
            WHERE group_code = %s
              AND status_code = 'ACTIVE'
              AND deleted_dt IS NULL
            ORDER BY sort_no, code
            """,
            (self._group_code,),
        )
        return [self._parse_mapping(row) for row in rows]

    @staticmethod
    def _parse_mapping(row: Mapping[str, Any]) -> dict[str, Any]:
        code = normalize_required_text(row.get("code"), "code")
        try:
            mapping = json.loads(
                normalize_required_text(row.get("common_code_json"), "common_code_json")
            )
        except json.JSONDecodeError as error:
            raise ValueError(
                f"File Runtime mapping must contain valid JSON. code={code}"
            ) from error

        if not isinstance(mapping, dict):
            raise ValueError(f"File Runtime mapping must be a JSON object. code={code}")

        default_yn = str(mapping.get("default_yn", "N")).upper()
        if default_yn not in {"Y", "N"}:
            raise ValueError(f"File Runtime mapping default_yn is invalid. code={code}")

        extensions = mapping.get("extensions")
        if (
            not isinstance(extensions, list)
            or any(not isinstance(value, str) or not value.startswith(".") for value in extensions)
        ):
            raise ValueError(
                f"File Runtime mapping extensions must be dotted strings. code={code}"
            )
        if not extensions and default_yn != "Y":
            raise ValueError(
                f"File Runtime mapping requires extensions unless default_yn is Y. code={code}"
            )

        object_code = normalize_required_text(mapping.get("object_code"), "object_code")
        analyzer_module = mapping.get("analyzer_module")
        analyzer_method = mapping.get("analyzer_method")
        if (analyzer_module is None) != (analyzer_method is None):
            raise ValueError(
                f"File Runtime mapping analyzer module and method must be paired. code={code}"
            )
        if analyzer_module is not None:
            analyzer_module = normalize_required_text(analyzer_module, "analyzer_module")
            analyzer_method = normalize_required_text(analyzer_method, "analyzer_method")

        return {
            "mapping_code": code,
            "mapping_name": normalize_required_text(row.get("code_name"), "code_name"),
            "extensions": tuple(value.lower() for value in extensions),
            "default_yn": default_yn,
            "object_code": object_code,
            "analyzer_module": analyzer_module,
            "analyzer_method": analyzer_method,
        }

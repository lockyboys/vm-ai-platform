"""File Runtime mapping repository tests."""

from __future__ import annotations

import json
from pathlib import Path

from engine.runtime.file_runtime_mapping_repository import FileRuntimeMappingRepository


class _CommonDatabase:
    def __init__(self) -> None:
        self.rows = [
            {
                "code": "DOCUMENT",
                "code_name": "Document",
                "common_code_json": json.dumps(
                    {
                        "extensions": [".pdf"],
                        "object_code": "DOCUMENT",
                        "analyzer_module": "document_analyzer",
                        "analyzer_method": "extract_document_text",
                    }
                ),
            },
            {
                "code": "FILE",
                "code_name": "Default File",
                "common_code_json": json.dumps(
                    {
                        "extensions": [],
                        "default_yn": "Y",
                        "object_code": "FILE",
                        "analyzer_module": None,
                        "analyzer_method": None,
                    }
                ),
            },
        ]
        self.parameters: tuple[str, ...] | None = None

    def fetch_all(self, _sql: str, parameters: tuple[str, ...]):
        self.parameters = parameters
        return self.rows


def test_extension_mapping_resolves_repository_contract(tmp_path: Path) -> None:
    database = _CommonDatabase()
    source_file = tmp_path / "source.pdf"
    source_file.write_bytes(b"pdf")

    mapping = FileRuntimeMappingRepository(
        database, group_code="FILE_RUNTIME_MAPPING"
    ).resolve(source_file)

    assert database.parameters == ("FILE_RUNTIME_MAPPING",)
    assert mapping is not None
    assert mapping["object_code"] == "DOCUMENT"
    assert mapping["analyzer_module"] == "document_analyzer"


def test_unmatched_extension_uses_repository_default_contract(tmp_path: Path) -> None:
    database = _CommonDatabase()
    source_file = tmp_path / "source.bin"
    source_file.write_bytes(b"bin")

    mapping = FileRuntimeMappingRepository(
        database, group_code="FILE_RUNTIME_MAPPING"
    ).resolve(source_file)

    assert mapping is not None
    assert mapping["object_code"] == "FILE"
    assert mapping["analyzer_module"] is None
    assert mapping["analyzer_method"] is None

"""File Work Service common-module integration tests."""
from __future__ import annotations

from pathlib import Path

import pytest

from engine.processor.work.file_work_service import FileWorkService


@pytest.mark.parametrize(
    ("requested_by", "client_ip", "field_name"),
    (
        ("   ", "127.0.0.1", "requested_by"),
        ("operator", "   ", "client_ip"),
    ),
)
def test_process_rejects_blank_audit_context_before_database_access(
    requested_by: str,
    client_ip: str,
    field_name: str,
) -> None:
    service = FileWorkService(output_root=Path("output/test_file_work"))

    with pytest.raises(ValueError, match=f"{field_name} is required"):
        service.process(
            upload_path=Path("not-used-before-input-validation.pdf"),
            requested_by=requested_by,
            client_ip=client_ip,
        )

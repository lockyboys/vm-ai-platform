"""Tests for the Harness storage-separation batch entrypoint."""

from __future__ import annotations

from harness.scripts import migrate_storage_separation_contracts as batch


def test_default_contracts_are_execution_ready() -> None:
    assert batch.DEFAULT_CONTRACT_CODES == (
        "CM_VERIFIED_SQL_DETAIL",
        "COMMON_REPOSITORY_DETAIL",
        "STORAGE_REPOSITORY_CHANGE_STORY",
    )

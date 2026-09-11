"""Tests for MariaDB payload-backup table verification."""

from __future__ import annotations

import harness.scripts.verify_storage_separation_mariadb_backups as verifier


class _FakeDatabase:
    def fetch_one(self, sql: str):
        assert sql == "SELECT COUNT(*) AS row_count FROM `cm_repository_payload_backup_20260902`"
        return {"row_count": 3}


def test_row_count_uses_a_valid_quoted_identifier() -> None:
    assert verifier._row_count(_FakeDatabase(), "cm_repository_payload_backup_20260902") == 3

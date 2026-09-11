"""Tests for cm_verified_sql_query physical backup refresh."""

from __future__ import annotations

import harness.scripts.refresh_cm_verified_sql_query_backup as refresh


def test_refresh_uses_safe_mariadb_identifier_quoting() -> None:
    assert refresh._quoted("cm_verified_sql_query") == "`cm_verified_sql_query`"


def test_generated_archive_names_stay_within_mariadb_limit() -> None:
    utc_stamp = "20260902140500"
    assert len(refresh.ARCHIVE_TABLE_PREFIX + utc_stamp) <= 64
    assert len(refresh.STAGING_STALE_TABLE_PREFIX + utc_stamp) <= 64

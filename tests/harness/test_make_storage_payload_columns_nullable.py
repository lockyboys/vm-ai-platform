"""Tests for payload-column nullable migration configuration."""

from __future__ import annotations

from harness.scripts import make_storage_payload_columns_nullable as migration


def test_all_not_null_payload_columns_are_listed() -> None:
    assert migration.TARGETS == (
        ("COMMON", "cm_verified_sql_query", "sql_text", "LONGTEXT"),
        ("COMMON", "cm_code_inspection_result", "message", "TEXT"),
        ("STORY", "sp_impact_analysis_result", "change_target_text", "TEXT"),
    )

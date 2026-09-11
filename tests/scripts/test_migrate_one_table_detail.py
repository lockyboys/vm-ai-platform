"""Storage separation physical-move contract tests."""

from __future__ import annotations

import inspect

import pytest

from common.database import MariaMongoWriteService
from scripts.migrate_one_table_detail import (
    _assert_source_queries_share_transaction_scope,
    _build_mongodb_payload,
    _clear_source_payload,
    _insert_change_history,
    _resolve_source_clear_parameters,
)


class FakeDatabase:
    """Minimal CommonDatabase double for storage-separation guards."""

    def __init__(
        self,
        *,
        database_name: str,
        host: str = "127.0.0.1",
        port: str = "3306",
        user: str = "sps",
        affected_rows: int = 1,
    ) -> None:
        self.database_name = database_name
        self.config = {"host": host, "port": port, "user": user}
        self.affected_rows = affected_rows
        self.executions: list[tuple[str, tuple[str, ...]]] = []

    def execute(self, sql_text: str, parameters: tuple[str, ...]) -> int:
        self.executions.append((sql_text, parameters))
        return self.affected_rows


def test_build_mongodb_payload_uses_metadata_target_field_name() -> None:
    assert _build_mongodb_payload(
        {"report_content": "report body"},
        payload_column_names=["report_content"],
        mongodb_payload_field_name="health_report_content",
    ) == {"health_report_content": "report body"}


def test_build_mongodb_payload_nests_multiple_source_columns_under_target_field() -> None:
    assert _build_mongodb_payload(
        {"affected_text": "affected", "analysis_note": "note"},
        payload_column_names=["affected_text", "analysis_note"],
        mongodb_payload_field_name="sp_impact_analysis_text",
    ) == {
        "sp_impact_analysis_text": {
            "affected_text": "affected",
            "analysis_note": "note",
        }
    }


def test_build_mongodb_payload_keeps_field_name_for_sparse_multi_column_row() -> None:
    assert _build_mongodb_payload(
        {"change_target_text": "cm_common_code"},
        payload_column_names=[
            "change_target_text",
            "affected_text",
            "analysis_note",
        ],
        mongodb_payload_field_name="sp_impact_analysis_text",
    ) == {
        "sp_impact_analysis_text": {
            "change_target_text": "cm_common_code",
        }
    }


def test_resolve_source_clear_parameters_uses_contract_order() -> None:
    parameters = _resolve_source_clear_parameters(
        {
            "migration_mode_code": "MOVE_PAYLOAD",
            "source_clear_parameter_codes": [
                "actor_id",
                "program_id",
                "client_ip",
                "source_identifier",
            ],
        },
        actor_id="TESTER",
        client_ip="127.0.0.1",
        source_identifier="REPORT_00001",
    )

    assert parameters == (
        "TESTER",
        "scripts.migrate_one_table_detail",
        "127.0.0.1",
        "REPORT_00001",
    )


def test_resolve_source_clear_parameters_rejects_copy_only_contract() -> None:
    with pytest.raises(ValueError, match="MOVE_PAYLOAD"):
        _resolve_source_clear_parameters(
            {
                "migration_mode_code": "FUTURE_PAYLOAD",
                "source_clear_parameter_codes": ["source_identifier"],
            },
            actor_id="TESTER",
            client_ip="127.0.0.1",
            source_identifier="REPORT_00001",
        )


def test_cross_role_move_requires_schema_qualified_verified_sql() -> None:
    source_database = FakeDatabase(database_name="te_common")
    transaction_database = FakeDatabase(database_name="te_story_platform")

    _assert_source_queries_share_transaction_scope(
        source_database=source_database,
        transaction_database=transaction_database,
        source_read_sql=(
            "SELECT health_report_id, report_content "
            "FROM te_common.health_report WHERE health_report_id = %s"
        ),
        source_clear_sql=(
            "UPDATE te_common.health_report "
            "SET report_content = NULL WHERE health_report_id = %s"
        ),
    )

    with pytest.raises(ValueError, match="schema-qualified"):
        _assert_source_queries_share_transaction_scope(
            source_database=source_database,
            transaction_database=transaction_database,
            source_read_sql=(
                "SELECT health_report_id, report_content "
                "FROM health_report WHERE health_report_id = %s"
            ),
            source_clear_sql=(
                "UPDATE te_common.health_report "
                "SET report_content = NULL WHERE health_report_id = %s"
            ),
        )


def test_clear_source_payload_requires_exactly_one_source_row() -> None:
    database = FakeDatabase(database_name="te_story_platform")

    _clear_source_payload(
        database,
        sql_text="UPDATE te_common.health_report SET report_content = NULL WHERE health_report_id = %s",
        parameters=("REPORT_00001",),
        source_table_name="health_report",
        source_identifier="REPORT_00001",
    )

    assert database.executions == [
        (
            "UPDATE te_common.health_report SET report_content = NULL WHERE health_report_id = %s",
            ("REPORT_00001",),
        )
    ]

    no_row_database = FakeDatabase(
        database_name="te_story_platform",
        affected_rows=0,
    )
    with pytest.raises(RuntimeError, match="did not affect one row"):
        _clear_source_payload(
            no_row_database,
            sql_text="UPDATE te_common.health_report SET report_content = NULL WHERE health_report_id = %s",
            parameters=("REPORT_00001",),
            source_table_name="health_report",
            source_identifier="REPORT_00001",
        )


def test_insert_change_history_records_migration_audit() -> None:
    database = FakeDatabase(database_name="te_story_platform")

    _insert_change_history(
        database,
        sql_text="INSERT INTO te_common.cm_change_history (...) VALUES (...)",
        change_history_id="CM_CO_CHANGE_00001",
        source_database_name="te_story_platform",
        source_table_name="sp_impact_analysis_result",
        source_identifier="SP_RP_IMPACT_ANALYSIS_00001",
        actor_id="jeaje",
        client_ip="127.0.0.1",
    )

    assert database.executions == [
        (
            "INSERT INTO te_common.cm_change_history (...) VALUES (...)",
            (
                "CM_CO_CHANGE_00001",
                "te_story_platform",
                "sp_impact_analysis_result",
                "SP_RP_IMPACT_ANALYSIS_00001",
                "UPDATE",
                "Moved MariaDB detail payload to MongoDB and linked the execution.",
                "jeaje",
                "127.0.0.1",
                "scripts.migrate_one_table_detail",
            ),
        )
    ]

def test_common_database_writer_accepts_compensation_filter() -> None:
    parameters = inspect.signature(
        MariaMongoWriteService.insert_mongodb_document
    ).parameters
    assert "compensation_filter" in parameters

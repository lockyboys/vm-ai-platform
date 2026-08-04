"""Regression tests for the deployed Object Level Rule Action procedure contract."""

from pathlib import Path


_SQL_PATH = "sql/runtime/08_reconcile_object_level_negative_default_condition_20260802.sql"


def test_object_level_procedure_accepts_condition_bound_default_action() -> None:
    project_root = Path(__file__).resolve().parents[1]
    sql_text = (project_root / _SQL_PATH).read_text(encoding="utf-8")
    procedure_body = sql_text.split(
        "CREATE PROCEDURE sp_resolve_object_level_classification"
    )[1].split("END$$")[0]

    for context_key in (
        "rule_id",
        "rule_action_id",
        "action_type_code",
        "action_type_group_code",
    ):
        assert f"$.{context_key}" in procedure_body

    assert "WHERE r.rule_code =" not in procedure_body
    assert "code = 'OBJECT_LEVEL_CLASSIFICATION'" not in procedure_body
    assert "c.group_code = v_action_type_group_code" in procedure_body
    assert "a.action_type_code = v_action_type_code" in procedure_body
    assert "$.condition_id" in procedure_body
    assert "$.resolution_order" in procedure_body
    assert "JSON_CONTAINS(" in procedure_body
    assert "JSON_QUOTE('DEFAULT')" in procedure_body
    assert "v_selected_condition_id IS NOT NULL" not in procedure_body
    assert "DEFAULT resolution" in procedure_body

    for declaration in (
        "DECLARE v_rule_id VARCHAR(99) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci;",
        "DECLARE v_rule_action_id VARCHAR(99) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci;",
        "DECLARE v_action_type_code VARCHAR(99) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;",
        "DECLARE v_action_type_group_code VARCHAR(99) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;",
    ):
        assert declaration in procedure_body

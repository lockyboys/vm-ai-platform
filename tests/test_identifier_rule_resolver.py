"""Identifier Rule Resolver regression tests."""

from __future__ import annotations

import json
from typing import Any

import pytest

from engine.common.identifier_rule_resolver import IdentifierRuleResolver


class _RuleDatabase:
    def __init__(
        self,
        *,
        actions: list[dict[str, Any]],
        conditions_by_rule: dict[str, list[dict[str, Any]]] | None = None,
    ) -> None:
        self.actions = actions
        self.conditions_by_rule = conditions_by_rule or {}
        self.calls: list[tuple[str, tuple[Any, ...] | None]] = []

    def fetch_all(
        self,
        sql: str,
        parameters: tuple[Any, ...] | None = None,
    ) -> list[dict[str, Any]]:
        self.calls.append((sql, parameters))
        if "FROM rl_rule_condition" in sql:
            assert parameters is not None
            return self.conditions_by_rule.get(str(parameters[0]), [])
        return self.actions

    def fetch_one(
        self,
        sql: str,
        parameters: tuple[Any, ...] | None = None,
    ) -> dict[str, Any] | None:
        self.calls.append((sql, parameters))
        return {"timezone_id": "Asia/Seoul"}

class _RuleActionRuntime:
    def __init__(
        self,
        *,
        default_object_level: int = 4,
        result_rule_id: str | None = None,
        result_rule_code: str | None = None,
        result_rule_action_id: str | None = None,
        result_action_type_code: str | None = None,
        result_resolution_source: str = "DEFAULT",
    ) -> None:
        self.default_object_level = default_object_level
        self.result_rule_id = result_rule_id
        self.result_rule_code = result_rule_code
        self.result_rule_action_id = result_rule_action_id
        self.result_action_type_code = result_action_type_code
        self.result_resolution_source = result_resolution_source
        self.rule_codes_by_id: dict[str, str] = {}
        self.action_type_codes_by_action_id: dict[str, str] = {}
        self.calls: list[tuple[str, str, dict[str, Any]]] = []

    def execute_action(
        self,
        rule_id: str,
        rule_action_id: str,
        parameters: dict[str, Any],
    ) -> dict[str, Any]:
        self.calls.append((rule_id, rule_action_id, parameters))
        return {
            "rule_action_id": rule_action_id,
            "result": {
                "result": [
                    {
                        "rule_id": self.result_rule_id or rule_id,
                        "rule_code": self.result_rule_code
                        or self.rule_codes_by_id[rule_id],
                        "rule_action_id": self.result_rule_action_id
                        or rule_action_id,
                        "action_type_code": self.result_action_type_code
                        or self.action_type_codes_by_action_id[rule_action_id],
                        "default_object_level": self.default_object_level,
                        "resolution_source": self.result_resolution_source,
                    },
                ],
            },
        }


def _action_row(
    *,
    rule_id: str,
    rule_code: str,
    rule_action_id: str,
    action_type_code: str = "OBJECT_LEVEL_CLASSIFICATION",
    action_contract: dict[str, Any],
) -> dict[str, Any]:
    return {
        "rule_id": rule_id,
        "rule_code": rule_code,
        "priority_no": 100,
        "rule_sort_no": 10,
        "rule_action_id": rule_action_id,
        "action_type_code": action_type_code,
        "action_value": json.dumps(action_contract),
        "action_sort_no": 10,
        "action_type_contract_json": json.dumps(
            {"action_code": action_type_code}
        ),
    }


def _resolver(
    *,
    actions: list[dict[str, Any]],
    conditions_by_rule: dict[str, list[dict[str, Any]]] | None = None,
    runtime: _RuleActionRuntime | None = None,
) -> tuple[IdentifierRuleResolver, _RuleActionRuntime]:
    action_runtime = runtime or _RuleActionRuntime()
    action_runtime.rule_codes_by_id.update(
        {str(action["rule_id"]): str(action["rule_code"]) for action in actions}
    )
    action_runtime.action_type_codes_by_action_id.update(
        {
            str(action["rule_action_id"]): str(action["action_type_code"])
            for action in actions
        }
    )
    resolver = IdentifierRuleResolver(
        rule_database=_RuleDatabase(
            actions=actions,
            conditions_by_rule=conditions_by_rule,
        ),
        rule_action_runtime=action_runtime,
    )
    return resolver, action_runtime


def test_definition_object_level_does_not_bypass_rule_default() -> None:
    resolver, runtime = _resolver(
        actions=[
            _action_row(
                rule_id="RULE_OBJECT_LEVEL",
                rule_code="RL_OBJECT_LEVEL_CLASSIFICATION",
                rule_action_id="ACTION_DEFAULT",
                action_contract={
                    "default_object_level": 4,
                    "resolution_order": ["DEFAULT"],
                    "verified_query_id": "VERIFIED_QUERY_OBJECT_LEVEL",
                },
            )
        ]
    )

    metadata = {
        "object_code": "WORK_SESSION",
        "object_level": 3,
    }
    resolution = resolver.resolve_object_level(metadata)

    assert resolution.rule_code == "RL_OBJECT_LEVEL_CLASSIFICATION"
    assert resolution.rule_action_id == "ACTION_DEFAULT"
    assert resolution.object_level == 4
    assert resolution.resolution_source == "DEFAULT"
    assert runtime.calls == [
        ("RULE_OBJECT_LEVEL", "ACTION_DEFAULT", {"object_code": "WORK_SESSION"})
    ]


def test_default_object_level_executes_registered_rule_action() -> None:
    resolver, runtime = _resolver(
        actions=[
            _action_row(
                rule_id="RULE_OBJECT_LEVEL",
                rule_code="RL_OBJECT_LEVEL_CLASSIFICATION",
                rule_action_id="ACTION_DEFAULT",
                action_contract={
                    "default_object_level": 4,
                    "resolution_order": ["DEFAULT"],
                    "verified_query_id": "VERIFIED_QUERY_OBJECT_LEVEL",
                },
            )
        ]
    )
    metadata = {"object_code": "UNCLASSIFIED"}

    resolution = resolver.resolve_object_level(metadata)

    assert resolution.object_level == 4
    assert resolution.resolution_source == "DEFAULT"
    assert runtime.calls == [
        ("RULE_OBJECT_LEVEL", "ACTION_DEFAULT", metadata)
    ]


def test_condition_id_binds_each_branch_and_negative_default() -> None:
    rule_id = "RULE_OBJECT_LEVEL"
    rule_code = "RL_OBJECT_LEVEL_CLASSIFICATION"
    default_action = _action_row(
        rule_id=rule_id,
        rule_code=rule_code,
        rule_action_id="ACTION_DEFAULT",
        action_contract={
            "condition_id": "CONDITION_DEFAULT",
            "condition_context": {"rule_resolution_source": "DEFAULT"},
            "default_object_level": 4,
            "resolution_order": ["DEFAULT"],
            "verified_query_id": "VERIFIED_QUERY_OBJECT_LEVEL",
        },
    )
    resolver, runtime = _resolver(
        actions=[
            default_action,
            _action_row(
                rule_id=rule_id,
                rule_code=rule_code,
                rule_action_id="ACTION_ERD",
                action_contract={
                    "condition_id": "CONDITION_ERD",
                    "object_level": 2,
                    "resolution_order": ["EXPLICIT_RULE"],
                },
            ),
            _action_row(
                rule_id=rule_id,
                rule_code=rule_code,
                rule_action_id="ACTION_ENTITY",
                action_contract={
                    "condition_id": "CONDITION_ENTITY",
                    "object_level": 3,
                    "resolution_order": ["EXPLICIT_RULE"],
                },
            ),
            _action_row(
                rule_id=rule_id,
                rule_code=rule_code,
                rule_action_id="ACTION_RELATIONSHIP",
                action_contract={
                    "condition_id": "CONDITION_RELATIONSHIP",
                    "object_level": 3,
                    "resolution_order": ["EXPLICIT_RULE"],
                },
            ),
        ],
        conditions_by_rule={
            rule_id: [
                {
                    "condition_id": "CONDITION_ERD",
                    "field_code": "object_code",
                    "operator_code": "EQ",
                    "condition_value": "ERD",
                    "logical_operator_code": None,
                    "sort_no": 10,
                },
                {
                    "condition_id": "CONDITION_ENTITY",
                    "field_code": "object_code",
                    "operator_code": "EQ",
                    "condition_value": "ENTITY",
                    "logical_operator_code": None,
                    "sort_no": 20,
                },
                {
                    "condition_id": "CONDITION_RELATIONSHIP",
                    "field_code": "object_code",
                    "operator_code": "EQ",
                    "condition_value": "RELATIONSHIP",
                    "logical_operator_code": None,
                    "sort_no": 30,
                },
                {
                    "condition_id": "CONDITION_DEFAULT",
                    "field_code": "rule_resolution_source",
                    "operator_code": "EQ",
                    "condition_value": "DEFAULT",
                    "logical_operator_code": None,
                    "sort_no": 40,
                },
            ]
        },
    )

    expected = {
        "ERD": ("ACTION_ERD", 2, "EXPLICIT_RULE"),
        "ENTITY": ("ACTION_ENTITY", 3, "EXPLICIT_RULE"),
        "RELATIONSHIP": ("ACTION_RELATIONSHIP", 3, "EXPLICIT_RULE"),
        "EXECUTION_HISTORY": ("ACTION_DEFAULT", 4, "DEFAULT"),
    }
    for object_code, (action_id, object_level, source) in expected.items():
        resolution = resolver.resolve_object_level(
            {"object_code": object_code, "object_level": 3}
        )

        assert resolution.rule_action_id == action_id
        assert resolution.object_level == object_level
        assert resolution.resolution_source == source

    assert runtime.calls == [
        (
            rule_id,
            "ACTION_DEFAULT",
            {"object_code": "EXECUTION_HISTORY"},
        )
    ]


def test_condition_bound_action_requires_existing_condition() -> None:
    resolver, _ = _resolver(
        actions=[
            _action_row(
                rule_id="RULE_OBJECT_LEVEL",
                rule_code="RL_OBJECT_LEVEL_CLASSIFICATION",
                rule_action_id="ACTION_MISSING_CONDITION",
                action_contract={
                    "condition_id": "CONDITION_MISSING",
                    "object_level": 3,
                    "resolution_order": ["EXPLICIT_RULE"],
                },
            )
        ]
    )

    with pytest.raises(
        LookupError,
        match="condition_id must reference exactly one active Rule Condition",
    ):
        resolver.resolve_object_level({"object_code": "ENTITY"})


def test_multiple_positive_condition_matches_fail_closed() -> None:
    rule_id = "RULE_OBJECT_LEVEL"
    resolver, _ = _resolver(
        actions=[
            _action_row(
                rule_id=rule_id,
                rule_code="RL_OBJECT_LEVEL_CLASSIFICATION",
                rule_action_id="ACTION_FIRST",
                action_contract={
                    "condition_id": "CONDITION_FIRST",
                    "object_level": 3,
                    "resolution_order": ["EXPLICIT_RULE"],
                },
            ),
            _action_row(
                rule_id=rule_id,
                rule_code="RL_OBJECT_LEVEL_CLASSIFICATION",
                rule_action_id="ACTION_SECOND",
                action_contract={
                    "condition_id": "CONDITION_SECOND",
                    "object_level": 3,
                    "resolution_order": ["EXPLICIT_RULE"],
                },
            ),
        ],
        conditions_by_rule={
            rule_id: [
                {
                    "condition_id": "CONDITION_FIRST",
                    "field_code": "object_code",
                    "operator_code": "EQ",
                    "condition_value": "ENTITY",
                    "logical_operator_code": None,
                    "sort_no": 10,
                },
                {
                    "condition_id": "CONDITION_SECOND",
                    "field_code": "object_code",
                    "operator_code": "EQ",
                    "condition_value": "ENTITY",
                    "logical_operator_code": None,
                    "sort_no": 20,
                },
            ]
        },
    )

    with pytest.raises(
        LookupError,
        match="matched multiple condition-bound Actions",
    ):
        resolver.resolve_object_level({"object_code": "ENTITY"})


def test_unknown_rule_condition_operator_fails_closed() -> None:
    resolver, _ = _resolver(
        actions=[
            _action_row(
                rule_id="RULE_INVALID_OPERATOR",
                rule_code="RL_INVALID_OPERATOR",
                rule_action_id="ACTION_INVALID_OPERATOR",
                action_contract={
                    "condition_id": "CONDITION_INVALID_OPERATOR",
                    "object_level": 3,
                    "resolution_order": ["EXPLICIT_RULE"],
                },
            )
        ],
        conditions_by_rule={
            "RULE_INVALID_OPERATOR": [
                {
                    "condition_id": "CONDITION_INVALID_OPERATOR",
                    "field_code": "object_type_code",
                    "operator_code": "CONTAINS",
                    "condition_value": "TABLE",
                    "logical_operator_code": None,
                    "sort_no": 10,
                }
            ]
        },
    )

    with pytest.raises(ValueError, match="Unsupported Rule condition operator"):
        resolver.resolve_object_level(
            {"object_code": "TABLE", "object_type_code": "TABLE"}
        )


def test_unknown_resolution_source_fails_closed() -> None:
    resolver, _ = _resolver(
        actions=[
            _action_row(
                rule_id="RULE_INVALID_SOURCE",
                rule_code="RL_INVALID_SOURCE",
                rule_action_id="ACTION_INVALID_SOURCE",
                action_contract={
                    "object_level": 3,
                    "resolution_order": ["HIERARCHY"],
                },
            )
        ]
    )

    with pytest.raises(ValueError, match="Unsupported Identifier Rule resolution source"):
        resolver.resolve_object_level({"object_code": "TABLE"})


def test_registered_procedure_result_must_match_rule_action_contract() -> None:
    runtime = _RuleActionRuntime(default_object_level=3)
    resolver, _ = _resolver(
        actions=[
            _action_row(
                rule_id="RULE_OBJECT_LEVEL",
                rule_code="RL_OBJECT_LEVEL_CLASSIFICATION",
                rule_action_id="ACTION_DEFAULT",
                action_contract={
                    "default_object_level": 4,
                    "resolution_order": ["DEFAULT"],
                    "verified_query_id": "VERIFIED_QUERY_OBJECT_LEVEL",
                },
            )
        ],
        runtime=runtime,
    )

    with pytest.raises(
        ValueError,
        match="default Object Level does not match Procedure result",
    ):
        resolver.resolve_object_level({"object_code": "UNCLASSIFIED"})


def test_registered_procedure_must_identify_the_selected_rule() -> None:
    runtime = _RuleActionRuntime(result_rule_code="RL_DIFFERENT_OBJECT_LEVEL")
    resolver, _ = _resolver(
        actions=[
            _action_row(
                rule_id="RULE_OBJECT_LEVEL",
                rule_code="RL_OBJECT_LEVEL_CLASSIFICATION",
                rule_action_id="ACTION_DEFAULT",
                action_contract={
                    "default_object_level": 4,
                    "resolution_order": ["DEFAULT"],
                    "verified_query_id": "VERIFIED_QUERY_OBJECT_LEVEL",
                },
            )
        ],
        runtime=runtime,
    )

    with pytest.raises(
        ValueError,
        match="Procedure resolved a different Rule",
    ):
        resolver.resolve_object_level({"object_code": "UNCLASSIFIED"})


@pytest.mark.parametrize(
    "runtime",
    (
        _RuleActionRuntime(result_rule_action_id="ACTION_DIFFERENT"),
        _RuleActionRuntime(result_action_type_code="DIFFERENT_ACTION_TYPE"),
    ),
)
def test_registered_procedure_must_identify_the_selected_action_contract(
    runtime: _RuleActionRuntime,
) -> None:
    resolver, _ = _resolver(
        actions=[
            _action_row(
                rule_id="RULE_OBJECT_LEVEL",
                rule_code="RL_OBJECT_LEVEL_CLASSIFICATION",
                rule_action_id="ACTION_DEFAULT",
                action_contract={
                    "default_object_level": 4,
                    "resolution_order": ["DEFAULT"],
                    "verified_query_id": "VERIFIED_QUERY_OBJECT_LEVEL",
                },
            )
        ],
        runtime=runtime,
    )

    with pytest.raises(
        ValueError,
        match="Procedure resolved a different Rule",
    ):
        resolver.resolve_object_level({"object_code": "UNCLASSIFIED"})


def test_explicit_rule_is_evaluated_before_group_default() -> None:
    high_priority = _action_row(
        rule_id="RULE_HIGH",
        rule_code="RL_HIGH_DEFAULT",
        rule_action_id="ACTION_HIGH_DEFAULT",
        action_contract={
            "default_object_level": 4,
            "resolution_order": ["DEFAULT"],
            "verified_query_id": "VERIFIED_QUERY_OBJECT_LEVEL",
        },
    )
    high_priority["priority_no"] = 200
    lower_priority = _action_row(
        rule_id="RULE_LOW",
        rule_code="RL_LOW_EXPLICIT",
        rule_action_id="ACTION_LOW_EXPLICIT",
        action_contract={
            "condition_id": "CONDITION_LOW",
            "object_level": 2,
            "resolution_order": ["EXPLICIT_RULE"],
        },
    )

    resolver, runtime = _resolver(
        actions=[high_priority, lower_priority],
        conditions_by_rule={
            "RULE_LOW": [
                {
                    "condition_id": "CONDITION_LOW",
                    "field_code": "object_code",
                    "operator_code": "EQ",
                    "condition_value": "UNCLASSIFIED",
                    "logical_operator_code": None,
                    "sort_no": 10,
                }
            ]
        },
    )

    resolution = resolver.resolve_object_level(
        {"object_code": "UNCLASSIFIED", "object_level": 2}
    )

    assert resolution.rule_code == "RL_LOW_EXPLICIT"
    assert resolution.rule_action_id == "ACTION_LOW_EXPLICIT"
    assert resolution.object_level == 2
    assert resolution.resolution_source == "EXPLICIT_RULE"
    assert runtime.calls == []


def test_invalid_active_rule_action_contract_fails_closed() -> None:
    malformed_action = _action_row(
        rule_id="RULE_INVALID_CONTRACT",
        rule_code="RL_INVALID_CONTRACT",
        rule_action_id="ACTION_INVALID_CONTRACT",
        action_contract={
            "default_object_level": 4,
            "resolution_order": ["DEFAULT"],
        },
    )
    malformed_action["action_value"] = "{not-valid-json"

    resolver, _ = _resolver(actions=[malformed_action])

    with pytest.raises(ValueError, match="Rule Action contract.*valid JSON"):
        resolver.resolve_object_level({"object_code": "UNCLASSIFIED"})


def test_table_object_id_and_execution_table_id_use_distinct_levels() -> None:
    resolver, _ = _resolver(
        actions=[
            _action_row(
                rule_id="RULE_ALL_TABLE_LEVEL3",
                rule_code="RL_TABLE_OBJECT_LEVEL3",
                rule_action_id="ACTION_TABLE_LEVEL3",
                action_contract={
                    "condition_id": "CONDITION_OBJECT_CODE_TABLE",
                    "object_level": 3,
                    "resolution_order": ["EXPLICIT_RULE"],
                },
            ),
            _action_row(
                rule_id="RULE_OBJECT_LEVEL",
                rule_code="RL_OBJECT_LEVEL_CLASSIFICATION",
                rule_action_id="ACTION_TABLE_IDENTIFIER_LEVEL4",
                action_contract={
                    "condition_id": "CONDITION_TABLE_IDENTIFIER_FIELD",
                    "object_level": 4,
                    "resolution_order": ["EXPLICIT_RULE"],
                },
            ),
            _action_row(
                rule_id="RULE_OBJECT_LEVEL",
                rule_code="RL_OBJECT_LEVEL_CLASSIFICATION",
                rule_action_id="ACTION_OBJECT_DEFAULT_LEVEL3",
                action_contract={
                    "default_object_level": 3,
                    "resolution_order": ["DEFAULT"],
                },
            ),
        ],
        conditions_by_rule={
            "RULE_ALL_TABLE_LEVEL3": [
                {
                    "condition_id": "CONDITION_OBJECT_CODE_TABLE",
                    "field_code": "object_code",
                    "operator_code": "EQ",
                    "condition_value": "TABLE",
                    "logical_operator_code": None,
                    "sort_no": 10,
                }
            ],
            "RULE_OBJECT_LEVEL": [
                {
                    "condition_id": "CONDITION_TABLE_IDENTIFIER_FIELD",
                    "field_code": "target_identifier_field",
                    "operator_code": "NOT_NULL",
                    "condition_value": "PRESENT",
                    "logical_operator_code": None,
                    "sort_no": 50,
                }
            ],
        },
    )

    table_resolution = resolver.resolve_object_level(
        {
            "object_code": "TABLE",
            "object_type_code": "TABLE",
            "object_level": 3,
            "target_identifier_field": None,
        }
    )
    execution_resolution = resolver.resolve_object_level(
        {
            "object_code": "EXECUTION_HISTORY",
            "object_type_code": "TABLE",
            "object_level": 3,
            "target_identifier_field": "execution_history_id",
        }
    )

    assert table_resolution.object_level == 3
    assert table_resolution.rule_code == "RL_TABLE_OBJECT_LEVEL3"
    assert execution_resolution.object_level == 4


def test_identifier_timezone_is_resolved_from_independent_time_rule() -> None:
    time_action = _action_row(
        rule_id="RULE_IDENTIFIER_TIMEZONE",
        rule_code="RL_IDENTIFIER_TIMEZONE_DEFAULT",
        rule_action_id="ACTION_TIMEZONE_DEFAULT",
        action_type_code="IDENTIFIER_TIMEZONE_RESOLUTION",
        action_contract={
            "condition_id": "CONDITION_TIMEZONE_DEFAULT",
            "timezone_id": "UTC",
            "resolution_order": ["DEFAULT"],
        },
    )
    time_action.update(
        {
            "condition_id": "CONDITION_TIMEZONE_DEFAULT",
            "field_code": "rule_resolution_source",
            "operator_code": "EQ",
            "condition_value": "DEFAULT",
            "logical_operator_code": None,
            "condition_sort_no": 90,
        }
    )
    resolver, _ = _resolver(actions=[time_action])

    timezone_id = resolver.resolve_timezone_id({"object_code": "EXECUTION_HISTORY"})

    assert timezone_id == "UTC"

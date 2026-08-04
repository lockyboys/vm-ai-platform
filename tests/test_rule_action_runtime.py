"""RuleActionRuntime selected-action execution tests."""

from __future__ import annotations

from unittest.mock import Mock

from engine.runtime.rule_action_runtime import RuleActionRuntime


def test_execute_action_dispatches_only_the_selected_rule_action() -> None:
    repository = Mock()
    repository.get_active_action.return_value = {
        "rule_action_id": "ACTION_SELECTED",
        "action_type_code": "OBJECT_LEVEL_CLASSIFICATION",
        "action_type_group_code": "ACTION_TYPE",
        "verified_query_id": "VERIFIED_QUERY_SELECTED",
    }
    dispatcher = Mock()
    dispatcher.dispatch.return_value = {
        "verified_query_id": "VERIFIED_QUERY_SELECTED",
        "result": [{"default_object_level": 4}],
    }
    runtime = RuleActionRuntime(repository, dispatcher)
    parameters = {
        "object_code": "DOCUMENT",
        "rule_id": "UNTRUSTED_RULE",
        "rule_action_id": "UNTRUSTED_ACTION",
        "action_type_code": "UNTRUSTED_ACTION_TYPE",
    }

    result = runtime.execute_action(
        "RULE_OBJECT_LEVEL",
        "ACTION_SELECTED",
        parameters,
    )

    repository.get_active_action.assert_called_once_with(
        "RULE_OBJECT_LEVEL",
        "ACTION_SELECTED",
    )
    dispatcher.dispatch.assert_called_once_with(
        "VERIFIED_QUERY_SELECTED",
        {
            "object_code": "DOCUMENT",
            "rule_id": "RULE_OBJECT_LEVEL",
            "rule_action_id": "ACTION_SELECTED",
            "action_type_code": "OBJECT_LEVEL_CLASSIFICATION",
            "action_type_group_code": "ACTION_TYPE",
        },
    )
    assert result == {
        "rule_action_id": "ACTION_SELECTED",
        "action_type_code": "OBJECT_LEVEL_CLASSIFICATION",
        "verified_query_id": "VERIFIED_QUERY_SELECTED",
        "result": {
            "verified_query_id": "VERIFIED_QUERY_SELECTED",
            "result": [{"default_object_level": 4}],
        },
    }

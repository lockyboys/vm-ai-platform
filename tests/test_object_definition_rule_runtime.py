"""Object Definition Rule Runtime regression tests."""

from __future__ import annotations

from unittest.mock import Mock

from engine.core import ExecutionContext
from engine.object_definition.engine import ObjectDefinitionEngine


def test_object_definition_persists_rule_resolved_object_level() -> None:
    database = Mock()
    engine = ObjectDefinitionEngine(database)
    coordinator = Mock()
    coordinator.prepare.return_value = {
        "object_level": 4,
    }
    engine.identifier_coordinator = coordinator
    context = ExecutionContext(
        request={
            "object_code": "WORK_SESSION",
            "object_level": 3,
        }
    )

    engine.pre_execute(context)

    coordinator.prepare.assert_called_once_with(request=context.request)
    assert context.request["object_level"] == 4
    assert context.shared["identifier_prepared"] == {"object_level": 4}
    assert context.shared["identifier_lock_acquired"] is True
    coordinator.acquire.assert_called_once_with({"object_level": 4})

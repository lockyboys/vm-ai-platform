"""Object Definition Rule Runtime regression tests."""

from __future__ import annotations

from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from engine.core import ExecutionContext
from engine.object_definition.engine import ObjectDefinitionEngine
from engine.object_definition.request_processor import ObjectDefinitionRequestProcessor
from engine.object_definition_engine import ObjectDefinitionEngine as LegacyObjectDefinitionEngine


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


@pytest.fixture(autouse=True)
def _deny_live_database_connections(monkeypatch):
    """회귀 테스트는 실제 MariaDB·MongoDB에 접속하지 않는다."""
    def deny_connection(*args, **kwargs):
        raise AssertionError("Live database access is forbidden in C1 unit tests.")

    monkeypatch.setattr("common.database.pymysql.connect", deny_connection)
    monkeypatch.setattr("common.database.MongoClient", deny_connection)


def _request(**overrides):
    request = {
        "object_code": "WORK_SESSION",
        "object_name": "Work Session",
        "business_code": "SP",
        "domain_code": "RP",
        "object_type_code": "TABLE",
        "identifier_target_code": "OB",
        "sequence_scope_code": "DAILY",
        "sequence_length": 5,
        "created_by": "ACTOR_C1",
        "updated_by": "ACTOR_C1",
        "program_id": "C1_TEST",
        "client_ip": "192.0.2.1",
    }
    request.update(overrides)
    return request


def _engine(engine_class=ObjectDefinitionEngine, *, existing=None):
    database = Mock()
    database.execute.return_value = 1
    engine = engine_class(database)
    engine.repository_resolver = Mock()
    saved = {"object_id": "OBJECT_TEST", "object_code": "WORK_SESSION"}
    engine.repository_resolver.find_existing.side_effect = (
        [existing] if existing else [None, None, saved]
    )
    coordinator = Mock()
    rule = SimpleNamespace(
        rule_id="RULE_TEST",
        rule_code="RL_TEST",
        rule_action_id="ACTION_TEST",
        action_type_code="LEVEL_TEST",
        object_level=4,
        resolution_source="DEFAULT",
    )
    coordinator.prepare.return_value = {
        "object_level": 4,
        "rule_resolution": rule,
        "blueprint": {"blueprint_code": "BLUEPRINT_TEST"},
        "sequence_date": "20260912",
        "sequence_length": 5,
        "now": datetime(2026, 9, 12, tzinfo=timezone.utc),
        "lock_name": "LOCK_TEST",
    }
    coordinator.resolve.return_value = SimpleNamespace(
        identifier="OBJECT_TEST",
        sequence_date="20260912",
        sequence_no=1,
        sequence_length=5,
        blueprint_code="BLUEPRINT_TEST",
        rule_id=rule.rule_id,
        rule_code=rule.rule_code,
        rule_action_id=rule.rule_action_id,
        rule_action_type_code=rule.action_type_code,
        object_level=rule.object_level,
        resolution_source=rule.resolution_source,
    )
    engine.identifier_coordinator = coordinator
    return engine, database, coordinator


def test_legacy_import_reexports_the_canonical_engine():
    from engine.object_definition import ObjectDefinitionEngine as PackageEngine

    assert LegacyObjectDefinitionEngine is ObjectDefinitionEngine
    assert PackageEngine is ObjectDefinitionEngine


@pytest.mark.parametrize("engine_class", [ObjectDefinitionEngine, LegacyObjectDefinitionEngine])
def test_create_uses_shared_generator_and_preserves_legacy_response(engine_class):
    engine, database, coordinator = _engine(engine_class)
    request = _request(object_level=3)
    result = engine.create(request)

    assert result["status"] == "CREATED"
    assert result["success"] is True
    assert result["affected_rows"] == 1
    assert result["object_id"] == "OBJECT_TEST"
    assert result["object"]["object_id"] == "OBJECT_TEST"
    assert result["identifier_target_code"] == "OB"
    assert result["object_level"] == 4
    assert result["rule_id"] == "RULE_TEST"
    assert request["object_level"] == 3
    assert "version_num" not in request
    database.begin.assert_called_once()
    database.commit.assert_called_once()
    database.rollback.assert_not_called()
    coordinator.resolve.assert_called_once()
    coordinator.release.assert_called_once()
    sql, params = database.execute.call_args.args
    assert "INSERT INTO sp_object" in sql
    assert params[8] == 4
    assert params[12] == "v1.0"
    assert params[14:18] == ("ACTOR_C1", "ACTOR_C1", "192.0.2.1", "C1_TEST")


def test_create_existing_preserves_sequence_preparation_without_allocating():
    existing = {"object_id": "EXISTING_TEST", "object_code": "WORK_SESSION"}
    engine, database, coordinator = _engine(existing=existing)

    result = engine.create(_request())

    assert result["status"] == "ALREADY_EXISTS"
    assert result["success"] is False
    assert result["affected_rows"] == 0
    assert result["object"] == existing
    assert result["rule_id"] == "RULE_TEST"
    coordinator.sequence_allocator.ensure_sequence.assert_called_once()
    prepared_request = coordinator.sequence_allocator.ensure_sequence.call_args.kwargs["request"]
    assert prepared_request["object_level"] == 4
    coordinator.resolve.assert_not_called()
    coordinator.reserve.assert_not_called()
    coordinator.sequence_allocator.allocate.assert_not_called()
    database.execute.assert_not_called()
    database.commit.assert_called_once()
    database.rollback.assert_not_called()
    coordinator.release.assert_called_once()


@pytest.mark.parametrize("existing", [None, {"object_id": "EXISTING_TEST"}])
def test_create_commit_failure_is_propagated_and_lock_is_released(existing):
    engine, database, coordinator = _engine(existing=existing)
    database.commit.side_effect = RuntimeError("commit failed")

    with pytest.raises(RuntimeError, match="commit failed"):
        engine.create(_request())

    database.rollback.assert_called_once()
    coordinator.release.assert_called_once()


def test_existing_sequence_preparation_failure_rolls_back_and_releases_lock():
    engine, database, coordinator = _engine(existing={"object_id": "EXISTING_TEST"})
    coordinator.sequence_allocator.ensure_sequence.side_effect = RuntimeError("sequence failed")

    with pytest.raises(RuntimeError, match="sequence failed"):
        engine.create(_request())

    database.commit.assert_not_called()
    database.rollback.assert_called_once()
    coordinator.release.assert_called_once()
    coordinator.sequence_allocator.allocate.assert_not_called()


def test_sequence_compatibility_method_only_delegates_to_shared_allocator():
    engine, database, coordinator = _engine()
    request = _request()
    blueprint = {"blueprint_code": "BLUEPRINT_TEST"}
    now = datetime(2026, 9, 12, tzinfo=timezone.utc)
    expected = {"identifier_sequence_id": "SEQUENCE_TEST"}
    coordinator.sequence_allocator.ensure_sequence.return_value = expected

    result = engine._ensure_sequence_metadata(request, blueprint, "20260912", 5, now)

    assert result is expected
    coordinator.sequence_allocator.ensure_sequence.assert_called_once_with(
        request=request,
        blueprint=blueprint,
        sequence_date="20260912",
        sequence_length=5,
        now=now,
    )
    database.begin.assert_not_called()
    database.commit.assert_not_called()
    database.execute.assert_not_called()


@pytest.mark.parametrize(
    ("values", "expected"),
    [({}, "v1.0"), ({"version_no": "v2.0"}, "v2.0"), ({"version_num": "v3.0"}, "v3.0")],
)
def test_normalization_uses_the_generator_version_column(values, expected):
    normalized = ObjectDefinitionRequestProcessor().normalize(_request(**values))
    assert normalized["version_num"] == expected
    assert "version_no" not in normalized


def test_conflicting_version_aliases_are_rejected():
    with pytest.raises(ValueError, match="version"):
        ObjectDefinitionRequestProcessor().normalize(
            _request(version_no="v1.0", version_num="v2.0")
        )


@pytest.mark.parametrize("declared_level", [None, "", 5])
def test_level_input_does_not_preempt_repository_rule_resolution(declared_level):
    processor = ObjectDefinitionRequestProcessor()
    normalized = processor.normalize(_request(object_level=declared_level))
    processor.validate(normalized)
    if declared_level in (None, ""):
        assert "object_level" not in normalized
    else:
        assert normalized["object_level"] == declared_level


def test_negative_level_is_rejected_before_repository_access():
    processor = ObjectDefinitionRequestProcessor()
    with pytest.raises(ValueError, match="object_level"):
        processor.validate(processor.normalize(_request(object_level=-1)))

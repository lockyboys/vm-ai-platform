"""IdentifierCoordinator Rule Runtime integration tests."""

from __future__ import annotations

from datetime import datetime
from unittest.mock import Mock, patch

from engine.common.identifier_rule_resolver import IdentifierRuleResolution
from engine.identifier.coordinator import IdentifierCoordinator


def _resolution(
    *,
    object_level: int,
    source: str,
) -> IdentifierRuleResolution:
    return IdentifierRuleResolution(
        rule_id="RULE_OBJECT_LEVEL",
        rule_code="RL_OBJECT_LEVEL_CLASSIFICATION",
        rule_action_id="ACTION_OBJECT_LEVEL",
        action_type_code="OBJECT_LEVEL_CLASSIFICATION",
        object_level=object_level,
        resolution_source=source,
    )


def _registered_object_metadata(
    *,
    object_level: int | None = 3,
) -> dict[str, object]:
    metadata: dict[str, object] = {
        "object_code": "WORK_SESSION",
        "business_code": "SP",
        "domain_code": "RP",
        "identifier_target_code": "OB",
        "sequence_scope_code": "DAILY",
        "sequence_length": 5,
    }
    if object_level is not None:
        metadata["object_level"] = object_level
    return metadata


def test_prepare_registered_object_uses_rule_resolver_not_declared_level() -> None:
    database = Mock()
    rule_resolver = Mock()
    rule_resolver.resolve_object_level.return_value = _resolution(
        object_level=4,
        source="EXPLICIT_RULE",
    )
    coordinator = IdentifierCoordinator(
        database,
        rule_resolver=rule_resolver,
    )
    blueprint = {
        "blueprint_code": "LEVEL4_NORMAL",
        "identifier_pattern": "{OBJECT}_{SEQ5}",
        "sequence_scope_code": "DAILY",
        "sequence_length": 5,
    }

    with (
        patch.object(
            coordinator.identifier_engine,
            "load_identifier_blueprint",
            return_value=blueprint,
        ) as load_blueprint,
        patch.object(
            coordinator.identifier_engine,
            "resolve_sequence_date",
            return_value="20260802",
        ),
    ):
        request, prepared = coordinator.prepare_registered_object(
            object_metadata=_registered_object_metadata(object_level=3),
            created_by="operator",
            updated_by="operator",
            client_ip="127.0.0.1",
            program_id="test_identifier",
            now=datetime(2026, 8, 2, 9, 0, 0),
        )

    rule_resolver.resolve_object_level.assert_called_once_with(request)
    load_blueprint.assert_called_once_with(4)
    assert prepared["object_level"] == 4
    assert prepared["rule_resolution"].rule_code == (
        "RL_OBJECT_LEVEL_CLASSIFICATION"
    )
    assert request["object_level"] == 3


def test_prepare_registered_object_allows_rule_default_when_metadata_level_absent() -> None:
    database = Mock()
    rule_resolver = Mock()
    rule_resolver.resolve_object_level.return_value = _resolution(
        object_level=4,
        source="DEFAULT",
    )
    coordinator = IdentifierCoordinator(
        database,
        rule_resolver=rule_resolver,
    )
    blueprint = {
        "blueprint_code": "LEVEL4_NORMAL",
        "identifier_pattern": "{OBJECT}_{SEQ5}",
        "sequence_scope_code": "DAILY",
        "sequence_length": 5,
    }

    with (
        patch.object(
            coordinator.identifier_engine,
            "load_identifier_blueprint",
            return_value=blueprint,
        ) as load_blueprint,
        patch.object(
            coordinator.identifier_engine,
            "resolve_sequence_date",
            return_value="20260802",
        ),
    ):
        request, prepared = coordinator.prepare_registered_object(
            object_metadata=_registered_object_metadata(object_level=None),
            created_by="operator",
            updated_by="operator",
            client_ip="127.0.0.1",
            program_id="test_identifier",
        )

    assert "object_level" not in request
    load_blueprint.assert_called_once_with(4)
    assert prepared["object_level"] == 4
    assert prepared["rule_resolution"].resolution_source == "DEFAULT"


def test_resolve_returns_rule_evidence_with_identifier() -> None:
    database = Mock()
    rule_resolver = Mock()
    coordinator = IdentifierCoordinator(
        database,
        rule_resolver=rule_resolver,
    )
    coordinator.sequence_allocator = Mock()
    coordinator.sequence_allocator.ensure_sequence.return_value = {
        "identifier_sequence_id": "IDENTIFIER_SEQUENCE",
    }
    coordinator.sequence_allocator.allocate.return_value = 9
    coordinator.identifier_engine.render_identifier = Mock(
        return_value="SP_RP_WORK_SESSION_20260802_00009"
    )
    rule_resolution = _resolution(
        object_level=3,
        source="EXPLICIT_RULE",
    )
    request = {
        **_registered_object_metadata(object_level=3),
        "updated_by": "operator",
        "program_id": "test_identifier",
    }
    prepared = {
        "now": datetime(2026, 8, 2, 9, 0, 0),
        "rule_resolution": rule_resolution,
        "object_level": 3,
        "blueprint": {
            "blueprint_code": "LEVEL3_DAY",
            "identifier_pattern": "{OBJECT}_{SEQ5}",
        },
        "sequence_length": 5,
        "sequence_date": "20260802",
        "lock_name": "SPS_IDENTIFIER:SP:RP:WORK_SESSION:20260802",
    }

    resolution = coordinator.resolve(request=request, prepared=prepared)

    assert resolution.identifier == "SP_RP_WORK_SESSION_20260802_00009"
    assert resolution.rule_id == "RULE_OBJECT_LEVEL"
    assert resolution.rule_action_id == "ACTION_OBJECT_LEVEL"
    assert resolution.object_level == 3
    assert resolution.resolution_source == "EXPLICIT_RULE"

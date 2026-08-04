"""Identifier Blueprint 공통코드 SSOT 회귀 테스트."""

from unittest.mock import MagicMock

from engine.identifier.coordinator import IdentifierCoordinator
from engine.identifier_engine import IdentifierEngine


def test_load_identifier_blueprint_reads_common_code_not_legacy_table():
    database = MagicMock()
    database.fetch_one.return_value = {
        "blueprint_code": "LEVEL4_NORMAL",
        "identifier_pattern": "{BUSINESS}_{DOMAIN}_{OBJECT}_{YYYYMMDD}_{HHMMSS}_{SEQ5}",
        "sequence_scope_code": "DAILY",
        "sequence_length": 5,
    }
    engine = IdentifierEngine(database)

    blueprint = engine.load_identifier_blueprint(4)

    sql, parameters = database.fetch_one.call_args.args
    assert "te_common.cm_common_code" in sql
    assert "sp_identifier_blueprint" not in sql
    assert parameters == (4,)
    assert blueprint["blueprint_code"] == "LEVEL4_NORMAL"


def test_prepare_registered_object_uses_existing_metadata_without_creation() -> None:
    coordinator = IdentifierCoordinator.__new__(IdentifierCoordinator)
    coordinator.prepare = MagicMock(return_value={"lock_name": "SPS_IDENTIFIER:SP:RP:WORK:20260802"})

    request, prepared = coordinator.prepare_registered_object(
        object_metadata={
            "object_code": "WORK_SESSION",
            "business_code": "SP",
            "domain_code": "RP",
            "object_level": "3",
            "identifier_target_code": "OB",
            "sequence_scope_code": "DAILY",
            "sequence_length": "5",
        },
        created_by="operator",
        updated_by="operator",
        client_ip="127.0.0.1",
        program_id="test_identifier",
    )

    assert request == {
        "object_code": "WORK_SESSION",
        "business_code": "SP",
        "domain_code": "RP",
        "object_level": 3,
        "identifier_target_code": "OB",
        "sequence_scope_code": "DAILY",
        "sequence_length": 5,
        "created_by": "operator",
        "updated_by": "operator",
        "client_ip": "127.0.0.1",
        "program_id": "test_identifier",
    }
    assert prepared == {"lock_name": "SPS_IDENTIFIER:SP:RP:WORK:20260802"}
    coordinator.prepare.assert_called_once_with(request=request, now=None)

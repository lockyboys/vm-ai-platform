from __future__ import annotations

from unittest import TestCase

from tools.register_repository_identifier_objects import build_requests


class _CommonDatabase:
    def __init__(self) -> None:
        self.calls: list[tuple[str, str]] = []

    def fetch_one(self, _query: str, parameters: tuple[str, str]) -> dict[str, str]:
        group_code, code = parameters
        self.calls.append((group_code, code))
        return {"code": code}


def _contract() -> dict[str, object]:
    return {
        "identifier_object_codes": {
            "table": "TABLE",
            "entity": "ENTITY",
            "attribute": "ATTRIBUTE",
            "erd": "ERD",
            "relationship": "RELATIONSHIP",
        },
        "identifier_object_definitions": {
            "table": {"identifier_target_code": "OB", "object_level": 3},
            "entity": {"identifier_target_code": "EN", "object_level": 3},
            "attribute": {"identifier_target_code": "AT", "object_level": 4},
            "erd": {"identifier_target_code": "OB", "object_level": 2},
            "relationship": {"identifier_target_code": "RE", "object_level": 3},
        },
        "object_definition_business_code": "SP",
        "object_definition_domain_code": "RP",
        "object_type_code": "TABLE",
        "sequence_scope_code": "DAILY",
        "sequence_length": 5,
    }


class RegisterRepositoryIdentifierObjectsTest(TestCase):
    def test_build_requests_uses_definition_specific_object_levels(self) -> None:
        requests = build_requests(_CommonDatabase(), _contract())

        levels_by_code = {request["object_code"]: request["object_level"] for request in requests}

        self.assertEqual(levels_by_code["ERD"], 2)
        self.assertEqual(levels_by_code["TABLE"], 3)
        self.assertEqual(levels_by_code["ENTITY"], 3)
        self.assertEqual(levels_by_code["RELATIONSHIP"], 3)
        self.assertEqual(levels_by_code["ATTRIBUTE"], 4)

    def test_build_requests_rejects_missing_definition_object_level(self) -> None:
        contract = _contract()
        definitions = contract["identifier_object_definitions"]
        assert isinstance(definitions, dict)
        erd_definition = definitions["erd"]
        assert isinstance(erd_definition, dict)
        erd_definition.pop("object_level")

        with self.assertRaisesRegex(
            ValueError,
            r"bucket=erd, missing=\['object_level'\]",
        ):
            build_requests(_CommonDatabase(), contract)

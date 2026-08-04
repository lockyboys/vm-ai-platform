"""Canonical SPS IdentifierEngine unit tests."""

from __future__ import annotations

from datetime import datetime
from unittest import TestCase
from unittest.mock import Mock, patch

from engine.common.identifier_rule_resolver import IdentifierRuleResolution
from engine.identifier_engine import IdentifierEngine


class IdentifierEngineTest(TestCase):
    def setUp(self) -> None:
        self.database = Mock()
        self.rule_resolver = Mock()
        self.engine = IdentifierEngine(
            self.database,
            rule_resolver=self.rule_resolver,
        )

    @staticmethod
    def _resolution(object_level: int) -> IdentifierRuleResolution:
        return IdentifierRuleResolution(
            rule_id="RULE_OBJECT_LEVEL",
            rule_code="RL_OBJECT_LEVEL_CLASSIFICATION",
            rule_action_id="ACTION_OBJECT_LEVEL",
            action_type_code="OBJECT_LEVEL_CLASSIFICATION",
            object_level=object_level,
            resolution_source="EXPLICIT_RULE",
        )

    def test_generate_uses_rule_resolved_object_level(self) -> None:
        metadata = {"object_code": "TABLE", "object_level": 3}
        self.rule_resolver.resolve_object_level.return_value = self._resolution(4)

        with (
            patch.object(
                self.engine,
                "load_object_metadata",
                return_value=metadata,
            ),
            patch.object(
                self.engine,
                "_generate_from_metadata",
                return_value="SP_RP_TABLE_20260728_00001",
            ) as generate_from_metadata,
        ):
            result = self.engine.generate(
                "TABLE",
                manage_transaction=False,
            )

        self.assertEqual(result, "SP_RP_TABLE_20260728_00001")
        self.rule_resolver.resolve_object_level.assert_called_once_with(metadata)
        generate_from_metadata.assert_called_once_with(
            object_metadata=metadata,
            object_level=4,
            manage_transaction=False,
        )

    def test_generate_for_level_rejects_rule_resolver_bypass(self) -> None:
        metadata = {"object_code": "RELATIONSHIP", "object_level": 3}
        self.rule_resolver.resolve_object_level.return_value = self._resolution(4)

        with (
            patch.object(
                self.engine,
                "load_object_metadata",
                return_value=metadata,
            ),
            patch.object(self.engine, "_generate_from_metadata") as generate,
            self.assertRaisesRegex(
                ValueError,
                "conflicts with Rule Resolver",
            ),
        ):
            self.engine.generate_for_level(
                object_code="RELATIONSHIP",
                object_level=3,
                manage_transaction=False,
            )

        generate.assert_not_called()

    def test_generate_for_level_uses_rule_resolved_sequence_contract(self) -> None:
        generated_dt = datetime(2026, 7, 28, 9, 30, 15, 123000)
        metadata = {
            "business_code": "SP",
            "domain_code": "RP",
            "object_code": "RELATIONSHIP",
            "object_level": 3,
            "identifier_target_code": "RE",
            "sequence_scope_code": "DAILY",
            "sequence_length": 5,
        }
        blueprint = {
            "blueprint_code": "LEVEL3_DAY",
            "identifier_pattern": "{BUSINESS}_{DOMAIN}_{OBJECT}_{YYYYMMDD}_{SEQ5}",
            "sequence_scope_code": "DAILY",
            "sequence_length": 5,
        }
        self.rule_resolver.resolve_object_level.return_value = self._resolution(3)

        with (
            patch.object(
                self.engine,
                "load_object_metadata",
                return_value=metadata,
            ),
            patch.object(
                self.engine,
                "load_identifier_blueprint",
                return_value=blueprint,
            ),
            patch.object(
                self.engine,
                "allocate_sequence",
                return_value=7,
            ) as allocate,
        ):
            result = self.engine.generate_for_level(
                object_code="RELATIONSHIP",
                object_level=3,
                now=generated_dt,
                manage_transaction=False,
            )

        self.assertEqual(result, "SP_RP_RELATIONSHIP_20260728_00007")
        allocate.assert_called_once_with(
            identifier_target_code="RE",
            identifier_prefix="RELATIONSHIP",
            sequence_date="20260728",
            sequence_length=5,
            manage_transaction=False,
        )

    def test_missing_sequence_length_fails_without_hardcoded_default(self) -> None:
        metadata = {
            "business_code": "SP",
            "domain_code": "RP",
            "object_code": "RELATIONSHIP",
            "identifier_target_code": "RE",
            "sequence_scope_code": "DAILY",
        }
        blueprint = {
            "blueprint_code": "LEVEL3_DAY",
            "identifier_pattern": "{BUSINESS}_{DOMAIN}_{OBJECT}_{YYYYMMDD}_{SEQ5}",
            "sequence_scope_code": "DAILY",
        }

        with (
            patch.object(
                self.engine,
                "load_identifier_blueprint",
                return_value=blueprint,
            ),
            patch.object(self.engine, "allocate_sequence") as allocate,
            self.assertRaisesRegex(
                ValueError,
                "sequence length is required",
            ),
        ):
            self.engine._generate_from_metadata(
                object_metadata=metadata,
                object_level=3,
                manage_transaction=False,
            )

        allocate.assert_not_called()

    def test_missing_sequence_metadata_fails_without_bootstrap(self) -> None:
        self.database.fetch_one.return_value = None

        with self.assertRaisesRegex(
            ValueError,
            "Identifier Sequence metadata not found",
        ):
            self.engine.allocate_sequence(
                identifier_target_code="RE",
                identifier_prefix="RELATIONSHIP",
                sequence_date="20260728",
                sequence_length=5,
                manage_transaction=False,
            )

        self.database.execute.assert_not_called()


if __name__ == "__main__":
    import unittest

    unittest.main()

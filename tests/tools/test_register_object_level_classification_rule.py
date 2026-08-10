from __future__ import annotations

from unittest import TestCase

from tools.register_object_level_classification_rule import RULE_DEFINITION


class ObjectLevelClassificationRuleTest(TestCase):
    def test_rule_separates_object_id_default_from_table_id(self) -> None:
        self.assertIn("기본 Level은 3", str(RULE_DEFINITION["rule_description"]))
        self.assertIn("Table ID", str(RULE_DEFINITION["rule_description"]))
        self.assertEqual(
            RULE_DEFINITION["remark"],
            "DEFAULT_OBJECT_ID_LEVEL=3; EXPLICIT_TABLE_ID_LEVEL=4; EXPLICIT_CONDITION_FIRST",
        )

from __future__ import annotations

from unittest import TestCase

from tools.register_object_level_classification_rule import RULE_DEFINITION


class ObjectLevelClassificationRuleTest(TestCase):
    def test_rule_declares_level_four_for_unregistered_objects(self) -> None:
        self.assertIn("기본 Level은 4", str(RULE_DEFINITION["rule_description"]))
        self.assertEqual(
            RULE_DEFINITION["remark"],
            "DEFAULT_OBJECT_LEVEL=4; Rule 등록값이 있으면 해당 값을 우선한다.",
        )

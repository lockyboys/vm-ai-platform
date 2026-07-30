import json
import unittest

from tools.register_object_level_classification_rule_action import build_action_value


class ObjectLevelClassificationRuleActionTest(unittest.TestCase):
    def test_action_contract_uses_issued_verified_query_id(self):
        contract = json.loads(build_action_value("issued-query-id"))

        self.assertEqual("issued-query-id", contract["verified_query_id"])
        self.assertEqual(4, contract["default_object_level"])
        self.assertEqual(["EXPLICIT_RULE", "DEFAULT"], contract["resolution_order"])


if __name__ == "__main__":
    unittest.main()

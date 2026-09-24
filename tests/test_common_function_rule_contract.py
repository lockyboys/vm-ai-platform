from common.common_function import load_rule_common_code_contract


class _Database:
    def fetch_all(self, sql, params):
        assert "ORDER BY a.sort_no, a.rule_action_id" in sql
        assert "LIMIT 1" not in sql
        assert params == ("RULE_MULTI",)
        return [
            {
                "rule_id": "R1",
                "rule_code": "RULE_MULTI",
                "rule_action_id": "A1",
                "action_type_code": "EXPLICIT_RULE",
                "common_code_json": '{"identifier_object_codes": {"table": "TABLE"}}',
            },
            {
                "rule_id": "R1",
                "rule_code": "RULE_MULTI",
                "rule_action_id": "A2",
                "action_type_code": "DEFAULT",
                "common_code_json": '{"default_object_level": 4}',
            },
        ]


def test_load_rule_common_code_contract_keeps_all_active_actions():
    contract = load_rule_common_code_contract(_Database(), "RULE_MULTI")

    assert contract["rule_action_id"] == "A1"
    assert [action["rule_action_id"] for action in contract["actions"]] == ["A1", "A2"]
    assert contract["actions"][1]["default_object_level"] == 4

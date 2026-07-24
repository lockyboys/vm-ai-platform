"""Repository access for active Rule Action contracts."""

import json


class RuleActionRepository:
    def __init__(self, database):
        self.database = database

    def get_active_actions(self, rule_id):
        sql = """
            SELECT rule_action_id, action_type_code, action_value, sort_no
            FROM rl_rule_action
            WHERE rule_id = %s
              AND status_code = 'ACTIVE'
              AND deleted_dt IS NULL
            ORDER BY sort_no, rule_action_id
        """
        rows = self.database.fetch_all(sql, (rule_id,))
        return [self._to_contract(row) for row in rows]

    @staticmethod
    def _to_contract(row):
        action_value = row.get("action_value")
        try:
            contract = json.loads(action_value)
        except (TypeError, json.JSONDecodeError) as exc:
            raise ValueError(
                f"Rule Action contract must be JSON: {row['rule_action_id']}"
            ) from exc

        verified_query_id = contract.get("verified_query_id")
        if not verified_query_id:
            raise ValueError(
                f"Rule Action contract requires verified_query_id: {row['rule_action_id']}"
            )

        return {
            "rule_action_id": row["rule_action_id"],
            "action_type_code": row["action_type_code"],
            "verified_query_id": verified_query_id,
        }

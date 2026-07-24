"""Repository access for Action Metadata and Verified Query contracts."""

import json

from common.database import CommonDatabase


class ActionMetadataRepository:
    def __init__(self, database=None):
        self.database = database or CommonDatabase("COMMON")

    def get_action_metadata(self, action_code):
        row = self.database.fetch_one(
            """
            SELECT code AS action_code, code_name AS action_name, common_code_json
            FROM cm_common_code
            WHERE group_code = %s
              AND code = %s
              AND status_code = %s
              AND deleted_dt IS NULL
            """,
            ("ACTION_TYPE", action_code, "ACTIVE"),
        )
        if not row:
            raise LookupError(f"Active Action Metadata not found: {action_code}")

        metadata = self._load_json(row["common_code_json"], "Action Metadata")
        metadata["action_code"] = row["action_code"]
        metadata["action_name"] = row["action_name"]
        if metadata.get("active_yn") != "Y":
            raise LookupError(f"Inactive Action Metadata: {action_code}")
        if not metadata.get("verified_query_id"):
            raise ValueError(f"verified_query_id is required: {action_code}")
        return metadata

    def get_verified_query(self, verified_query_id):
        row = self.database.fetch_one(
            """
            SELECT query_id, query_name, query_description, sql_text
            FROM cm_verified_sql_query
            WHERE query_id = %s
              AND verified_yn = %s
              AND status_code = %s
              AND deleted_dt IS NULL
            """,
            (verified_query_id, "Y", "ACTIVE"),
        )
        if not row:
            raise LookupError(f"Active Verified Query not found: {verified_query_id}")

        contract = self._load_json(row["query_description"], "Verified Query contract")
        contract["verified_query_id"] = row["query_id"]
        contract["query_name"] = row["query_name"]
        if not contract.get("procedure_name"):
            raise ValueError(f"procedure_name is required: {verified_query_id}")
        return contract

    def resolve_execution_contract(self, action_code):
        action = self.get_action_metadata(action_code)
        query = self.get_verified_query(action["verified_query_id"])
        if action.get("procedure_name") != query.get("procedure_name"):
            raise ValueError("Action Metadata and Verified Query procedure_name mismatch.")
        return {"action_metadata": action, "verified_query": query}

    @staticmethod
    def _load_json(value, label):
        try:
            return json.loads(value)
        except (TypeError, json.JSONDecodeError) as exc:
            raise ValueError(f"{label} must be valid JSON.") from exc

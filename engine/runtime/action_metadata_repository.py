"""Verified Query contract reader for Action Metadata Runtime.

The Rule Engine resolves Action Metadata and supplies verified_query_id.  This
module deliberately contains no physical table, status, group-code, or SQL
knowledge; repository access is injected by the composition root.
"""

import json


class ActionMetadataRepository:
    def __init__(self, verified_query_reader):
        self.verified_query_reader = verified_query_reader

    def get_verified_query(self, verified_query_id):
        row = self.verified_query_reader.get_verified_query(verified_query_id)
        if not row:
            raise LookupError(f"Verified Query not found: {verified_query_id}")

        contract = self._load_json(row["query_description"], "Verified Query contract")
        contract["verified_query_id"] = row["query_id"]
        contract["query_name"] = row["query_name"]
        if not contract.get("procedure_name"):
            raise ValueError(f"procedure_name is required: {verified_query_id}")
        return contract

    @staticmethod
    def _load_json(value, label):
        try:
            return json.loads(value)
        except (TypeError, json.JSONDecodeError) as exc:
            raise ValueError(f"{label} must be valid JSON.") from exc

"""Repository access for verified Stored Procedure execution contracts."""

import json


class VerifiedSqlQueryRepository:
    def __init__(self, database):
        self.database = database

    def get_verified_query(self, query_id):
        sql = """
            SELECT query_id, query_description
            FROM cm_verified_sql_query
            WHERE query_id = %s
              AND verified_yn = 'Y'
              AND status_code = 'ACTIVE'
              AND deleted_dt IS NULL
        """
        row = self.database.fetch_one(sql, (query_id,))
        if not row:
            raise LookupError(f"Active verified query not found: {query_id}")

        try:
            contract = json.loads(row["query_description"])
        except (TypeError, json.JSONDecodeError) as exc:
            raise ValueError(
                f"Verified query execution contract must be JSON: {query_id}"
            ) from exc

        contract["query_id"] = row["query_id"]
        return contract

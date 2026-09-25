"""Repository access for active verified SQL Query records."""


import json


class VerifiedSqlQueryRepository:
    def __init__(self, database):
        self.database = database

    def get_verified_query(self, query_id):
        sql = """
            SELECT query_id, query_name, crud_type, certified_level_code
            FROM cm_verified_sql_query
            WHERE query_id = %s
              AND verified_yn = 'Y'
              AND status_code = 'ACTIVE'
              AND deleted_dt IS NULL
        """
        row = self.database.fetch_one(sql, (query_id,))
        if not row:
            raise LookupError(f"Active verified query not found: {query_id}")

        payload_document = self.database.find_one(
            collection_name="verified_sql_payload",
            filter_document={
                "_sps.source_table_name": "cm_verified_sql_query",
                "_sps.source_identifier": row["query_id"],
            },
        )
        payload = (
            payload_document.get("payload", {}).get("verified_sql_payload")
            if isinstance(payload_document, dict)
            else None
        )
        if not isinstance(payload, dict):
            raise LookupError(f"Verified SQL payload not found: {query_id}")
        query_description = payload.get("query_description")
        if isinstance(query_description, dict):
            query_description = json.dumps(query_description, ensure_ascii=False)
        if not str(query_description or "").strip():
            raise ValueError(f"Verified Query contract is empty: {query_id}")
        row["query_description"] = query_description
        return row

"""Repository access for active verified SQL Query records."""


class VerifiedSqlQueryRepository:
    def __init__(self, database):
        self.database = database

    def get_verified_query(self, query_id):
        sql = """
            SELECT query_id, query_name, query_description
            FROM cm_verified_sql_query
            WHERE query_id = %s
              AND verified_yn = 'Y'
              AND status_code = 'ACTIVE'
              AND deleted_dt IS NULL
        """
        row = self.database.fetch_one(sql, (query_id,))
        if not row:
            raise LookupError(f"Active verified query not found: {query_id}")
        return row

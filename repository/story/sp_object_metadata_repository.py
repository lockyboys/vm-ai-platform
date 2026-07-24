"""Repository access for active Story Object execution metadata."""


class SpObjectMetadataRepository:
    def __init__(self, database):
        self.database = database

    def get_active_by_code(self, object_code):
        sql = """
            SELECT
                object_id,
                object_code,
                object_name,
                business_code,
                domain_code,
                object_type_code,
                object_level,
                sequence_scope_code,
                sequence_length,
                identifier_target_code
            FROM sp_object
            WHERE object_code = %s
              AND active_yn = 'Y'
              AND status_code = 'ACTIVE'
              AND deleted_dt IS NULL
            LIMIT 1
        """
        row = self.database.fetch_one(sql, (object_code,))
        if not row:
            raise LookupError(f"Active Object metadata not found: {object_code}")
        return row

import os
import mysql.connector
from dotenv import load_dotenv


class ExecutionHistoryGenerator:
    """
    Execution History Generator

    STEP-011
    sp_execution_history 실제 저장.
    """

    def __init__(self):
        load_dotenv()

        self.db_config = {
            "host": os.getenv("STORY_PLATFORM_MARIADB_HOST", "127.0.0.1"),
            "port": int(os.getenv("STORY_PLATFORM_MARIADB_PORT", "3306")),
            "user": os.getenv("STORY_PLATFORM_MARIADB_USER"),
            "password": os.getenv("STORY_PLATFORM_MARIADB_PASSWORD"),
            "database": os.getenv("STORY_PLATFORM_MARIADB_DATABASE", "te_story_platform"),
        }

    def load_identity_metadata(self, database):
        """Load the Repository-managed identity metadata for this table."""
        row = database.fetch_one(
            """
            SELECT
                object_id,
                object_code,
                object_name,
                business_code,
                domain_code,
                object_type_code,
                object_level,
                identifier_target_code,
                sequence_scope_code,
                sequence_length
            FROM sp_object
            WHERE target_identifier_field = %s
              AND object_type_code = 'TABLE'
              AND active_yn = 'Y'
              AND status_code = 'ACTIVE'
              AND deleted_dt IS NULL
            ORDER BY sort_no, object_code
            LIMIT 1
            """,
            ("execution_history_id",),
        )

        if not row:
            raise ValueError(
                "Execution-history identifier metadata not found. "
                "Register the sp_execution_history Table Object first."
            )

        return row

    def save(self, execution_history_request, database):
        sql = """
            INSERT INTO sp_execution_history (
                execution_history_id,
                trace_id,
                engine_code,
                object_code,
                object_id,
                generated_identifier,
                repository_status_code,
                mongodb_status_code,
                execution_status_code,
                history_status_code,
                created_dt
            )
            VALUES (
                %s, %s, %s, %s, %s, %s,
                %s, %s, %s, %s,
                NOW()
            )
        """

        params = (
            execution_history_request["execution_history_id"],
            execution_history_request["trace_id"],
            execution_history_request["engine_code"],
            execution_history_request["object_code"],
            execution_history_request.get("object_id"),
            execution_history_request.get("generated_identifier"),
            execution_history_request.get("repository_status_code"),
            execution_history_request.get("mongodb_status_code"),
            execution_history_request["execution_status_code"],
            "SAVED",
        )

        database.execute(sql, params)

        return {
            "generator": "ExecutionHistoryGenerator",
            "execution_history_id": execution_history_request["execution_history_id"],
            "status": "SUCCESS",
        }

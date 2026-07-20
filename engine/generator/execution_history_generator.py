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

    def save(self, execution_history_request, database):
        sql = """
            INSERT INTO sp_execution_history (
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
                %s, %s, %s, %s, %s,
                %s, %s, %s, %s,
                NOW()
            )
        """

        params = (
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
        execution_history_id = database.last_insert_id()

        return {
            "generator": "ExecutionHistoryGenerator",
            "execution_history_id": execution_history_id,
            "status": "SUCCESS",
        }

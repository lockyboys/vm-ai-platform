import os
import re
from typing import Dict, Optional

import pymysql
from dotenv import load_dotenv


DATABASE_OBJECT_NAME_PATTERN = re.compile(r"^[a-zA-Z0-9_]+$")


class DatabaseManager:
    """
    SPS Database Manager v1.0

    역할:
    - Bootstrap Repository 접속 정보만 .env에서 읽는다.
    - Database Role Code(COMMON, STORY, AI, HEALTH 등)를 실제 database_name으로 해석한다.
    - Engine은 물리 DB명을 직접 알지 않는다.
    - database.table 형태의 Qualified Table Name을 안전하게 생성한다.
    """

    DATABASE_ROLE_GROUP_CODE = "SPS_DATABASE_ROLE"

    def __init__(self):
        load_dotenv()

        self.bootstrap_config = {
            "host": os.getenv("SPS_REPOSITORY_HOST"),
            "port": int(os.getenv("SPS_REPOSITORY_PORT", "3306")),
            "user": os.getenv("SPS_REPOSITORY_USER"),
            "password": os.getenv("SPS_REPOSITORY_PASSWORD"),
            "database": os.getenv("SPS_REPOSITORY_BOOTSTRAP_DATABASE"),
            "charset": os.getenv("SPS_REPOSITORY_CHARSET", "utf8mb4"),
        }

        self._validate_bootstrap_config()
        self._database_name_cache: Dict[str, str] = {}

    def get_connection(self, database_role_code: str):
        database_name = self.get_database_name(database_role_code)

        return pymysql.connect(
            host=self.bootstrap_config["host"],
            port=self.bootstrap_config["port"],
            user=self.bootstrap_config["user"],
            password=self.bootstrap_config["password"],
            database=database_name,
            charset=self.bootstrap_config["charset"],
            autocommit=False,
            cursorclass=pymysql.cursors.DictCursor,
        )

    def list_active_database_roles(self) -> list[str]:
        """Return ACTIVE database role codes from the Repository SSOT."""

        with self._get_bootstrap_connection() as conn:
            with conn.cursor() as cursor:
                sql = """
                    SELECT code
                    FROM cm_common_code
                    WHERE group_code = %s
                      AND status_code = 'ACTIVE'
                    ORDER BY sort_no, code
                """
                cursor.execute(sql, (self.DATABASE_ROLE_GROUP_CODE,))
                rows = cursor.fetchall()

        roles = [
            self._normalize_role_code(row["code"])
            for row in rows
        ]

        if not roles:
            raise ValueError(
                "No ACTIVE database roles are registered in Repository metadata."
            )

        return roles

    def get_database_name(self, database_role_code: str) -> str:
        role_code = self._normalize_role_code(database_role_code)

        if role_code in self._database_name_cache:
            return self._database_name_cache[role_code]

        with self._get_bootstrap_connection() as conn:
            with conn.cursor() as cursor:
                sql = """
                    SELECT
                        code_name AS database_name
                    FROM cm_common_code
                    WHERE group_code = %s
                      AND code = %s
                      AND status_code = 'ACTIVE'
                    LIMIT 1
                """
                cursor.execute(sql, (self.DATABASE_ROLE_GROUP_CODE, role_code))
                row = cursor.fetchone()

        if not row:
            raise ValueError(f"Database role is not registered: {role_code}")

        database_name = self._validate_database_object_name(row["database_name"])
        self._database_name_cache[role_code] = database_name

        return database_name

    def get_qualified_table_name(self, database_role_code: str, table_name: str) -> str:
        database_name = self.get_database_name(database_role_code)
        safe_table_name = self._validate_database_object_name(table_name)

        return f"`{database_name}`.`{safe_table_name}`"

    def _get_bootstrap_connection(self):
        return pymysql.connect(
            host=self.bootstrap_config["host"],
            port=self.bootstrap_config["port"],
            user=self.bootstrap_config["user"],
            password=self.bootstrap_config["password"],
            database=self.bootstrap_config["database"],
            charset=self.bootstrap_config["charset"],
            autocommit=False,
            cursorclass=pymysql.cursors.DictCursor,
        )

    def _normalize_role_code(self, database_role_code: str) -> str:
        if not database_role_code:
            raise ValueError("database_role_code is required.")

        return database_role_code.upper().strip()

    def _validate_database_object_name(self, name: Optional[str]) -> str:
        if not name:
            raise ValueError("Database object name is required.")

        normalized_name = name.strip()

        if not DATABASE_OBJECT_NAME_PATTERN.match(normalized_name):
            raise ValueError(f"Invalid database object name: {normalized_name}")

        return normalized_name

    def _validate_bootstrap_config(self) -> None:
        required_keys = ["host", "port", "user", "password", "database"]

        for key in required_keys:
            if self.bootstrap_config.get(key) in (None, ""):
                raise ValueError(f"SPS repository bootstrap config is missing: {key}")
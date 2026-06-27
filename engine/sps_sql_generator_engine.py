# =============================================================================
# File Name   : sps_sql_generator_engine.py
# Purpose     : SPS SQL Generator Engine
# Author      : PARK HEAKYU
# Created     : 2026-06-27
# Updated     : 2026-06-27
# Description : SPS 표준 SQL을 자동 생성하는 엔진
# =============================================================================
# CHANGE HISTORY
# =============================================================================
# 20260627 | SYSTEM | SPS SQL Generator Engine을 CommonDatabase 기반으로 변경했고, 감사 필드 제외 SELECT를 지원했음
# =============================================================================
# ROADMAP
# =============================================================================
# 20260627 | SYSTEM | INSERT 생성, UPDATE 생성, ALTER 표준검사를 다음 단계로 정의했음
# =============================================================================


AUDIT_COLUMNS = {
    "created_dt",
    "created_by",
    "updated_dt",
    "updated_by",
    "deleted_dt",
    "deleted_by",
    "client_ip",
    "program_id",
}


class SpsSqlGeneratorEngine:
    # -------------------------------------------------------------------------
    # Story : SQL Generator Engine을 생성한다.
    # Input : database(CommonDatabase)
    # Output: SpsSqlGeneratorEngine instance
    # -------------------------------------------------------------------------
    def __init__(self, database):
        self.database = database

    # -------------------------------------------------------------------------
    # Story : 테이블의 컬럼 목록을 조회한다.
    # Input : table_name(str)
    # Output: list[str]
    # -------------------------------------------------------------------------
    def get_columns(self, table_name):
        sql = """
        SELECT column_name
        FROM information_schema.columns
        WHERE table_schema = %s
        AND table_name = %s
        ORDER BY ordinal_position
        """

        rows = self.database.fetch_all(
            sql,
            (self.database.database_name, table_name)
        )

        return [row["column_name"] for row in rows]

    # -------------------------------------------------------------------------
    # Story : 감사 컬럼을 제외한 SELECT SQL을 생성한다.
    # Input : table_name(str), where_text(str | None)
    # Output: str
    # -------------------------------------------------------------------------
    def generate_select_without_audit(self, table_name, where_text=None):
        columns = self.get_columns(table_name)

        selected_columns = [
            column for column in columns
            if column not in AUDIT_COLUMNS
        ]

        column_text = ",\n    ".join(selected_columns)

        sql = f"""SELECT
    {column_text}
FROM {table_name}
WHERE deleted_dt IS NULL"""

        if where_text:
            sql += f"\n  AND {where_text}"

        sql += ";"

        return sql

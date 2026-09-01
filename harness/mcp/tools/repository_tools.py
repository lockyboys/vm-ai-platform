# =============================================================================
# File Name   : harness/mcp/tools/repository_tools.py
# Purpose     : 데이터베이스 구조와 연결 관계를 읽기만 하는 확인 도구
# =============================================================================
# CHANGE HISTORY
# =============================================================================
# 20260902 | Codex | Harness 표준 파일 헤더와 Repository 검증 역할을 보강했음
# =============================================================================
# 이 파일은 무엇을 하나요?
# - 테이블의 칸 구성, 예시 데이터, 테이블 사이의 연결 관계를 보여 줍니다.
# - 실제 데이터베이스가 지금 어떤 상태인지 바꾸기 전에 확인할 때 사용합니다.
# 주의: 이 파일의 명령어는 데이터를 추가·수정·삭제하지 않습니다.
from __future__ import annotations

import re
from typing import Any

from core.database.database_manager import DatabaseManager


DEFAULT_DATABASE_ROLE = "STORY"

DEFAULT_LIMIT = 20
MAX_LIMIT = 100

VALID_IDENTIFIER_PATTERN = re.compile(
    r"^[A-Za-z_][A-Za-z0-9_]*$"
)


def _normalize_database_roles(
    database_roles: list[str] | None,
) -> list[str]:
    roles = (
        database_roles
        if database_roles
        else DatabaseManager().list_active_database_roles()
    )

    normalized_roles = [
        str(role).strip().upper()
        for role in roles
        if str(role).strip()
    ]

    if not normalized_roles:
        raise ValueError(
            "At least one database_role is required."
        )

    return list(dict.fromkeys(normalized_roles))


def _resolve_database_names(
    database_roles: list[str],
) -> dict[str, str]:
    database_names: dict[str, str] = {}
    database_manager = DatabaseManager()

    for database_role in database_roles:
        database_name = database_manager.get_database_name(
            database_role
        )
        database_names[database_name] = database_role

    return database_names


def _fetch_all(
    database_role: str,
    sql: str,
    params: tuple | None = None,
) -> list[dict]:
    database_manager = DatabaseManager()
    connection = database_manager.get_connection(database_role)

    try:
        with connection.cursor() as cursor:
            cursor.execute(sql, params or ())
            return list(cursor.fetchall())
    finally:
        connection.close()


def _information_schema_fetch_all(
    sql: str,
    params: tuple | None = None,
) -> list[dict]:
    return _fetch_all("COMMON", sql, params)


def table_schema(
    table_name: str,
    database_role: str = DEFAULT_DATABASE_ROLE,
) -> list[dict]:
    """Read one table's CREATE TABLE definition."""

    normalized_table_name = table_name.strip()
    normalized_database_role = (
        database_role.strip().upper()
    )

    if not normalized_table_name:
        raise ValueError(
            "table_name must not be empty."
        )

    if not VALID_IDENTIFIER_PATTERN.fullmatch(
        normalized_table_name
    ):
        raise ValueError(
            "table_name contains invalid characters."
        )

    sql = (
        "SHOW CREATE TABLE "
        f"`{normalized_table_name}`"
    )

    return _fetch_all(normalized_database_role, sql)


def table_data(
    table_name: str,
    limit: int = DEFAULT_LIMIT,
    database_role: str = DEFAULT_DATABASE_ROLE,
) -> list[dict]:
    """Read sample rows from a repository table."""

    normalized_table_name = table_name.strip()

    if not VALID_IDENTIFIER_PATTERN.fullmatch(
        normalized_table_name
    ):
        raise ValueError(
            "table_name contains invalid characters."
        )

    normalized_limit = max(
        1,
        min(int(limit), MAX_LIMIT),
    )

    sql = (
        "SELECT * "
        f"FROM `{normalized_table_name}` "
        f"LIMIT {normalized_limit}"
    )

    return _fetch_all(database_role.strip().upper(), sql)


def repository_inventory(
    database_roles: list[str] | None = None,
) -> list[dict[str, Any]]:
    """Return live Repository Table inventory."""

    normalized_roles = _normalize_database_roles(
        database_roles
    )
    database_name_map = _resolve_database_names(
        normalized_roles
    )
    database_names = list(database_name_map)

    placeholders = ", ".join(
        ["%s"] * len(database_names)
    )

    sql = f"""
    SELECT
        table_schema,
        table_name,
        table_type,
        table_rows,
        table_comment
    FROM information_schema.tables
    WHERE table_schema IN ({placeholders})
    ORDER BY
        table_schema,
        table_name
    """

    rows = _information_schema_fetch_all(
        sql,
        tuple(database_names),
    )

    for row in rows:
        row["database_role"] = database_name_map.get(
            row["table_schema"]
        )

    return rows


def repository_foreign_keys(
    database_roles: list[str] | None = None,
) -> list[dict[str, Any]]:
    """Return live Repository Foreign Key relations."""

    normalized_roles = _normalize_database_roles(
        database_roles
    )
    database_name_map = _resolve_database_names(
        normalized_roles
    )
    database_names = list(database_name_map)

    placeholders = ", ".join(
        ["%s"] * len(database_names)
    )

    sql = f"""
    SELECT
        constraint_schema,
        table_name,
        column_name,
        constraint_name,
        referenced_table_schema,
        referenced_table_name,
        referenced_column_name,
        ordinal_position
    FROM information_schema.key_column_usage
    WHERE constraint_schema IN ({placeholders})
      AND referenced_table_name IS NOT NULL
    ORDER BY
        constraint_schema,
        table_name,
        constraint_name,
        ordinal_position
    """

    return _information_schema_fetch_all(
        sql,
        tuple(database_names),
    )


def repository_logical_relations(
    database_roles: list[str] | None = None,
) -> list[dict[str, Any]]:
    """
    Return logical relations inferred from shared ID/Code columns.
    """

    normalized_roles = _normalize_database_roles(
        database_roles
    )
    database_name_map = _resolve_database_names(
        normalized_roles
    )
    database_names = list(database_name_map)

    placeholders = ", ".join(
        ["%s"] * len(database_names)
    )

    sql = f"""
    SELECT
        column_name,
        COUNT(
            DISTINCT CONCAT(
                table_schema,
                '.',
                table_name
            )
        ) AS table_count,
        GROUP_CONCAT(
            DISTINCT CONCAT(
                table_schema,
                '.',
                table_name
            )
            ORDER BY
                table_schema,
                table_name
            SEPARATOR ', '
        ) AS related_tables
    FROM information_schema.columns
    WHERE table_schema IN ({placeholders})
      AND (
          RIGHT(column_name, 3) = '_id'
          OR RIGHT(column_name, 5) = '_code'
      )
      AND column_name NOT IN (
          'status_code',
          'program_id'
      )
      AND INSTR(table_name, 'backup') = 0
    GROUP BY column_name
    HAVING COUNT(
        DISTINCT CONCAT(
            table_schema,
            '.',
            table_name
        )
    ) >= 2
    ORDER BY
        table_count DESC,
        column_name
    """

    return _information_schema_fetch_all(
        sql,
        tuple(database_names),
    )

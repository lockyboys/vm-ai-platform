from __future__ import annotations

import re
from typing import Any

from common.database import CommonDatabase


DEFAULT_DATABASE_ROLE = "STORY_PLATFORM"
DEFAULT_DATABASE_ROLES = [
    "COMMON",
    "STORY_PLATFORM",
    "HEALTH_COMPANION",
]

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
        else DEFAULT_DATABASE_ROLES
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

    for database_role in database_roles:
        database = CommonDatabase(
            database_role=database_role
        )

        try:
            database_names[database.database_name] = (
                database_role
            )
        finally:
            database.close()

    return database_names


def _information_schema_database() -> CommonDatabase:
    return CommonDatabase(database_role="COMMON")


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

    database = CommonDatabase(
        database_role=normalized_database_role,
    )

    try:
        sql = (
            "SHOW CREATE TABLE "
            f"`{normalized_table_name}`"
        )

        return database.fetch_all(sql)
    finally:
        database.close()


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

    database = CommonDatabase(
        database_role=database_role.strip().upper(),
    )

    try:
        sql = (
            "SELECT * "
            f"FROM `{normalized_table_name}` "
            f"LIMIT {normalized_limit}"
        )

        return database.fetch_all(sql)
    finally:
        database.close()


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

    database = _information_schema_database()

    try:
        rows = database.fetch_all(
            sql,
            tuple(database_names),
        )
    finally:
        database.close()

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

    database = _information_schema_database()

    try:
        return database.fetch_all(
            sql,
            tuple(database_names),
        )
    finally:
        database.close()


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

    database = _information_schema_database()

    try:
        return database.fetch_all(
            sql,
            tuple(database_names),
        )
    finally:
        database.close()

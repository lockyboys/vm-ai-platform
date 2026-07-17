from __future__ import annotations

import re

from common.database import CommonDatabase


DEFAULT_DATABASE_ROLE = "STORY_PLATFORM"

VALID_IDENTIFIER_PATTERN = re.compile(
    r"^[A-Za-z_][A-Za-z0-9_]*$"
)


def table_schema(
    table_name: str,
    database_role: str = DEFAULT_DATABASE_ROLE,
) -> list[dict]:
    """Read one table's CREATE TABLE definition."""

    normalized_table_name = table_name.strip()
    normalized_database_role = database_role.strip().upper()

    if not normalized_table_name:
        raise ValueError("table_name must not be empty.")

    if not VALID_IDENTIFIER_PATTERN.fullmatch(
        normalized_table_name
    ):
        raise ValueError(
            "table_name contains invalid characters."
        )

    database = CommonDatabase(
        database_role=normalized_database_role,
    )

    sql = (
        f"SHOW CREATE TABLE "
        f"`{normalized_table_name}`"
    )

    return database.fetch_all(sql)

DEFAULT_LIMIT = 20
MAX_LIMIT = 100


def table_data(
    table_name: str,
    limit: int = DEFAULT_LIMIT,
    database_role: str = "STORY_PLATFORM",
) -> list[dict]:
    """
    Read sample rows from a repository table.
    """

    normalized_limit = max(
        1,
        min(limit, MAX_LIMIT),
    )

    database = CommonDatabase(
        database_role=database_role,
    )

    sql = (
        f"SELECT * "
        f"FROM `{table_name}` "
        f"LIMIT {normalized_limit}"
    )

    return database.fetch_all(sql)
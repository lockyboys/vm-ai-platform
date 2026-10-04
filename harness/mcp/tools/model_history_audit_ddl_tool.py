# =============================================================================
# File Name   : harness/mcp/tools/model_history_audit_ddl_tool.py
# Purpose     : Execute one guarded MariaDB table DDL statement
# =============================================================================
from __future__ import annotations

import re
from typing import Any

from common.common_function import logger, normalize_required_text
from common.database import CommonDatabase


_TABLE_DDL = re.compile(
    r"^\s*(ALTER\s+TABLE|CREATE\s+TABLE|DROP\s+TABLE|TRUNCATE(?:\s+TABLE)?|RENAME\s+TABLE)\s+"
    r"(?:IF\s+(?:NOT\s+)?EXISTS\s+)?((?:`?[A-Za-z_][A-Za-z0-9_$]*`?\.)?`?[A-Za-z_][A-Za-z0-9_$]*`?)",
    re.IGNORECASE,
)
_IDENTIFIER = re.compile(r"`?([A-Za-z_][A-Za-z0-9_$]*)`?")


def _parse_target(statement: str, database_name: str) -> tuple[str, str]:
    if not statement.strip() or any(token in statement for token in (";", "--", "/*", "*/", "#")):
        # One optional trailing semicolon is accepted below; comments are not.
        stripped = statement.strip()
        if stripped.endswith(";") and stripped.count(";") == 1 and not any(
            token in statement for token in ("--", "/*", "*/", "#")
        ):
            statement = stripped[:-1]
        else:
            raise ValueError("Provide exactly one table DDL statement without SQL comments.")
    match = _TABLE_DDL.match(statement)
    if not match:
        raise ValueError("Supported statements: CREATE TABLE, ALTER TABLE, DROP TABLE, TRUNCATE [TABLE], RENAME TABLE.")
    op = match.group(1).split()[0].upper()
    raw_target = match.group(2)
    parts = raw_target.split(".")
    names = []
    for part in parts:
        identifier_match = _IDENTIFIER.fullmatch(part)
        if not identifier_match:
            raise ValueError("DDL target must use a plain table identifier.")
        names.append(identifier_match.group(1))
    if len(names) == 2 and names[0] != database_name:
        raise ValueError(f"DDL target must belong to the selected database ({database_name}).")
    table_name = names[-1]
    if op == "DROP":
        drop_match = re.fullmatch(
            r"\s*DROP\s+TABLE\s+(?:IF\s+EXISTS\s+)?((?:`?[A-Za-z_][A-Za-z0-9_$]*`?\.)?`?[A-Za-z_][A-Za-z0-9_$]*`?)\s*",
            statement,
            re.IGNORECASE,
        )
        if not drop_match or drop_match.group(1) != raw_target:
            raise ValueError("Only one DROP TABLE target is supported; DROP DATABASE and multi-table DROP are rejected.")
    return op, table_name


def mariadb_ddl_execute(
    sql_text: str,
    database_role: str = "COMMON",
    apply: bool = False,
    confirmation_text: str = "",
) -> dict[str, Any]:
    """Preview or execute one table DDL statement in a Repository database role.

    DROP TABLE and TRUNCATE [TABLE] require exact operation-specific confirmation
    text naming one table; both also require apply=True to execute.
    DROP is limited to one existing table and requires its exact confirmation
    text plus apply=True. Service reflection of this description is unverified.
    """
    if not isinstance(sql_text, str):
        raise TypeError("sql_text must be a string.")
    sql_text = normalize_required_text(sql_text, "sql_text")
    role = normalize_required_text(database_role, "database_role").upper()
    if role not in {
        "COMMON", "STORY", "STORY_PLATFORM", "AI", "AI_PLATFORM",
        "HEALTH", "HEALTH_COMPANION", "BUSAN", "BUSAN_CARE", "KDT", "KDT_CARE",
    }:
        raise ValueError("database_role must be an official CommonDatabase role.")

    database = CommonDatabase(database_role=role)
    try:
        operation, table_name = _parse_target(sql_text, database.database_name)
        normalized_sql = sql_text.strip().removesuffix(";").strip()
        if operation in {"DROP", "TRUNCATE"}:
            confirmation_verb = "DROP TABLE" if operation == "DROP" else "TRUNCATE TABLE"
            expected = f"{confirmation_verb} {database.database_name}.{table_name}"
            if confirmation_text.strip().upper() != expected.upper():
                raise ValueError(f"{operation} requires confirmation_text exactly equal to: {expected}")

        exists = database.fetch_one(
            """SELECT table_name, table_type FROM information_schema.tables
               WHERE table_schema = %s AND table_name = %s""",
            (database.database_name, table_name),
        )
        if operation in {"ALTER", "DROP", "TRUNCATE", "RENAME"} and not exists:
            raise ValueError(f"Target table does not exist: {database.database_name}.{table_name}")
        if operation == "DROP" and str(exists.get("table_type", "")).upper() != "BASE TABLE":
            raise ValueError("DROP is limited to existing base tables.")

        plan = {
            "database_role": role,
            "database_name": database.database_name,
            "operation": operation,
            "table_name": table_name,
            "sql_preview": normalized_sql,
            "dry_run": not apply,
            "applied": False,
        }
        if not apply:
            return plan

        affected = database.execute(normalized_sql)
        database.commit()
        if operation == "DROP":
            verified = database.fetch_one(
                """SELECT table_name FROM information_schema.tables
                   WHERE table_schema = %s AND table_name = %s""",
                (database.database_name, table_name),
            )
            if verified:
                raise RuntimeError(f"DROP did not remove table {table_name}.")
            plan["verified_absent"] = True
        else:
            plan["affected_rows"] = affected
        plan["dry_run"] = False
        plan["applied"] = True
        logger.info("MariaDB DDL applied: role=%s operation=%s table=%s", role, operation, table_name)
        return plan
    except Exception:
        database.rollback()
        logger.exception("MariaDB DDL failed: role=%s", role)
        raise
    finally:
        database.close()
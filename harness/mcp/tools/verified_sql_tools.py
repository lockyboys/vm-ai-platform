# =============================================================================
# File Name   : harness/mcp/tools/verified_sql_tools.py
# Purpose     : SPS Harness Verified SQL Execution Tool
# =============================================================================
# CHANGE HISTORY
# =============================================================================
# 20260729 | OpenAI | Verified SQL Query ID 기반의 단일 문장 실행 도구를 추가했음
# =============================================================================

from __future__ import annotations

import json
import re
from typing import Any

from common.database import CommonDatabase


_READ_STATEMENTS = {"SELECT", "SHOW", "DESCRIBE", "EXPLAIN"}
_MUTATION_STATEMENTS = {"INSERT", "UPDATE", "DELETE", "CALL"}
_DISALLOWED_STATEMENTS = {
    "ALTER",
    "CREATE",
    "DROP",
    "GRANT",
    "LOAD",
    "RENAME",
    "REPLACE",
    "TRUNCATE",
}
_SQL_KEYWORD_PATTERN = re.compile(r"^[A-Z]+")
_MAX_RESULT_ROWS = 100


def _parse_params_json(parameters_json: str) -> tuple[Any, ...]:
    try:
        parameters = json.loads(parameters_json)
    except json.JSONDecodeError as error:
        raise ValueError("parameters_json must be a JSON array.") from error

    if not isinstance(parameters, list):
        raise ValueError("parameters_json must contain a JSON array.")

    return tuple(parameters)


def _strip_leading_sql_comments(sql_text: str) -> str:
    remaining = sql_text.lstrip()

    while True:
        if remaining.startswith("--"):
            line_end = remaining.find("\n")
            remaining = "" if line_end == -1 else remaining[line_end + 1 :].lstrip()
            continue

        if remaining.startswith("/*"):
            comment_end = remaining.find("*/")
            if comment_end == -1:
                raise ValueError("sql_text contains an unclosed block comment.")
            remaining = remaining[comment_end + 2 :].lstrip()
            continue

        return remaining


def _statement_keyword(sql_text: str) -> str:
    executable_sql = _strip_leading_sql_comments(sql_text)
    matched = _SQL_KEYWORD_PATTERN.match(executable_sql.upper())

    if not matched:
        raise ValueError("Verified SQL must begin with a SQL statement keyword.")

    return matched.group(0)


def _contains_multiple_statements(sql_text: str) -> bool:
    quote = ""
    index = 0
    statement_ended = False

    while index < len(sql_text):
        character = sql_text[index]
        next_character = sql_text[index + 1] if index + 1 < len(sql_text) else ""

        if quote:
            if character == "\\":
                index += 2
                continue
            if character == quote:
                quote = ""
            index += 1
            continue

        if character in {"'", '"', "`"}:
            quote = character
            index += 1
            continue

        if character == "-" and next_character == "-":
            line_end = sql_text.find("\n", index + 2)
            index = len(sql_text) if line_end == -1 else line_end + 1
            continue

        if character == "/" and next_character == "*":
            comment_end = sql_text.find("*/", index + 2)
            if comment_end == -1:
                raise ValueError("sql_text contains an unclosed block comment.")
            index = comment_end + 2
            continue

        if character == ";":
            statement_ended = True
            index += 1
            continue

        if statement_ended and not character.isspace():
            raise ValueError(
                "verified_sql_execute supports exactly one SQL statement per Query ID."
            )

        index += 1

    if quote:
        raise ValueError("sql_text contains an unclosed quoted value.")

    return statement_ended


def _load_executable_query(
    database: CommonDatabase,
    query_id: str,
) -> dict[str, Any]:
    query = database.fetch_one(
        """
        SELECT
            query_id,
            query_name,
            query_description,
            crud_type,
            sql_text,
            certified_level_code
        FROM cm_verified_sql_query
        WHERE query_id = %s
          AND verified_yn = 'Y'
          AND certified_level_code = 'A'
          AND status_code = 'ACTIVE'
          AND deleted_dt IS NULL
        """,
        (query_id.strip(),),
    )

    if not query:
        raise ValueError(
            "query_id is not an executable Verified SQL Query. "
            "It must be active, verified, certified A, and not deleted."
        )

    return query


def _resolve_execution_database_role(query_description: str | None) -> str:
    if not query_description:
        return "COMMON"

    try:
        execution_contract = json.loads(query_description)
    except json.JSONDecodeError:
        return "COMMON"

    if not isinstance(execution_contract, dict):
        return "COMMON"

    database_role = execution_contract.get("database_role", "COMMON")
    if not isinstance(database_role, str) or not database_role.strip():
        raise ValueError("Verified SQL execution contract has an invalid database_role.")

    return database_role.strip().upper()


def verified_sql_execute(
    query_id: str,
    parameters_json: str = "[]",
    apply: bool = False,
) -> dict[str, Any]:
    """
    Execute one certified, active Verified SQL Query by Query ID.

    Arbitrary SQL text is never accepted. The default is dry-run; set apply=true
    only after reviewing the registered Query ID and its verified SQL contract.
    DDL and multi-statement batches are deliberately rejected.
    """

    normalized_query_id = query_id.strip()
    if not normalized_query_id:
        raise ValueError("query_id must not be empty.")

    parameters = _parse_params_json(parameters_json)
    repository_database = CommonDatabase(database_role="COMMON")

    try:
        query = _load_executable_query(repository_database, normalized_query_id)
    finally:
        repository_database.close()

    execution_database = CommonDatabase(
        database_role=_resolve_execution_database_role(query["query_description"]),
    )

    try:
        statement_keyword = _statement_keyword(query["sql_text"])

        if statement_keyword in _DISALLOWED_STATEMENTS:
            raise ValueError(
                f"{statement_keyword} is not allowed by verified_sql_execute."
            )

        if statement_keyword not in _READ_STATEMENTS | _MUTATION_STATEMENTS:
            raise ValueError(
                f"{statement_keyword} is not supported by verified_sql_execute."
            )

        _contains_multiple_statements(query["sql_text"])

        result: dict[str, Any] = {
            "query_id": query["query_id"],
            "query_name": query["query_name"],
            "crud_type": query["crud_type"],
            "statement_keyword": statement_keyword,
            "certified_level_code": query["certified_level_code"],
            "parameter_count": len(parameters),
            "dry_run": not apply,
        }

        if not apply:
            return result

        connection = execution_database.connect_mariadb()
        try:
            with connection.cursor() as cursor:
                cursor.execute(query["sql_text"], parameters)

                if cursor.description:
                    rows = list(cursor.fetchmany(_MAX_RESULT_ROWS))
                    result["row_count"] = len(rows)
                    result["rows"] = rows
                    result["result_row_limit"] = _MAX_RESULT_ROWS
                    connection.rollback()
                else:
                    result["affected_rows"] = int(cursor.rowcount)
                    connection.commit()

            result["executed"] = True
            return result
        except Exception:
            connection.rollback()
            raise
    finally:
        execution_database.close()

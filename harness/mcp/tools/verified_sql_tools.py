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

from common.common_function import (
    normalize_required_text,
    validate_common_code_value,
)
from common.database import CommonDatabase
from engine.common.query_identifier_feature_rule_resolver import (
    QueryIdentifierFeatureRuleResolver,
)
from engine.identifier import IdentifierCoordinator


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

def _resolve_query_identifier_feature(query_feature_code: str) -> Any:
    rule_database = CommonDatabase(database_role="COMMON")
    try:
        return QueryIdentifierFeatureRuleResolver(rule_database).resolve(
            query_feature_code
        )
    finally:
        rule_database.close()


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


def _validate_registration_sql(sql_text: str) -> tuple[str, str]:
    normalized_sql_text = normalize_required_text(sql_text, "sql_text")
    statement_keyword = _statement_keyword(normalized_sql_text)
    if statement_keyword in _DISALLOWED_STATEMENTS:
        raise ValueError(f"{statement_keyword} is not allowed by verified_sql_register.")
    if statement_keyword not in _READ_STATEMENTS | _MUTATION_STATEMENTS:
        raise ValueError(f"{statement_keyword} is not supported by verified_sql_register.")
    _contains_multiple_statements(normalized_sql_text)
    return normalized_sql_text, statement_keyword


def _normalize_verification_request(
    *,
    verified_yn: bool,
    certified_level_code: str,
    verification_description: str,
    verified_by: str,
) -> tuple[str, str | None, str | None, str | None]:
    if not verified_yn:
        if any(value.strip() for value in (
            certified_level_code,
            verification_description,
            verified_by,
        )):
            raise ValueError("Verification fields require verified_yn=true.")
        return "N", None, None, None

    return (
        "Y",
        normalize_required_text(certified_level_code, "certified_level_code").upper(),
        normalize_required_text(verification_description, "verification_description"),
        normalize_required_text(verified_by, "verified_by"),
    )


def _resolve_verified_sql_object_code(
    identifier_database: CommonDatabase,
) -> str:
    object_rows = identifier_database.fetch_all(
        """
        SELECT object_code
        FROM sp_object
        WHERE target_identifier_field = %s
          AND active_yn = 'Y'
          AND status_code = 'ACTIVE'
          AND deleted_dt IS NULL
        ORDER BY object_code
        """,
        ("query_id",),
    )
    if len(object_rows) != 1:
        raise ValueError(
            "Verified SQL Identifier metadata must resolve exactly one Object. "
            f"target_identifier_field=query_id, object_count={len(object_rows)}"
        )
    return normalize_required_text(
        object_rows[0].get("object_code"),
        "sp_object.object_code",
    )
def verified_sql_register(
    query_name: str,
    query_feature_code: str,
    query_description: str,
    crud_type: str,
    sql_text: str,
    registered_by: str,
    verified_yn: bool = False,
    certified_level_code: str = "",
    verification_description: str = "",
    verified_by: str = "",
    story_programming_rule_pass_yn: bool = False,
    snake_case_pass_yn: bool = False,
    table_exists_pass_yn: bool = False,
    column_exists_pass_yn: bool = False,
    crud_match_pass_yn: bool = False,
    where_clause_pass_yn: bool = False,
    program_id: str = "",
    client_ip: str = "",
    apply: bool = False,
) -> dict[str, Any]:
    """
    Register one new Verified SQL Query without executing it.

    The default is validation-only. Set apply=true to allocate the Repository
    Query ID and insert exactly one new cm_verified_sql_query row. SQL execution
    remains available only through verified_sql_execute(query_id=...).
    """

    normalized_query_name = normalize_required_text(query_name, "query_name")
    normalized_query_description = normalize_required_text(
        query_description,
        "query_description",
    )
    normalized_crud_type = normalize_required_text(crud_type, "crud_type").upper()
    normalized_registered_by = normalize_required_text(registered_by, "registered_by")
    normalized_sql_text, statement_keyword = _validate_registration_sql(sql_text)
    query_feature_resolution = _resolve_query_identifier_feature(
        query_feature_code
    )
    normalized_query_feature_code = query_feature_resolution.query_feature_code
    (
        normalized_verified_yn,
        normalized_certified_level_code,
        normalized_verification_description,
        normalized_verified_by,
    ) = _normalize_verification_request(
        verified_yn=verified_yn,
        certified_level_code=certified_level_code,
        verification_description=verification_description,
        verified_by=verified_by,
    )
    validation_flags = (
        story_programming_rule_pass_yn,
        snake_case_pass_yn,
        table_exists_pass_yn,
        column_exists_pass_yn,
        crud_match_pass_yn,
        where_clause_pass_yn,
    )
    if normalized_verified_yn == "Y" and not all(validation_flags):
        raise ValueError(
            "verified_yn=true requires every explicit validation pass flag."
        )
    if normalized_verified_yn == "N" and any(validation_flags):
        raise ValueError(
            "Validation pass flags require verified_yn=true."
        )
    result: dict[str, Any] = {
        "dry_run": not apply,
        "statement_keyword": statement_keyword,
        "crud_type": normalized_crud_type,
        "verified_yn": normalized_verified_yn,
        "query_feature_code": normalized_query_feature_code,
        "query_feature_rule_id": query_feature_resolution.rule_id,
        "query_feature_rule_code": query_feature_resolution.rule_code,
    }
    if not apply:
        return result

    identifier_database = CommonDatabase(database_role="STORY")
    try:
        identifier_object_code = _resolve_verified_sql_object_code(identifier_database)
        identifier_coordinator = IdentifierCoordinator(identifier_database)
        identifier_object_metadata = _load_registered_object_metadata(
            identifier_database,
            identifier_object_code,
        )
        identifier_maximum_length = (
            identifier_coordinator.resolve_identifier_maximum_length(
                object_metadata=identifier_object_metadata,
            )
        )
        identifier_request, identifier_preparation = (
            identifier_coordinator.prepare_registered_object(
                object_metadata=identifier_object_metadata,
                created_by=normalized_registered_by,
                updated_by=normalized_registered_by,
                client_ip=client_ip.strip() or "127.0.0.1",
                program_id=program_id.strip() or "VERIFIED_SQL_REGISTER",
            )
        )
        identifier_database.begin()
        try:
            identifier_coordinator.acquire(identifier_preparation)
            try:
                identifier_resolution = identifier_coordinator.resolve(
                    request=identifier_request,
                    prepared=identifier_preparation,
                    maximum_length=identifier_maximum_length,
                )
                query_id = identifier_coordinator.render_resolution(
                    request=identifier_request,
                    prepared=identifier_preparation,
                    resolution=identifier_resolution,
                    object_code=normalized_query_feature_code,
                    maximum_length=identifier_maximum_length,
                )
            finally:
                identifier_coordinator.release(identifier_preparation)
            identifier_database.commit()
        except Exception:
            identifier_database.rollback()
            raise
    finally:
        identifier_database.close()

    repository_database = CommonDatabase(database_role="COMMON")
    try:
        normalized_crud_type = validate_common_code_value(
            repository_database,
            "CRUD",
            normalized_crud_type,
        )
        if normalized_certified_level_code:
            normalized_certified_level_code = validate_common_code_value(
                repository_database,
                "EVIDENCE_LEVEL",
                normalized_certified_level_code,
            )
        existing_query = repository_database.fetch_one(
            "SELECT query_id FROM cm_verified_sql_query WHERE query_id = %s",
            (query_id,),
        )
        if existing_query:
            raise RuntimeError(
                "Generated Query ID already exists in cm_verified_sql_query. "
                f"query_id={query_id}"
            )

        repository_database.begin()
        try:
            inserted_rows = repository_database.execute(
                """
                INSERT INTO cm_verified_sql_query (
                    query_id, query_name, query_description, crud_type, sql_text,
                    verified_yn, certified_level_code, verification_description,
                    verified_by, story_programming_rule_pass_yn,
                    snake_case_pass_yn, table_exists_pass_yn,
                    column_exists_pass_yn, crud_match_pass_yn,
                    where_clause_pass_yn, created_by, program_id, client_ip
                )
                VALUES (
                    %s, %s, %s, %s, %s, %s, %s, %s, %s,
                    %s, %s, %s, %s, %s, %s, %s, %s, %s
                )
                """,
                (
                    query_id,
                    normalized_query_name,
                    normalized_query_description,
                    normalized_crud_type,
                    normalized_sql_text,
                    normalized_verified_yn,
                    normalized_certified_level_code,
                    normalized_verification_description,
                    normalized_verified_by,
                    "Y" if story_programming_rule_pass_yn else "N",
                    "Y" if snake_case_pass_yn else "N",
                    "Y" if table_exists_pass_yn else "N",
                    "Y" if column_exists_pass_yn else "N",
                    "Y" if crud_match_pass_yn else "N",
                    "Y" if where_clause_pass_yn else "N",
                    normalized_registered_by,
                    program_id.strip() or None,
                    client_ip.strip() or None,
                ),
            )
            if inserted_rows != 1:
                raise RuntimeError(
                    "Verified SQL registration did not insert exactly one row. "
                    f"inserted_rows={inserted_rows}"
                )
            repository_database.commit()
        except Exception:
            repository_database.rollback()
            raise
    finally:
        repository_database.close()

    result.update(
        {
            "dry_run": False,
            "query_id": query_id,
            "certified_level_code": normalized_certified_level_code,
            "inserted_rows": inserted_rows,
        }
    )
    return result



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

def _load_registered_object_metadata(
    identifier_database: CommonDatabase,
    object_code: str,
) -> dict[str, Any]:
    """Load the existing active Object metadata required for identifier allocation."""
    object_metadata = identifier_database.fetch_one(
        """
        SELECT
            object_code,
            object_name,
            business_code,
            domain_code,
            object_level,
            identifier_target_code,
            sequence_scope_code,
            sequence_length,
            target_identifier_field
        FROM sp_object
        WHERE object_code = %s
          AND active_yn = 'Y'
          AND status_code = 'ACTIVE'
          AND deleted_dt IS NULL
        """,
        (object_code,),
    )
    if not object_metadata:
        raise LookupError(
            "Verified SQL Identifier Object metadata was not found. "
            f"object_code={object_code}"
        )
    return object_metadata

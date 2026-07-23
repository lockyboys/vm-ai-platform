from __future__ import annotations

import json
import os
import re
from typing import Any

from bson import ObjectId
from pymongo import MongoClient

from core.database.database_manager import DatabaseManager


DEFAULT_LIMIT = 20
MAX_LIMIT = 100
VALID_IDENTIFIER_PATTERN = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


def _validate_collection_name(collection_name: str) -> str:
    normalized_name = collection_name.strip()

    if not VALID_IDENTIFIER_PATTERN.fullmatch(normalized_name):
        raise ValueError("collection_name contains invalid characters.")

    return normalized_name


def _normalize_limit(limit: int) -> int:
    return max(1, min(int(limit), MAX_LIMIT))


def _get_mongodb_database() -> tuple[MongoClient, Any]:
    mongodb_uri = os.getenv("MONGODB_URI")
    mongodb_database = os.getenv("MONGODB_DATABASE")

    if not mongodb_uri or not mongodb_database:
        raise RuntimeError(
            "MONGODB_URI and MONGODB_DATABASE must be configured."
        )

    client = MongoClient(
        mongodb_uri,
        serverSelectionTimeoutMS=5000,
    )
    return client, client[mongodb_database]


def _normalize_mongodb_value(value: Any) -> Any:
    if isinstance(value, ObjectId):
        return str(value)

    if isinstance(value, dict):
        return {
            str(key): _normalize_mongodb_value(item)
            for key, item in value.items()
        }

    if isinstance(value, list):
        return [
            _normalize_mongodb_value(item)
            for item in value
        ]

    return value


def _parse_json_object(
    raw_json: str,
    field_name: str,
) -> dict[str, Any]:
    try:
        value = json.loads(raw_json)
    except json.JSONDecodeError as error:
        raise ValueError(
            f"{field_name} must be valid JSON."
        ) from error

    if not isinstance(value, dict):
        raise ValueError(
            f"{field_name} must contain a JSON object."
        )

    return value


def mongodb_collections() -> list[dict[str, Any]]:
    """List MongoDB collections resolved from Harness environment metadata."""

    client, database = _get_mongodb_database()

    try:
        return [
            {"collection_name": name}
            for name in sorted(database.list_collection_names())
        ]
    finally:
        client.close()


def mongodb_documents(
    collection_name: str,
    filter_json: str = "{}",
    limit: int = DEFAULT_LIMIT,
) -> list[dict[str, Any]]:
    """Read bounded MongoDB documents from one collection."""

    normalized_collection_name = _validate_collection_name(
        collection_name
    )
    filter_document = _parse_json_object(
        filter_json,
        "filter_json",
    )
    normalized_limit = _normalize_limit(limit)
    client, database = _get_mongodb_database()

    try:
        documents = database[normalized_collection_name].find(
            filter_document
        ).limit(normalized_limit)

        return [
            _normalize_mongodb_value(document)
            for document in documents
        ]
    finally:
        client.close()


def mongodb_save_document(
    collection_name: str,
    document_json: str,
) -> dict[str, Any]:
    """
    Save one MongoDB document.

    Call only after the Object Runtime has generated and saved the
    corresponding Repository identity and execution metadata.
    """

    normalized_collection_name = _validate_collection_name(
        collection_name
    )
    document = _parse_json_object(
        document_json,
        "document_json",
    )
    client, database = _get_mongodb_database()

    try:
        result = database[normalized_collection_name].insert_one(document)

        return {
            "collection_name": normalized_collection_name,
            "mongodb_document_id": str(result.inserted_id),
            "acknowledged": bool(result.acknowledged),
        }
    finally:
        client.close()


def verified_sql(
    query_id: str | None = None,
    include_sql_text: bool = False,
) -> list[dict[str, Any]]:
    """
    Read approved SQL from the Common Repository.

    This tool returns only verified, active, non-deleted queries.
    It does not execute SQL batches.
    """

    selected_sql_text = "sql_text" if include_sql_text else "NULL AS sql_text"
    sql = f"""
    SELECT
        query_id,
        query_name,
        query_description,
        crud_type,
        verified_yn,
        certified_level_code,
        verification_description,
        verified_by,
        verified_dt,
        {selected_sql_text}
    FROM cm_verified_sql_query
    WHERE verified_yn = 'Y'
      AND status_code = 'ACTIVE'
      AND deleted_dt IS NULL
    """
    params: tuple[Any, ...] = ()

    if query_id:
        sql += " AND query_id = %s"
        params = (query_id.strip(),)

    sql += " ORDER BY query_id"

    database_manager = DatabaseManager()
    connection = database_manager.get_connection("COMMON")

    try:
        with connection.cursor() as cursor:
            cursor.execute(sql, params)
            return list(cursor.fetchall())
    finally:
        connection.close()

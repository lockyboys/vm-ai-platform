"""
MongoDB Document Generator

Purpose:
    SPS Knowledge Document Object를 MongoDB Collection에 저장한다.

Principle:
    - Generator is Model.
    - Repository First.
    - No Hardcoding.
"""

from __future__ import annotations

from typing import Any

from common.database import CommonDatabase


class MongoDBDocumentGenerator:
    """Knowledge Document를 MongoDB에 저장한다."""

    def __init__(self) -> None:
        self.database = CommonDatabase(
            database_role="STORY",
            connect_mariadb=False,
            connect_mongodb=True,
        )
        self.mongodb_database = self.database.get_mongodb_database().name

    def save(
        self,
        mongodb_document_request: dict[str, Any],
    ) -> dict[str, Any]:
        """Knowledge Document 한 건을 MongoDB에 저장한다."""
        try:
            collection_name = mongodb_document_request.get(
                "collection_name"
            )
            knowledge_document = mongodb_document_request.get(
                "knowledge_document"
            )

            if not collection_name:
                raise ValueError(
                    "collection_name is required."
                )

            if not knowledge_document:
                raise ValueError(
                    "knowledge_document is required."
                )

            insert_result = self.database.insert_one(
                collection_name=collection_name,
                document=knowledge_document,
            )

            return {
                "generator": "MongoDBDocumentGenerator",
                "database_name": self.mongodb_database,
                "collection_name": collection_name,
                "knowledge_document_id": (
                    knowledge_document.get(
                        "knowledge_document_id"
                    )
                ),
                "inserted_id": str(insert_result.inserted_id),
                "status": "SUCCESS",
            }

        except Exception as error:
            return {
                "generator": "MongoDBDocumentGenerator",
                "database_name": self.mongodb_database,
                "collection_name": (
                    mongodb_document_request.get(
                        "collection_name"
                    )
                ),
                "knowledge_document_id": (
                    mongodb_document_request
                    .get("knowledge_document", {})
                    .get("knowledge_document_id")
                ),
                "inserted_id": None,
                "status": "FAILED",
                "message": str(error),
            }

    def close(self) -> None:
        self.database.close()

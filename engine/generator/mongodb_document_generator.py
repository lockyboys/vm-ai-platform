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

import os
from typing import Any

from dotenv import load_dotenv
from pymongo import MongoClient


class MongoDBDocumentGenerator:
    """Knowledge Document를 MongoDB에 저장한다."""

    def __init__(self) -> None:
        load_dotenv()

        self.mongodb_uri = os.getenv("MONGODB_URI")
        self.mongodb_database = os.getenv("MONGODB_DATABASE")

        if not self.mongodb_uri:
            raise RuntimeError(
                "MONGODB_URI metadata is not configured."
            )

        if not self.mongodb_database:
            raise RuntimeError(
                "MONGODB_DATABASE metadata is not configured."
            )

    def save(
        self,
        mongodb_document_request: dict[str, Any],
    ) -> dict[str, Any]:
        """Knowledge Document 한 건을 MongoDB에 저장한다."""
        client = None

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

            client = MongoClient(
                self.mongodb_uri,
                serverSelectionTimeoutMS=5000,
            )

            database = client[self.mongodb_database]
            collection = database[collection_name]

            insert_result = collection.insert_one(
                knowledge_document
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

        finally:
            if client is not None:
                client.close()

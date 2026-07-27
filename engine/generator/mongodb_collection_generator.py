# =============================================================================
# File Name   : engine/generator/mongodb_collection_generator.py
# Purpose     : MongoDB Collection and Document Generator
# Author      : PARK HEAKYU
# Updated     : 2026-07-26
# Description : CommonDatabase를 통해 MongoDB Collection과 Document를 생성한다.
# =============================================================================
# CHANGE HISTORY
# =============================================================================
# 20260726 | OpenAI | MongoClient 직접 사용을 제거하고 CommonDatabase 기반으로 변경했음
# =============================================================================

from common.database import CommonDatabase


class MongoDBCollectionGenerator:
    """
    MongoDB Collection Generator

    MongoDB Collection 존재 여부를 확인하고 없으면 생성한다.
    Knowledge Document를 대상 Collection에 저장한다.
    """

    def __init__(self):
        self.database = CommonDatabase(
            database_role="STORY",
            connect_mariadb=False,
            connect_mongodb=True,
        )
        self.mongodb_database = self.database.get_mongodb_database().name

    def save(self, mongodb_collection_request):
        """Collection 존재 여부를 확인하고 없으면 생성한다."""
        try:
            collection_name = mongodb_collection_request["collection_name"]
            mongodb_database = self.database.get_mongodb_database()
            existing_collections = self.database.list_collection_names()

            if collection_name not in existing_collections:
                mongodb_database.create_collection(collection_name)
                created_yn = "Y"
            else:
                created_yn = "N"

            return {
                "generator": "MongoDBCollectionGenerator",
                "database_name": self.mongodb_database,
                "collection_name": collection_name,
                "created_yn": created_yn,
                "status": "SUCCESS",
            }

        except Exception as ex:
            return {
                "generator": "MongoDBCollectionGenerator",
                "database_name": self.mongodb_database,
                "collection_name": mongodb_collection_request.get(
                    "collection_name"
                ),
                "created_yn": "N",
                "status": "FAILED",
                "message": str(ex),
            }

    def save_document(self, mongodb_save_request):
        """Knowledge Document를 MongoDB Collection에 저장한다."""
        try:
            collection_name = mongodb_save_request["target_collection"]
            knowledge_document = mongodb_save_request["knowledge_document"]
            insert_result = self.database.insert_one(
                collection_name=collection_name,
                document=knowledge_document,
            )

            return {
                "generator": "MongoDBCollectionGenerator",
                "database_name": self.mongodb_database,
                "collection_name": collection_name,
                "mongodb_document_id": knowledge_document.get(
                    "knowledge_document_id"
                ),
                "inserted_id": str(insert_result.inserted_id),
                "status": "SUCCESS",
            }

        except Exception as ex:
            return {
                "generator": "MongoDBCollectionGenerator",
                "database_name": self.mongodb_database,
                "collection_name": mongodb_save_request.get(
                    "target_collection"
                ),
                "mongodb_document_id": (
                    mongodb_save_request
                    .get("knowledge_document", {})
                    .get("knowledge_document_id")
                ),
                "inserted_id": None,
                "status": "FAILED",
                "message": str(ex),
            }

    def close(self):
        self.database.close()

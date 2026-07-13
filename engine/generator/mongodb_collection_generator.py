import os

from dotenv import load_dotenv
from pymongo import MongoClient


class MongoDBCollectionGenerator:
    """
    MongoDB Collection Generator

    MongoDB Collection 존재 여부를 확인하고,
    없으면 생성한다.

    Knowledge Document를 대상 Collection에 저장한다.
    """

    def __init__(self):
        load_dotenv()

        self.mongodb_uri = os.getenv("MONGODB_URI")
        self.mongodb_database = os.getenv(
            "MONGODB_DATABASE",
            "vm_project_v7",
        )

    def save(self, mongodb_collection_request):
        """
        Collection 존재 여부를 확인하고 없으면 생성한다.
        """
        client = None

        try:
            client = MongoClient(self.mongodb_uri)
            db = client[self.mongodb_database]

            collection_name = mongodb_collection_request["collection_name"]

            existing_collections = db.list_collection_names()

            if collection_name not in existing_collections:
                db.create_collection(collection_name)
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

        finally:
            if client:
                client.close()

    def save_document(self, mongodb_save_request):
        """
        Knowledge Document를 MongoDB Collection에 저장한다.
        """
        client = None

        try:
            client = MongoClient(self.mongodb_uri)
            db = client[self.mongodb_database]

            collection_name = mongodb_save_request["target_collection"]
            knowledge_document = mongodb_save_request["knowledge_document"]

            collection = db[collection_name]

            insert_result = collection.insert_one(knowledge_document)

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

        finally:
            if client:
                client.close()

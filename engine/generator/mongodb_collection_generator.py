import os
from pymongo import MongoClient
from dotenv import load_dotenv


class MongoDBCollectionGenerator:
    """
    MongoDB Collection Generator

    MongoDB Collection 존재 여부를 확인하고,
    없으면 생성한다.
    """

    def __init__(self):
        load_dotenv()

        self.mongodb_uri = os.getenv("MONGODB_URI")
        self.mongodb_database = os.getenv(
            "MONGODB_DATABASE",
            "vm_project_v7"
        )

    def save(self, mongodb_collection_request):
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
                "status": "SUCCESS"
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
                "message": str(ex)
            }

        finally:
            if client:
                client.close()
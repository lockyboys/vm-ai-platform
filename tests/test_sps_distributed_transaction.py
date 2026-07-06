import os
from datetime import datetime

from dotenv import load_dotenv
from pymongo import MongoClient

from urllib.parse import quote_plus
from core.database.database_manager import DatabaseManager
from core.identifier.identifier_engine import IdentifierEngine
from core.transaction.sps_distributed_transaction import SpsDistributedTransaction


# def get_mongodb_client():
#     load_dotenv()

#     host = os.getenv("MONGODB_HOST", "127.0.0.1")
#     port = int(os.getenv("MONGODB_PORT", "27017"))
#     user = os.getenv("MONGODB_USER")
#     password = os.getenv("MONGODB_PASSWORD")
#     auth_db = os.getenv("MONGODB_AUTH_DATABASE", "admin")

#     # if user and password:
#     #     uri = f"mongodb://{user}:{password}@{host}:{port}/?authSource={auth_db}"
#     # else:
#     #     uri = f"mongodb://{host}:{port}"

#     if user and password:
#         user = quote_plus(user)
#         password = quote_plus(password)
#         uri = (
#             f"mongodb://{user}:{password}"
#             f"@{host}:{port}/?authSource={auth_db}"
#         )
#     else:
#         uri = f"mongodb://{host}:{port}"

#     return MongoClient(uri)

def get_mongodb_client():
    load_dotenv()

    host = os.getenv("MONGODB_HOST", "127.0.0.1")
    port = int(os.getenv("MONGODB_PORT", "27017"))
    user = os.getenv("MONGODB_USER")
    password = os.getenv("MONGODB_PASSWORD")
    auth_db = os.getenv("MONGODB_AUTH_DATABASE", "admin")

    if user and password:
        uri = (
            f"mongodb://{quote_plus(user)}:{quote_plus(password)}"
            f"@{host}:{port}/?authSource={quote_plus(auth_db)}"
        )
    else:
        uri = f"mongodb://{host}:{port}"

    return MongoClient(uri)


def count_mariadb_rows(conn, object_attempt_id: str) -> int:
    sql = """
        SELECT COUNT(*) AS row_count
        FROM sp_object_execution_link
        WHERE object_attempt_id = %s
    """

    with conn.cursor() as cursor:
        cursor.execute(sql, (object_attempt_id,))
        row = cursor.fetchone()

    return int(row["row_count"])

def clean(value):

    if value is None:
        return ""

    value = value.strip()

    if value.startswith("'") and value.endswith("'"):
        value = value[1:-1]

    if value.startswith('"') and value.endswith('"'):
        value = value[1:-1]

    return value

def count_mongodb_docs(mongo_client, database_name: str, collection_name: str, object_attempt_id: str) -> int:
    collection = mongo_client[database_name][collection_name]
    return collection.count_documents({"object_attempt_id": object_attempt_id})


def main():
    print("SPS Distributed Transaction Test")

    database_manager = DatabaseManager()
    mariadb_conn = database_manager.get_connection("STORY")
    mongo_client = get_mongodb_client()

    identifier_engine = IdentifierEngine(
        sequence_database_role_code="STORY",
        block_size=10,
        database_manager=database_manager,
    )

    object_attempt_id = identifier_engine.generate_identifier(
        identifier_target_code="OBJECT",
        created_by="SYSTEM",
        program_id="test_sps_distributed_transaction.py",
    )

    object_id = "OB_2026_00001"

    mongodb_database_name = os.getenv("SPS_TEST_MONGODB_DATABASE", "sps_test")
    mongodb_collection_name = os.getenv("SPS_TEST_MONGODB_COLLECTION", "distributed_transaction_test")

    try:
        with SpsDistributedTransaction(
            mariadb_connection=mariadb_conn,
            mongodb_client=mongo_client,
        ) as tx:

            insert_sql = """
                INSERT INTO sp_object_execution_link (
                    object_attempt_id,
                    object_id,
                    target_object_id,
                    execution_link_type_code,
                    mongodb_database_id,
                    mongodb_collection_id,
                    mongodb_document_master_id,
                    created_by,
                    created_dt,
                    updated_by,
                    updated_dt,
                    program_id
                )
                VALUES (
                    %s, %s, %s,
                    'MONGODB',
                    %s, %s, %s,
                    'SYSTEM',
                    NOW(),
                    'SYSTEM',
                    NOW(),
                    'test_sps_distributed_transaction.py'
                )
            """

            with mariadb_conn.cursor() as cursor:
                cursor.execute(
                    insert_sql,
                    (
                        object_attempt_id,
                        object_id,
                        object_id,
                        mongodb_database_name,
                        mongodb_collection_name,
                        object_attempt_id,
                    ),
                )

            document = {
                "object_attempt_id": object_attempt_id,
                "object_id": object_id,
                "test_type": "SPS_DISTRIBUTED_TRANSACTION",
                "created_at": datetime.now().isoformat(),
                "message": "This document should be removed by compensation.",
            }

            tx.insert_mongodb_document(
                database_name=mongodb_database_name,
                collection_name=mongodb_collection_name,
                document=document,
                compensation_filter={"object_attempt_id": object_attempt_id},
            )

            print("Forced failure occurred")
            raise RuntimeError("Forced failure for SPS distributed transaction test")

    except RuntimeError as exc:
        print(f"Caught expected exception: {exc}")

    mariadb_remaining = count_mariadb_rows(mariadb_conn, object_attempt_id)
    mongodb_remaining = count_mongodb_docs(
        mongo_client=mongo_client,
        database_name=mongodb_database_name,
        collection_name=mongodb_collection_name,
        object_attempt_id=object_attempt_id,
    )

    print(f"MariaDB remaining rows: {mariadb_remaining}")
    print(f"MongoDB remaining docs: {mongodb_remaining}")

    if mariadb_remaining != 0:
        raise AssertionError("MariaDB rollback failed.")

    if mongodb_remaining != 0:
        raise AssertionError("MongoDB compensation failed.")

    mariadb_conn.close()
    mongo_client.close()

    print("SPS Distributed Transaction test completed successfully.")


if __name__ == "__main__":
    main()
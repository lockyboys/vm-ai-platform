"""Backfill SPS source metadata for the existing Hyundai pet-policy payload documents.

This migration intentionally uses the registered source-table/source-identifier
selector path because no insurance-specific contract_code is registered.
"""
from __future__ import annotations

import argparse
import json
import os
from datetime import datetime, timezone

from pymongo import MongoClient


COLLECTION = "insurance_policy_terms_payload"
SOURCE_FILE = "(무)현대해상굿앤굿우리펫보험(Hi2601) 1종_약관.pdf"
SOURCE_TABLE = "insurance_policy_terms_payload"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()

    uri = os.getenv("MONGODB_URI") or os.getenv("HEALTH_COMPANION_MONGODB_URI")
    database_name = os.getenv("MONGODB_DATABASE", "health_companion_ai")
    if not uri:
        raise RuntimeError("MONGODB_URI or HEALTH_COMPANION_MONGODB_URI is required")

    client = MongoClient(uri, serverSelectionTimeoutMS=10000)
    try:
        collection = client[database_name][COLLECTION]
        docs = list(collection.find(
            {"source_file": SOURCE_FILE},
            {"_id": 1, "document_id": 1, "_sps": 1},
        ))
        plan = []
        for doc in docs:
            document_id = doc.get("document_id")
            if not document_id:
                raise RuntimeError(f"document_id missing for _id={doc.get('_id')}")
            plan.append({
                "_id": str(doc["_id"]),
                "document_id": document_id,
                "before_sps": doc.get("_sps"),
                "set": {
                    "_sps.source_table_name": SOURCE_TABLE,
                    "_sps.source_identifier_column_name": "document_id",
                    "_sps.source_identifier": document_id,
                    "_sps.schema_version": "v1.0",
                },
            })

        if args.apply:
            now = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
            for item in plan:
                collection.update_one(
                    {"_id": next(d["_id"] for d in docs if str(d["_id"]) == item["_id"])},
                    {"$set": {**item["set"], "_sps.metadata_updated_dt": now,
                              "_sps.metadata_updated_by": "CODEX"}},
                )

        print(json.dumps({
            "apply": args.apply,
            "source_file": SOURCE_FILE,
            "matched": len(plan),
            "updated": len(plan) if args.apply else 0,
            "selector": {"source_table_name": SOURCE_TABLE, "source_identifier": "document_id"},
        }, ensure_ascii=False))
        return 0
    finally:
        client.close()


if __name__ == "__main__":
    raise SystemExit(main())

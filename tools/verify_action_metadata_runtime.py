"""Verify Rule -> Action Metadata -> Verified Query -> Stored Procedure without new data."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from common.database import CommonDatabase
from engine.runtime.rule_action_runtime import RuleActionRuntime
from repository.story.sp_object_metadata_repository import SpObjectMetadataRepository


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--rule-id", required=True)
    parser.add_argument("--object-code", required=True)
    parser.add_argument("--client-ip", required=True)
    args = parser.parse_args()

    common_database = CommonDatabase(database_role="COMMON")
    story_database = CommonDatabase(database_role="STORY_PLATFORM")
    try:
        parameters = SpObjectMetadataRepository(story_database).get_active_by_code(
            args.object_code
        )
        parameters["client_ip"] = args.client_ip

        result = RuleActionRuntime.from_common_repository(
            common_database
        ).execute(args.rule_id, parameters)

        if not result or any(
            action["result"][0]["registered_yn"] != "N" for action in result
        ):
            raise RuntimeError("Existing object verification did not return registered_yn=N.")

        print(json.dumps({"status": "SUCCESS", "result": result}, ensure_ascii=False, default=str))
    finally:
        common_database.close()
        story_database.close()


if __name__ == "__main__":
    main()

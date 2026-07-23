"""Verify one real PDF/image Work execution and display stored Repository rows."""
from __future__ import annotations

import argparse
from pathlib import Path

from common.database import CommonDatabase
from engine.processor.work.file_work_service import FileWorkService


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("source_file")
    parser.add_argument("--requested-by", required=True)
    parser.add_argument("--client-ip", default="127.0.0.1")
    args = parser.parse_args()

    result = FileWorkService().process(
        upload_path=Path(args.source_file),
        requested_by=args.requested_by,
        client_ip=args.client_ip,
    )
    database = CommonDatabase(database_role="STORY_PLATFORM")
    try:
        session_row = database.fetch_one(
            """
            SELECT work_session_id, worker_object_id, work_type_code, work_status_code,
                   work_result_code, started_dt, completed_dt
            FROM sp_work_session
            WHERE work_session_id = %s
            """,
            (result.work_session_id,),
        )
        item_row = database.fetch_one(
            """
            SELECT work_item_id, work_session_id, work_step_no, work_status_code,
                   work_result_code, started_dt, completed_dt
            FROM sp_work_item
            WHERE work_item_id = %s
            """,
            (result.work_item_id,),
        )
        asset_rows = database.fetch_all(
            """
            SELECT work_asset_id, work_item_id, asset_type_code, asset_name,
                   asset_size, asset_status_code
            FROM sp_work_asset
            WHERE work_item_id = %s
            ORDER BY asset_type_code
            """,
            (result.work_item_id,),
        )
    finally:
        database.close()

    if not session_row or not item_row or len(asset_rows) != 4:
        raise RuntimeError("Work Repository row verification failed.")

    print("FILE WORK DEMO VERIFICATION: OK")
    print({"work_session": session_row})
    print({"work_item": item_row})
    print({"work_assets": asset_rows})
    print({"docx_path": str(result.docx_path)})
    print({"report_path": str(result.report_path)})
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

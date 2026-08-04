"""Issue and connect one UI Screen Identifier through SPS Repository metadata.

File Story:
    UI Runtime의 화면 행을 SP_UI_SCREEN Object metadata와 Identifier Engine으로
    연결한다.

Change History:
    20260803 | Codex | menu_code 입력 행의 ui_screen_id를 Repository metadata,
    Lifecycle 상태 및 Identifier Engine으로 멱등 발급·연결한다.

Repository First:
    - SP_UI_SCREEN의 target_identifier_field, Identifier Target, Sequence 정책은
      Common Repository Object Definition과 sp_object에서 조회한다.
    - menu_code는 호출 인자이며 UI screen ID는 조합하거나 하드코딩하지 않는다.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from common.database import CommonDatabase
from engine.identifier_engine import IdentifierEngine
from engine.object_definition_engine import ObjectDefinitionEngine


OBJECT_DEFINITION_GROUP_CODE = "UI_RUNTIME_OBJECT_DEFINITION"
SCREEN_OBJECT_CODE = "SP_UI_SCREEN"
PROGRAM_ID = "UI_SCREEN_IDENTIFIER_CONNECTOR_20260803"


def _load_screen_contract(common_database: CommonDatabase) -> dict[str, object]:
    row = common_database.fetch_one(
        """
        SELECT common_code_json
        FROM cm_common_code
        WHERE group_code = %s
          AND code = %s
          AND status_code = 'ACTIVE'
          AND deleted_dt IS NULL
        LIMIT 1
        """,
        (OBJECT_DEFINITION_GROUP_CODE, SCREEN_OBJECT_CODE),
    )
    if not row:
        raise LookupError("UI Screen Object Definition contract not found.")
    return json.loads(str(row["common_code_json"]))


def _load_screen_object(story_database: CommonDatabase) -> dict[str, object]:
    row = story_database.fetch_one(
        """
        SELECT
            object_id, object_code, object_level, lifecycle_id,
            target_identifier_field, identifier_target_code,
            sequence_scope_code, sequence_length, status_code, active_yn
        FROM sp_object
        WHERE object_code = %s
          AND status_code = 'ACTIVE'
          AND active_yn = 'Y'
          AND deleted_dt IS NULL
        LIMIT 1
        """,
        (SCREEN_OBJECT_CODE,),
    )
    if not row:
        raise LookupError("Active SP_UI_SCREEN Object metadata not found.")
    if not row["lifecycle_id"]:
        raise LookupError("SP_UI_SCREEN Lifecycle registration is required.")
    return dict(row)


def _synchronize_target_identifier_field(
    story_database: CommonDatabase,
    contract: dict[str, object],
    screen_object: dict[str, object],
) -> None:
    target_field = str(contract["target_identifier_field"])
    if screen_object["target_identifier_field"] == target_field:
        return
    affected_rows = story_database.execute(
        """
        UPDATE sp_object
        SET target_identifier_field = %s,
            updated_by = 'SYSTEM',
            updated_dt = CURRENT_TIMESTAMP,
            program_id = %s
        WHERE object_id = %s
          AND object_code = %s
          AND deleted_dt IS NULL
        """,
        (
            target_field,
            PROGRAM_ID,
            screen_object["object_id"],
            SCREEN_OBJECT_CODE,
        ),
    )
    if affected_rows != 1:
        raise RuntimeError("SP_UI_SCREEN target identifier field synchronization failed.")


def _load_menu(common_database: CommonDatabase, menu_code: str) -> dict[str, object]:
    row = common_database.fetch_one(
        """
        SELECT menu_code, menu_name, ui_screen_id, status_code
        FROM ui_menu
        WHERE menu_code = %s
          AND status_code = 'ACTIVE'
          AND deleted_dt IS NULL
        LIMIT 1
        """,
        (menu_code,),
    )
    if not row:
        raise LookupError(f"Active UI Menu not found: menu_code={menu_code}")
    return dict(row)


def _ensure_sequence_metadata(
    story_database: CommonDatabase,
    screen_object: dict[str, object],
) -> None:
    identifier_engine = IdentifierEngine(story_database)
    object_engine = ObjectDefinitionEngine(story_database)
    now = datetime.now()
    blueprint = identifier_engine.load_identifier_blueprint(
        int(screen_object["object_level"])
    )
    sequence_date = identifier_engine.resolve_sequence_date(
        str(screen_object["sequence_scope_code"]),
        now,
    )
    story_database.begin()
    try:
        object_engine._ensure_sequence_metadata(
            screen_object,
            blueprint,
            sequence_date,
            int(screen_object["sequence_length"]),
            now,
        )
        story_database.commit()
    except Exception:
        story_database.rollback()
        raise


def connect_screen_identifier(menu_code: str) -> dict[str, object]:
    common_database = CommonDatabase(database_role="COMMON")
    story_database = CommonDatabase(database_role="STORY_PLATFORM")
    try:
        contract = _load_screen_contract(common_database)
        if contract.get("object_code") != SCREEN_OBJECT_CODE:
            raise ValueError("UI Screen contract Object Code mismatch.")
        if contract.get("target_identifier_field") != "ui_screen_id":
            raise ValueError("UI Screen contract must target ui_screen_id.")

        screen_object = _load_screen_object(story_database)
        _synchronize_target_identifier_field(
            story_database, contract, screen_object
        )
        menu = _load_menu(common_database, menu_code)
        if menu["ui_screen_id"]:
            return {
                "status": "ALREADY_CONNECTED",
                "menu_code": menu["menu_code"],
                "menu_name": menu["menu_name"],
                "ui_screen_id": menu["ui_screen_id"],
                "screen_object_id": screen_object["object_id"],
            }

        _ensure_sequence_metadata(story_database, screen_object)
        ui_screen_id = IdentifierEngine(story_database).generate(
            SCREEN_OBJECT_CODE
        )

        common_database.begin()
        try:
            affected_rows = common_database.execute(
                """
                UPDATE ui_menu
                SET ui_screen_id = %s,
                    updated_by = 'SYSTEM',
                    updated_dt = CURRENT_TIMESTAMP,
                    program_id = %s
                WHERE menu_code = %s
                  AND ui_screen_id IS NULL
                  AND status_code = 'ACTIVE'
                  AND deleted_dt IS NULL
                """,
                (ui_screen_id, PROGRAM_ID, menu_code),
            )
            if affected_rows != 1:
                raise RuntimeError(
                    "UI Screen Identifier connection failed or was concurrently updated."
                )
            common_database.commit()
        except Exception:
            common_database.rollback()
            raise

        return {
            "status": "CONNECTED",
            "menu_code": menu["menu_code"],
            "menu_name": menu["menu_name"],
            "ui_screen_id": ui_screen_id,
            "screen_object_id": screen_object["object_id"],
        }
    finally:
        story_database.close()
        common_database.close()


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--menu-code", required=True)
    args = parser.parse_args()
    print(json.dumps(connect_screen_identifier(args.menu_code), ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

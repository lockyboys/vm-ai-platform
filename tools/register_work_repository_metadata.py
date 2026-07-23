"""Register Work Repository metadata required by the file-ingestion demonstration.

Run:
    python -m tools.register_work_repository_metadata

This bootstrap is idempotent. It registers the common-code vocabulary first, then
registers the Work Session, Work Item and Work Asset table Objects through the
Object Definition Engine. It does not create a demonstration work record.
"""

from __future__ import annotations

from typing import Final

from common.database import CommonDatabase
from engine.object_definition_engine import ObjectDefinitionEngine


PROGRAM_ID: Final[str] = "WORK_REPOSITORY_METADATA_REGISTRAR"
ACTOR: Final[str] = "SYSTEM"
CLIENT_IP: Final[str] = "127.0.0.1"

COMMON_CODE_GROUPS: Final[tuple[dict[str, object], ...]] = (
    {
        "group_code": "WORK_TYPE",
        "group_name": "작업 유형",
        "group_description": "Work Session이 수행하는 업무 흐름 유형을 관리한다.",
        "sort_no": 350,
        "codes": (
            ("FILE_INGESTION", "파일 수집", "파일 업로드, 분석, 저장 및 보고서 생성을 수행하는 작업.", 10),
        ),
    },
    {
        "group_code": "WORK_STATUS",
        "group_name": "작업 상태",
        "group_description": "Work Session과 Work Item의 처리 생명주기 상태를 관리한다.",
        "sort_no": 351,
        "codes": (
            ("RECEIVED", "접수", "사용자 파일을 접수한 상태.", 10),
            ("PROCESSING", "처리 중", "파일 분석 또는 산출물 생성을 수행 중인 상태.", 20),
            ("COMPLETED", "완료", "모든 처리와 Repository 저장이 성공한 상태.", 30),
            ("FAILED", "실패", "처리 또는 저장이 실패하여 완료되지 않은 상태.", 40),
        ),
    },
    {
        "group_code": "WORK_RESULT",
        "group_name": "작업 결과",
        "group_description": "완료된 Work의 최종 성공 또는 실패 판정을 관리한다.",
        "sort_no": 352,
        "codes": (
            ("SUCCESS", "성공", "요청한 처리와 저장 검증이 모두 성공한 결과.", 10),
            ("FAILED", "실패", "요청한 처리 또는 저장 검증에 실패한 결과.", 20),
        ),
    },
    {
        "group_code": "ASSET_TYPE",
        "group_name": "작업 자산 유형",
        "group_description": "Work Item에 연결되는 원본, 추출 결과 및 산출물의 유형을 관리한다.",
        "sort_no": 353,
        "codes": (
            ("SOURCE_FILE", "원본 파일", "사용자가 업로드한 PDF 또는 이미지 원본.", 10),
            ("EXTRACTED_TEXT", "추출 텍스트", "PDF 파싱 또는 OCR로 생성한 텍스트.", 20),
            ("DOCX_REPORT", "DOCX 리포트", "처리 결과를 기록한 Microsoft Word 보고서.", 30),
            ("MARKDOWN_REPORT", "Markdown 리포트", "실행 및 저장 검증 결과를 기록한 Markdown 보고서.", 40),
        ),
    },
    {
        "group_code": "ASSET_STATUS",
        "group_name": "작업 자산 상태",
        "group_description": "Work Asset의 저장 및 사용 가능 상태를 관리한다.",
        "sort_no": 354,
        "codes": (
            ("STORED", "저장됨", "Repository가 자산 경로와 Metadata를 정상 저장한 상태.", 10),
            ("FAILED", "저장 실패", "자산 저장 또는 검증에 실패한 상태.", 20),
        ),
    },
)

TABLE_OBJECTS: Final[tuple[dict[str, object], ...]] = (
    {
        "object_code": "WORK_SESSION",
        "object_name": "Work Session",
        "object_description": "파일 기반 처리 흐름의 최상위 Work Session을 관리하는 Table Object.",
        "target_identifier_field": "work_session_id",
        "sort_no": 60,
    },
    {
        "object_code": "WORK_ITEM",
        "object_name": "Work Item",
        "object_description": "Work Session의 파일 분석 및 산출물 생성 단위를 관리하는 Table Object.",
        "target_identifier_field": "work_item_id",
        "sort_no": 61,
    },
    {
        "object_code": "WORK_ASSET",
        "object_name": "Work Asset",
        "object_description": "원본 파일, 추출 텍스트 및 보고서 산출물을 추적하는 Table Object.",
        "target_identifier_field": "work_asset_id",
        "sort_no": 62,
    },
    {
        "object_code": "EXECUTION_HISTORY",
        "object_name": "Execution History",
        "object_description": "Runtime의 Repository·MongoDB 실행 결과를 추적하는 Table Object.",
        "target_identifier_field": "execution_history_id",
        "sort_no": 63,
        "identifier_target_code": "EG",
    },
)


def upsert_common_code_repository(database: CommonDatabase) -> None:
    """Register groups and values before an Engine may reference them."""
    database.begin()
    try:
        for group in COMMON_CODE_GROUPS:
            database.execute(
                """
                INSERT INTO cm_common_code_group
                (
                    group_code, group_name, group_description, sort_no,
                    status_code, reserved_yn, system_yn,
                    created_by, updated_by, client_ip, program_id,
                    lifecycle_status_code
                )
                VALUES (%s, %s, %s, %s, 'ACTIVE', 'N', 'Y', %s, %s, %s, %s, 'CREATE_MAINTAIN')
                ON DUPLICATE KEY UPDATE
                    group_name = VALUES(group_name),
                    group_description = VALUES(group_description),
                    sort_no = VALUES(sort_no),
                    status_code = 'ACTIVE',
                    updated_by = VALUES(updated_by),
                    client_ip = VALUES(client_ip),
                    program_id = VALUES(program_id),
                    lifecycle_status_code = 'CREATE_MAINTAIN'
                """,
                (
                    group["group_code"],
                    group["group_name"],
                    group["group_description"],
                    group["sort_no"],
                    ACTOR,
                    ACTOR,
                    CLIENT_IP,
                    PROGRAM_ID,
                ),
            )
            for code, code_name, description, sort_no in group["codes"]:
                database.execute(
                    """
                    INSERT INTO cm_common_code
                    (
                        group_code, code, code_name, common_code_description,
                        sort_no, status_code, created_by, updated_by,
                        client_ip, program_id, lifecycle_status_code
                    )
                    VALUES (%s, %s, %s, %s, %s, 'ACTIVE', %s, %s, %s, %s, 'CREATE_MAINTAIN')
                    ON DUPLICATE KEY UPDATE
                        code_name = VALUES(code_name),
                        common_code_description = VALUES(common_code_description),
                        sort_no = VALUES(sort_no),
                        status_code = 'ACTIVE',
                        updated_by = VALUES(updated_by),
                        client_ip = VALUES(client_ip),
                        program_id = VALUES(program_id),
                        lifecycle_status_code = 'CREATE_MAINTAIN'
                    """,
                    (
                        group["group_code"],
                        code,
                        code_name,
                        description,
                        sort_no,
                        ACTOR,
                        ACTOR,
                        CLIENT_IP,
                        PROGRAM_ID,
                    ),
                )
        database.commit()
    except Exception:
        database.rollback()
        raise


def register_table_objects(database: CommonDatabase) -> list[dict[str, object]]:
    """Register Work tables at Object Level 3 using the official Engine."""
    engine = ObjectDefinitionEngine(database=database)
    results: list[dict[str, object]] = []
    for table_object in TABLE_OBJECTS:
        results.append(
            engine.create(
                {
                    **table_object,
                    "business_code": "SP",
                    "domain_code": "RP",
                    "object_type_code": "TABLE",
                    "object_level": 3,
                    "status_code": "ACTIVE",
                    "active_yn": "Y",
                    "version_num": "v1.0",
                    "sequence_scope_code": "DAILY",
                    "sequence_length": 5,
                    "identifier_target_code": table_object.get("identifier_target_code", "OB"),
                    "created_by": ACTOR,
                    "updated_by": ACTOR,
                    "client_ip": CLIENT_IP,
                    "program_id": PROGRAM_ID,
                }
            )
        )
    return results


def verify_registration(
    common_database: CommonDatabase,
    story_database: CommonDatabase,
) -> tuple[list[dict[str, object]], list[dict[str, object]]]:
    group_rows = common_database.fetch_all(
        """
        SELECT group_code, group_name, status_code
        FROM cm_common_code_group
        WHERE group_code IN ('WORK_TYPE', 'WORK_STATUS', 'WORK_RESULT', 'ASSET_TYPE', 'ASSET_STATUS')
        ORDER BY sort_no, group_code
        """
    )
    object_rows = story_database.fetch_all(
        """
        SELECT object_id, object_code, object_level, object_type_code,
               target_identifier_field, identifier_target_code
        FROM sp_object
        WHERE object_code IN ('WORK_SESSION', 'WORK_ITEM', 'WORK_ASSET', 'EXECUTION_HISTORY')
          AND deleted_dt IS NULL
        ORDER BY object_code
        """
    )
    if len(group_rows) != len(COMMON_CODE_GROUPS):
        raise RuntimeError(f"Common-code group verification failed: {group_rows!r}")
    if len(object_rows) != len(TABLE_OBJECTS):
        raise RuntimeError(f"Table Object verification failed: {object_rows!r}")
    return group_rows, object_rows


def main() -> int:
    common_database = CommonDatabase(database_role="COMMON")
    story_database = CommonDatabase(database_role="STORY_PLATFORM")
    try:
        upsert_common_code_repository(common_database)
        registration_results = register_table_objects(story_database)
        group_rows, object_rows = verify_registration(common_database, story_database)
        print("WORK REPOSITORY METADATA REGISTRATION: OK")
        print({"common_code_groups": group_rows})
        print({"table_objects": object_rows})
        print({"object_registration": registration_results})
        return 0
    finally:
        common_database.close()
        story_database.close()


if __name__ == "__main__":
    raise SystemExit(main())

/*
 * File Story
 * UI Runtime의 Screen, Menu, Action, Permission 분류를 Common Repository에 등록한다.
 *
 * Change History
 * 20260730 | Codex | UI Runtime 공통코드 Group을 멱등 등록한다.
 *
 * DB 구조는 변경하지 않는다.
 */
USE te_common;

START TRANSACTION;

SET @program_id = 'UI_RUNTIME_COMMON_CODE_GROUP_20260730';
SET @created_by = 'SYSTEM';

INSERT INTO cm_common_code_group
(
    group_code,
    group_name,
    group_description,
    sort_no,
    status_code,
    reserved_yn,
    system_yn,
    created_by,
    updated_by,
    program_id,
    lifecycle_status_code
)
VALUES
(
    'UI_SCREEN_TYPE',
    'UI Screen Type',
    'UI Screen Object가 제공하는 화면 표현과 업무 상호작용 유형을 관리한다.',
    310,
    'ACTIVE',
    'Y',
    'Y',
    @created_by,
    @created_by,
    @program_id,
    'CREATE_MAINTAIN'
),
(
    'UI_MENU_TYPE',
    'UI Menu Type',
    'UI Menu Object의 계층 역할과 탐색 구조 유형을 관리한다.',
    320,
    'ACTIVE',
    'Y',
    'Y',
    @created_by,
    @created_by,
    @program_id,
    'CREATE_MAINTAIN'
),
(
    'UI_ACTION_TYPE',
    'UI Action Type',
    'UI Action Object가 실행하는 사용자 요청과 Runtime 행위 유형을 관리한다.',
    330,
    'ACTIVE',
    'Y',
    'Y',
    @created_by,
    @created_by,
    @program_id,
    'CREATE_MAINTAIN'
),
(
    'UI_PERMISSION_TYPE',
    'UI Permission Type',
    'UI Permission Object가 부여하는 UI Runtime 접근 권한 유형을 관리한다.',
    340,
    'ACTIVE',
    'Y',
    'Y',
    @created_by,
    @created_by,
    @program_id,
    'CREATE_MAINTAIN'
)
ON DUPLICATE KEY UPDATE
    group_name = VALUES(group_name),
    group_description = VALUES(group_description),
    sort_no = VALUES(sort_no),
    status_code = VALUES(status_code),
    reserved_yn = VALUES(reserved_yn),
    system_yn = VALUES(system_yn),
    updated_dt = CURRENT_TIMESTAMP,
    updated_by = VALUES(updated_by),
    program_id = VALUES(program_id),
    lifecycle_status_code = VALUES(lifecycle_status_code);

SELECT
    group_code,
    group_name,
    sort_no,
    status_code,
    reserved_yn,
    system_yn,
    lifecycle_status_code
FROM cm_common_code_group
WHERE group_code IN
(
    'UI_SCREEN_TYPE',
    'UI_MENU_TYPE',
    'UI_ACTION_TYPE',
    'UI_PERMISSION_TYPE'
)
  AND deleted_dt IS NULL
ORDER BY sort_no, group_code;

COMMIT;

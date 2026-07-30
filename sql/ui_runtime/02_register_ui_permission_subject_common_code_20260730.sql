/*
 * File Story
 * UI Permission 레코드의 적용 대상을 Common Repository에 등록한다.
 *
 * Change History
 * 20260730 | Codex | Member와 Rule을 UI Permission Subject Type 공통 코드로 멱등 등록한다.
 *
 * DB 구조는 변경하지 않는다.
 */
USE te_common;

START TRANSACTION;

SET @program_id = 'UI_PERMISSION_SUBJECT_COMMON_CODE_20260730';
SET @created_by = 'SYSTEM';
SET @client_ip = '127.0.0.1';

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
    'UI_PERMISSION_SUBJECT_TYPE',
    'UI Permission Subject Type',
    'UI Permission 레코드가 적용되는 보안 주체 유형을 관리한다.',
    350,
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

INSERT INTO cm_common_code
(
    group_code, code, code_name, common_code_description, sort_no, status_code,
    created_by, updated_by, client_ip, program_id, common_code_json, lifecycle_status_code
)
VALUES
(
    'UI_PERMISSION_SUBJECT_TYPE',
    'MEMBER',
    'Member',
    'cm_member의 특정 Member에게 UI Permission을 직접 적용하는 대상 유형.',
    10,
    'ACTIVE',
    @created_by,
    @created_by,
    @client_ip,
    @program_id,
    JSON_OBJECT('subject_repository_object', 'CM_MEMBER', 'subject_table', 'cm_member'),
    'CREATE_MAINTAIN'
),
(
    'UI_PERMISSION_SUBJECT_TYPE',
    'RULE',
    'Rule',
    'rl_rule의 Rule 평가 결과를 통해 UI Permission을 적용하는 대상 유형.',
    20,
    'ACTIVE',
    @created_by,
    @created_by,
    @client_ip,
    @program_id,
    JSON_OBJECT('subject_repository_object', 'RL_RULE', 'subject_table', 'rl_rule'),
    'CREATE_MAINTAIN'
)
ON DUPLICATE KEY UPDATE
    code_name = VALUES(code_name),
    common_code_description = VALUES(common_code_description),
    sort_no = VALUES(sort_no),
    status_code = VALUES(status_code),
    deleted_by = NULL,
    deleted_dt = NULL,
    updated_dt = CURRENT_TIMESTAMP,
    updated_by = VALUES(updated_by),
    client_ip = VALUES(client_ip),
    program_id = VALUES(program_id),
    common_code_json = VALUES(common_code_json),
    lifecycle_status_code = VALUES(lifecycle_status_code);

COMMIT;

SELECT
    group_code,
    code,
    code_name,
    common_code_json,
    status_code,
    lifecycle_status_code
FROM cm_common_code
WHERE group_code = 'UI_PERMISSION_SUBJECT_TYPE'
  AND deleted_dt IS NULL
ORDER BY sort_no, code;

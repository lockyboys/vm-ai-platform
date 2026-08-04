/*
 * File Story
 * UI Runtime Repository Object Definition을 Common Repository metadata로 등록한다.
 *
 * Change History
 * 20260803 | Codex | UI Screen Instance Identifier 대상 필드를 ui_screen_id로 정합화한다.
 *
 * DB 구조 변경은 11_migrate_ui_screen_identifier_20260803.sql에서만 수행한다.
 */
USE te_common;

START TRANSACTION;

SET @program_id = 'UI_RUNTIME_OBJECT_DEFINITION_20260731';
SET @actor_id = 'SYSTEM';
SET @client_ip = '127.0.0.1';

INSERT INTO cm_common_code_group
(
    group_code, group_name, group_description, sort_no,
    status_code, reserved_yn, system_yn,
    created_by, updated_by, client_ip, program_id, lifecycle_status_code
)
VALUES
(
    'UI_RUNTIME_OBJECT_DEFINITION',
    'UI Runtime Object Definition',
    'UI Runtime Repository Object의 Identifier 발급과 등록에 사용하는 선언형 Engine 입력 계약을 관리한다.',
    350,
    'ACTIVE', 'Y', 'Y',
    @actor_id, @actor_id, @client_ip, @program_id, 'CREATE_MAINTAIN'
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
    client_ip = VALUES(client_ip),
    program_id = VALUES(program_id),
    lifecycle_status_code = VALUES(lifecycle_status_code);

INSERT INTO cm_common_code
(
    group_code, code, code_name, common_code_description, sort_no,
    status_code, created_by, updated_by, client_ip, program_id,
    common_code_json, lifecycle_status_code
)
VALUES
(
    'UI_RUNTIME_OBJECT_DEFINITION', 'SP_UI_SCREEN', 'UI Screen',
    'ui_menu.ui_screen_id를 화면 Instance Identifier로, 화면 표시 계약을 해석하는 UI Screen Repository Object 정의.',
    10, 'ACTIVE', @actor_id, @actor_id, @client_ip, @program_id,
    JSON_OBJECT(
        'object_code', 'SP_UI_SCREEN',
        'object_name', 'UI Screen',
        'object_description', 'COMMON.ui_menu의 ui_screen_id, menu_code, menu_name, menu_url, ui_screen_type_code, menu_sort_no를 화면 표시 계약으로 해석한다.',
        'business_code', 'SP', 'domain_code', 'RP', 'object_type_code', 'TABLE',
        'object_level', 3, 'sort_no', 10,
        'target_identifier_field', 'ui_screen_id',
        'identifier_target_code', 'OB',
        'sequence_scope_code', 'YEARLY', 'sequence_length', 5
    ),
    'CREATE_MAINTAIN'
),
(
    'UI_RUNTIME_OBJECT_DEFINITION', 'SP_UI_MENU', 'UI Menu',
    'ui_menu를 공식 SSOT로 해석하는 UI Menu Repository Object 정의.',
    20, 'ACTIVE', @actor_id, @actor_id, @client_ip, @program_id,
    JSON_OBJECT(
        'object_code', 'SP_UI_MENU',
        'object_name', 'UI Menu',
        'object_description', 'COMMON.ui_menu의 menu_code, menu_name, menu_url, ui_menu_type_code, menu_sort_no를 UI Menu Repository의 공식 SSOT로 해석한다.',
        'business_code', 'SP', 'domain_code', 'RP', 'object_type_code', 'TABLE',
        'object_level', 3, 'sort_no', 20,
        'target_identifier_field', 'object_id',
        'identifier_target_code', 'OB',
        'sequence_scope_code', 'YEARLY', 'sequence_length', 5
    ),
    'CREATE_MAINTAIN'
),
(
    'UI_RUNTIME_OBJECT_DEFINITION', 'SP_UI_ACTION', 'UI Action',
    'ui_menu_action을 UI Action 계약으로 해석하는 Repository Object 정의.',
    30, 'ACTIVE', @actor_id, @actor_id, @client_ip, @program_id,
    JSON_OBJECT(
        'object_code', 'SP_UI_ACTION',
        'object_name', 'UI Action',
        'object_description', 'COMMON.ui_menu_action의 menu_code, button_code, ui_action_type_code, query_id를 UI Action 계약으로 해석한다.',
        'business_code', 'SP', 'domain_code', 'RP', 'object_type_code', 'TABLE',
        'object_level', 3, 'sort_no', 30,
        'target_identifier_field', 'object_id',
        'identifier_target_code', 'OB',
        'sequence_scope_code', 'YEARLY', 'sequence_length', 5
    ),
    'CREATE_MAINTAIN'
),
(
    'UI_RUNTIME_OBJECT_DEFINITION', 'SP_UI_PERMISSION', 'UI Permission',
    'ui_menu_action_permission을 행 기반 권한 계약으로 해석하는 Repository Object 정의.',
    40, 'ACTIVE', @actor_id, @actor_id, @client_ip, @program_id,
    JSON_OBJECT(
        'object_code', 'SP_UI_PERMISSION',
        'object_name', 'UI Permission',
        'object_description', 'COMMON.ui_menu_action_permission의 Action별 Member 또는 Rule 권한 행과 permission_type_code를 UI Permission 계약으로 해석한다.',
        'business_code', 'SP', 'domain_code', 'RP', 'object_type_code', 'TABLE',
        'object_level', 3, 'sort_no', 40,
        'target_identifier_field', 'object_id',
        'identifier_target_code', 'OB',
        'sequence_scope_code', 'YEARLY', 'sequence_length', 5
    ),
    'CREATE_MAINTAIN'
)
ON DUPLICATE KEY UPDATE
    code_name = VALUES(code_name),
    common_code_description = VALUES(common_code_description),
    sort_no = VALUES(sort_no),
    status_code = VALUES(status_code),
    updated_dt = CURRENT_TIMESTAMP,
    updated_by = VALUES(updated_by),
    client_ip = VALUES(client_ip),
    program_id = VALUES(program_id),
    common_code_json = VALUES(common_code_json),
    lifecycle_status_code = VALUES(lifecycle_status_code);

SELECT
    code AS object_code,
    JSON_UNQUOTE(JSON_EXTRACT(common_code_json, '$.object_level')) AS object_level,
    JSON_UNQUOTE(JSON_EXTRACT(common_code_json, '$.identifier_target_code')) AS identifier_target_code,
    JSON_UNQUOTE(JSON_EXTRACT(common_code_json, '$.sequence_scope_code')) AS sequence_scope_code,
    JSON_UNQUOTE(JSON_EXTRACT(common_code_json, '$.sequence_length')) AS sequence_length
FROM cm_common_code
WHERE group_code = 'UI_RUNTIME_OBJECT_DEFINITION'
  AND status_code = 'ACTIVE'
  AND deleted_dt IS NULL
ORDER BY sort_no, code;

COMMIT;

/*
 * File Story
 * UI Runtime 분류값과 물리 Repository SSOT 연결을 Common Repository에 등록한다.
 *
 * Change History
 * 20260730 | Codex | UI Screen, Menu, Action, Permission 유형을 멱등 등록한다.
 *
 * DB 구조는 변경하지 않는다.
 */
USE te_common;

START TRANSACTION;

SET @program_id = 'UI_RUNTIME_COMMON_CODE_20260730';
SET @created_by = 'SYSTEM';
SET @client_ip = '127.0.0.1';

INSERT INTO cm_common_code
(
    group_code, code, code_name, common_code_description, sort_no, status_code,
    created_by, updated_by, client_ip, program_id, common_code_json, lifecycle_status_code
)
VALUES
('UI_SCREEN_TYPE', 'DASHBOARD', 'Dashboard', '핵심 업무 지표와 요약 정보를 제공하는 화면 유형.', 10, 'ACTIVE', @created_by, @created_by, @client_ip, @program_id, JSON_OBJECT('ui_runtime_object', 'SP_UI_SCREEN', 'source_database_role', 'COMMON', 'source_table', 'system_menu', 'render_mode', 'DASHBOARD'), 'CREATE_MAINTAIN'),
('UI_SCREEN_TYPE', 'DETAIL', 'Detail', '단일 업무 대상의 상세 정보와 연관 정보를 제공하는 화면 유형.', 20, 'ACTIVE', @created_by, @created_by, @client_ip, @program_id, JSON_OBJECT('ui_runtime_object', 'SP_UI_SCREEN', 'source_database_role', 'COMMON', 'source_table', 'system_menu', 'render_mode', 'DETAIL'), 'CREATE_MAINTAIN'),
('UI_SCREEN_TYPE', 'FORM', 'Form', '업무 데이터를 입력하거나 수정하는 화면 유형.', 30, 'ACTIVE', @created_by, @created_by, @client_ip, @program_id, JSON_OBJECT('ui_runtime_object', 'SP_UI_SCREEN', 'source_database_role', 'COMMON', 'source_table', 'system_menu', 'render_mode', 'FORM'), 'CREATE_MAINTAIN'),
('UI_SCREEN_TYPE', 'LIST', 'List', '복수 업무 대상을 조회, 검색, 정렬하는 화면 유형.', 40, 'ACTIVE', @created_by, @created_by, @client_ip, @program_id, JSON_OBJECT('ui_runtime_object', 'SP_UI_SCREEN', 'source_database_role', 'COMMON', 'source_table', 'system_menu', 'render_mode', 'LIST'), 'CREATE_MAINTAIN'),
('UI_MENU_TYPE', 'GROUP', 'Group', '하위 메뉴를 묶어 탐색 구조를 제공하는 메뉴 유형.', 10, 'ACTIVE', @created_by, @created_by, @client_ip, @program_id, JSON_OBJECT('ui_runtime_object', 'SP_UI_MENU', 'source_database_role', 'COMMON', 'source_table', 'system_menu', 'navigable_yn', 'N'), 'CREATE_MAINTAIN'),
('UI_MENU_TYPE', 'ITEM', 'Item', '특정 UI Screen으로 이동하는 실행 메뉴 유형.', 20, 'ACTIVE', @created_by, @created_by, @client_ip, @program_id, JSON_OBJECT('ui_runtime_object', 'SP_UI_MENU', 'source_database_role', 'COMMON', 'source_table', 'system_menu', 'navigable_yn', 'Y'), 'CREATE_MAINTAIN'),
('UI_MENU_TYPE', 'ROOT', 'Root', 'UI 메뉴 트리의 최상위 탐색 시작점 유형.', 30, 'ACTIVE', @created_by, @created_by, @client_ip, @program_id, JSON_OBJECT('ui_runtime_object', 'SP_UI_MENU', 'source_database_role', 'COMMON', 'source_table', 'system_menu', 'navigable_yn', 'Y'), 'CREATE_MAINTAIN'),
('UI_ACTION_TYPE', 'CREATE', 'Create', '새 업무 데이터를 생성하는 UI Action 유형.', 10, 'ACTIVE', @created_by, @created_by, @client_ip, @program_id, JSON_OBJECT('crud_type', 'CREATE', 'ui_runtime_object', 'SP_UI_ACTION', 'source_table', 'system_menu_button'), 'CREATE_MAINTAIN'),
('UI_ACTION_TYPE', 'DELETE', 'Delete', '업무 데이터를 논리 삭제하거나 삭제 요청을 실행하는 UI Action 유형.', 20, 'ACTIVE', @created_by, @created_by, @client_ip, @program_id, JSON_OBJECT('crud_type', 'DELETE', 'ui_runtime_object', 'SP_UI_ACTION', 'source_table', 'system_menu_button'), 'CREATE_MAINTAIN'),
('UI_ACTION_TYPE', 'EXECUTE', 'Execute', 'CRUD 외의 검증된 업무 Action을 실행하는 UI Action 유형.', 30, 'ACTIVE', @created_by, @created_by, @client_ip, @program_id, JSON_OBJECT('crud_type', 'EXECUTE', 'ui_runtime_object', 'SP_UI_ACTION', 'source_table', 'system_menu_button'), 'CREATE_MAINTAIN'),
('UI_ACTION_TYPE', 'READ', 'Read', '업무 데이터를 조회하는 UI Action 유형.', 40, 'ACTIVE', @created_by, @created_by, @client_ip, @program_id, JSON_OBJECT('crud_type', 'READ', 'ui_runtime_object', 'SP_UI_ACTION', 'source_table', 'system_menu_button'), 'CREATE_MAINTAIN'),
('UI_ACTION_TYPE', 'UPDATE', 'Update', '기존 업무 데이터를 변경하는 UI Action 유형.', 50, 'ACTIVE', @created_by, @created_by, @client_ip, @program_id, JSON_OBJECT('crud_type', 'UPDATE', 'ui_runtime_object', 'SP_UI_ACTION', 'source_table', 'system_menu_button'), 'CREATE_MAINTAIN'),
('UI_PERMISSION_TYPE', 'CREATE', 'Create', 'UI Action의 생성 권한을 부여하는 Permission 유형.', 10, 'ACTIVE', @created_by, @created_by, @client_ip, @program_id, JSON_OBJECT('ui_runtime_object', 'SP_UI_PERMISSION', 'source_table', 'system_menu_button_crud_permission', 'permission_column', 'can_create_yn'), 'CREATE_MAINTAIN'),
('UI_PERMISSION_TYPE', 'READ', 'Read', 'UI Action의 조회 권한을 부여하는 Permission 유형.', 20, 'ACTIVE', @created_by, @created_by, @client_ip, @program_id, JSON_OBJECT('ui_runtime_object', 'SP_UI_PERMISSION', 'source_table', 'system_menu_button_crud_permission', 'permission_column', 'can_read_yn'), 'CREATE_MAINTAIN'),
('UI_PERMISSION_TYPE', 'UPDATE', 'Update', 'UI Action의 수정 권한을 부여하는 Permission 유형.', 30, 'ACTIVE', @created_by, @created_by, @client_ip, @program_id, JSON_OBJECT('ui_runtime_object', 'SP_UI_PERMISSION', 'source_table', 'system_menu_button_crud_permission', 'permission_column', 'can_update_yn'), 'CREATE_MAINTAIN'),
('UI_PERMISSION_TYPE', 'DELETE', 'Delete', 'UI Action의 삭제 권한을 부여하는 Permission 유형.', 40, 'ACTIVE', @created_by, @created_by, @client_ip, @program_id, JSON_OBJECT('ui_runtime_object', 'SP_UI_PERMISSION', 'source_table', 'system_menu_button_crud_permission', 'permission_column', 'can_delete_yn'), 'CREATE_MAINTAIN'),
('UI_PERMISSION_TYPE', 'ALTER', 'Alter', 'UI Action의 변경 권한을 부여하는 Permission 유형.', 50, 'ACTIVE', @created_by, @created_by, @client_ip, @program_id, JSON_OBJECT('ui_runtime_object', 'SP_UI_PERMISSION', 'source_table', 'system_menu_button_crud_permission', 'permission_column', 'can_alter_yn'), 'CREATE_MAINTAIN')
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

SELECT group_code, code, code_name, common_code_json
FROM cm_common_code
WHERE group_code IN ('UI_SCREEN_TYPE', 'UI_MENU_TYPE', 'UI_ACTION_TYPE', 'UI_PERMISSION_TYPE')
  AND status_code = 'ACTIVE'
  AND deleted_dt IS NULL
ORDER BY group_code, sort_no, code;

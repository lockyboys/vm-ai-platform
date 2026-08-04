/*
 * File Story
 * system_ UI Repository 테이블군을 UI 도메인 명칭으로 재정렬한다.
 *
 * Change History
 * 20260730 | Codex | system_menu 계열 테이블, FK, 유니크 인덱스를 ui_ 명칭으로 변경한다.
 *
 * Scope
 * - te_common.system_menu                         -> te_common.ui_menu
 * - te_common.system_menu_button                  -> te_common.ui_menu_action
 * - te_common.system_menu_button_crud_permission  -> te_common.ui_menu_action_permission
 *
 * Safety
 * - 행 데이터와 컬럼 정의는 보존한다.
 * - MariaDB DDL은 자동 커밋되므로 실행 전 백업 또는 스냅샷을 확보한다.
 * - 이 파일은 1회성 rename migration이며, 대상이 이미 변경된 환경에서 재실행하지 않는다.
 */

USE te_common;

-- Pre-flight: 세 기존 테이블과 현재 FK/인덱스가 모두 존재하는지 확인한다.
SELECT table_name, table_rows
FROM information_schema.tables
WHERE table_schema = DATABASE()
  AND table_name IN
(
    'system_menu',
    'system_menu_button',
    'system_menu_button_crud_permission'
)
ORDER BY table_name;

SELECT table_name, constraint_name, referenced_table_name
FROM information_schema.key_column_usage
WHERE table_schema = DATABASE()
  AND constraint_name IN
(
    'fk_system_menu_button_menu',
    'fk_button_permission_button',
    'fk_button_permission_menu'
)
ORDER BY table_name, constraint_name;

-- 기존 FK 이름을 제거한 뒤 테이블을 원자적으로 rename 한다.
ALTER TABLE system_menu_button_crud_permission
    DROP FOREIGN KEY fk_button_permission_button,
    DROP FOREIGN KEY fk_button_permission_menu;

ALTER TABLE system_menu_button
    DROP FOREIGN KEY fk_system_menu_button_menu;

RENAME TABLE
    system_menu TO ui_menu,
    system_menu_button TO ui_menu_action,
    system_menu_button_crud_permission TO ui_menu_action_permission;

ALTER TABLE ui_menu_action
    ADD CONSTRAINT fk_ui_menu_action_menu
        FOREIGN KEY (menu_code)
        REFERENCES ui_menu (menu_code);

ALTER TABLE ui_menu_action_permission
    ADD CONSTRAINT fk_ui_action_permission_menu
        FOREIGN KEY (menu_code)
        REFERENCES ui_menu (menu_code),
    ADD CONSTRAINT fk_ui_action_permission_action
        FOREIGN KEY (button_code)
        REFERENCES ui_menu_action (button_code),
    RENAME INDEX uk_button_role_permission TO uk_ui_action_role_permission;

-- Post-flight: 이전 테이블이 사라지고 새 UI Repository 및 관계가 보존됐는지 확인한다.
SELECT table_name, table_rows
FROM information_schema.tables
WHERE table_schema = DATABASE()
  AND table_name IN
(
    'ui_menu',
    'ui_menu_action',
    'ui_menu_action_permission'
)
ORDER BY table_name;

SELECT table_name, constraint_name, column_name, referenced_table_name, referenced_column_name
FROM information_schema.key_column_usage
WHERE table_schema = DATABASE()
  AND table_name IN ('ui_menu_action', 'ui_menu_action_permission')
  AND referenced_table_name IS NOT NULL
ORDER BY table_name, constraint_name, ordinal_position;

SELECT table_name, index_name, column_name, seq_in_index
FROM information_schema.statistics
WHERE table_schema = DATABASE()
  AND table_name = 'ui_menu_action_permission'
  AND index_name = 'uk_ui_action_role_permission'
ORDER BY seq_in_index;

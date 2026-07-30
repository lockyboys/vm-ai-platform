/*
 * File Story
 * 기존 Role 기반 UI Action Permission 레코드를 독립 백업한 뒤 제거한다.
 *
 * Change History
 * 20260730 | Codex | 신규 Member/Rule Permission Runtime 전환을 위해 legacy Role 권한 전체를 백업·삭제한다.
 *
 * Safety
 * - 백업 테이블은 원본과 동일한 물리 구조로 1회 생성한다.
 * - 삭제는 backup 테이블에 동일 permission_id가 존재하는 원본 레코드만 대상으로 한다.
 * - 이 파일은 새 Member/Rule Permission 레코드 등록 전에 한 번만 실행한다.
 */
USE te_common;

CREATE TABLE IF NOT EXISTS ui_menu_action_permission_legacy_20260730
LIKE ui_menu_action_permission;

START TRANSACTION;

INSERT INTO ui_menu_action_permission_legacy_20260730
SELECT source_permission.*
FROM ui_menu_action_permission AS source_permission
ON DUPLICATE KEY UPDATE
    permission_id = VALUES(permission_id);

DELETE source_permission
FROM ui_menu_action_permission AS source_permission
INNER JOIN ui_menu_action_permission_legacy_20260730 AS backup_permission
    ON backup_permission.permission_id = source_permission.permission_id;

SELECT
    (SELECT COUNT(*) FROM ui_menu_action_permission_legacy_20260730) AS backup_row_count,
    (SELECT COUNT(*) FROM ui_menu_action_permission) AS remaining_source_row_count;

COMMIT;

SELECT
    permission_id,
    menu_code,
    button_code,
    user_role_code,
    can_create_yn,
    can_read_yn,
    can_update_yn,
    can_delete_yn,
    can_alter_yn,
    status_code
FROM ui_menu_action_permission_legacy_20260730
ORDER BY permission_id;

SELECT COUNT(*) AS remaining_source_row_count
FROM ui_menu_action_permission;

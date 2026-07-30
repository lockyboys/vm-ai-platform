/*
 * File Story
 * 빈 UI Action Permission Repository를 Member/Rule 주체와 Permission Type 행 기반 구조로 재구성한다.
 *
 * Change History
 * 20260730 | Codex | legacy Role 권한 백업·삭제 후 UI Action Permission을 Subject × Permission Type 행 구조로 전환한다.
 *
 * Safety
 * - ui_menu_action_permission 행이 비어 있지 않으면 구조 변경을 중단한다.
 * - legacy backup 테이블에 최소 한 행이 없으면 구조 변경을 중단한다.
 * - Permission ID는 본 migration이 생성하지 않으며 IdentifierCoordinator로 발급한다.
 * - Member/Rule은 다형 주체이므로 물리 FK 대신 UI_PERMISSION_SUBJECT_TYPE Repository 계약으로 검증한다.
 */
USE te_common;

DELIMITER $$

DROP PROCEDURE IF EXISTS rebuild_ui_menu_action_permission_20260730$$

CREATE PROCEDURE rebuild_ui_menu_action_permission_20260730()
BEGIN
    DECLARE v_source_row_count BIGINT DEFAULT 0;
    DECLARE v_backup_row_count BIGINT DEFAULT 0;

    SELECT COUNT(*)
      INTO v_source_row_count
      FROM ui_menu_action_permission;

    SELECT COUNT(*)
      INTO v_backup_row_count
      FROM ui_menu_action_permission_legacy_20260730;

    IF v_source_row_count <> 0 THEN
        SIGNAL SQLSTATE '45000'
            SET MESSAGE_TEXT = 'UI Permission rebuild aborted: source table must be empty.';
    END IF;

    IF v_backup_row_count = 0 THEN
        SIGNAL SQLSTATE '45000'
            SET MESSAGE_TEXT = 'UI Permission rebuild aborted: legacy backup is required.';
    END IF;

    ALTER TABLE ui_menu_action_permission
        DROP FOREIGN KEY fk_ui_action_permission_menu,
        DROP FOREIGN KEY fk_ui_action_permission_action,
        DROP INDEX uk_ui_action_role_permission,
        DROP COLUMN menu_code,
        CHANGE COLUMN user_role_code permission_subject_type_code VARCHAR(99) NOT NULL
            COMMENT 'Permission Subject Type Code 코드. te_common.cm_common_code의 group_code=UI_PERMISSION_SUBJECT_TYPE을 해석한다.',
        ADD COLUMN permission_subject_id VARCHAR(99) NOT NULL
            COMMENT 'Permission Subject Id 식별자. permission_subject_type_code가 MEMBER이면 cm_member.member_id, RULE이면 rl_rule.rule_id를 Repository 계약으로 해석한다.'
            AFTER permission_subject_type_code,
        ADD COLUMN permission_type_code VARCHAR(99) NOT NULL
            COMMENT 'Permission Type Code 코드. te_common.cm_common_code의 group_code=UI_PERMISSION_TYPE을 해석한다.'
            AFTER permission_subject_id,
        DROP COLUMN can_create_yn,
        DROP COLUMN can_read_yn,
        DROP COLUMN can_update_yn,
        DROP COLUMN can_delete_yn,
        DROP COLUMN can_alter_yn,
        MODIFY COLUMN button_code VARCHAR(99) NOT NULL
            COMMENT 'UI Action Code 코드. te_common.ui_menu_action.button_code를 참조한다.';

    ALTER TABLE ui_menu_action_permission
        ADD CONSTRAINT fk_ui_action_permission_action
            FOREIGN KEY (button_code)
            REFERENCES ui_menu_action (button_code),
        ADD CONSTRAINT uk_ui_action_permission_subject_type
            UNIQUE (button_code, permission_subject_type_code, permission_subject_id, permission_type_code),
        COMMENT = 'PURPOSE: Member 또는 Rule 주체별 UI Action Permission Type 부여 관계를 행 단위로 관리한다. ROLE: COMMON 공식 Repository. SSOT: UI Permission 부여 관계의 단일 원천. ENGINE_GUIDE: Generator, Engine 및 AI는 UI_PERMISSION_SUBJECT_TYPE과 UI_PERMISSION_TYPE Repository 계약을 해석하며 값을 하드코딩하지 않는다.';
END$$

DELIMITER ;

CALL rebuild_ui_menu_action_permission_20260730();

DROP PROCEDURE IF EXISTS rebuild_ui_menu_action_permission_20260730;

SELECT
    column_name,
    column_type,
    is_nullable,
    column_key,
    column_comment
FROM information_schema.columns
WHERE table_schema = DATABASE()
  AND table_name = 'ui_menu_action_permission'
ORDER BY ordinal_position;

SELECT
    constraint_name,
    constraint_type
FROM information_schema.table_constraints
WHERE table_schema = DATABASE()
  AND table_name = 'ui_menu_action_permission'
ORDER BY constraint_type, constraint_name;

SELECT
    constraint_name,
    column_name,
    referenced_table_name,
    referenced_column_name
FROM information_schema.key_column_usage
WHERE table_schema = DATABASE()
  AND table_name = 'ui_menu_action_permission'
  AND referenced_table_name IS NOT NULL
ORDER BY constraint_name, ordinal_position;

SELECT COUNT(*) AS ui_permission_row_count
FROM ui_menu_action_permission;

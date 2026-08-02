/*
 * File Story
 * UI Runtime Repository의 유형 Code 컬럼을 UI Common Code Group과 직접 연결한다.
 *
 * Change History
 * 20260802 | Codex | ui_menu의 UI Screen/Menu Type Code를 추가하고, ui_menu_action의 crud_type을 ui_action_type_code로 변경하며, UI Permission Type Code의 허용 Code COMMENT를 갱신한다.
 *
 * Contract
 * - ui_menu.ui_screen_type_code: UI_SCREEN_TYPE = DASHBOARD, DETAIL, FORM, LIST
 * - ui_menu.ui_menu_type_code: UI_MENU_TYPE = GROUP, ITEM, ROOT
 * - ui_menu_action.ui_action_type_code: UI_ACTION_TYPE = CREATE, DELETE, EXECUTE, READ, UPDATE
 * - ui_menu_action_permission.permission_type_code: UI_PERMISSION_TYPE = CREATE, READ, UPDATE, DELETE, ALTER
 *
 * Safety
 * - 기존 ui_menu_action.crud_type 값이 UI_ACTION_TYPE 허용 Code 밖이면 이름 변경을 중단한다.
 * - 새 ui_menu 유형 Code는 기존 행을 보존하기 위해 NULL 허용으로 추가한다. 값 등록 후 별도 검증을 거쳐 NOT NULL 전환한다.
 * - 테이블·행 삭제는 하지 않는다.
 */
USE te_common;

DELIMITER $$

DROP PROCEDURE IF EXISTS migrate_ui_runtime_type_code_20260802$$

CREATE PROCEDURE migrate_ui_runtime_type_code_20260802()
BEGIN
    DECLARE v_invalid_action_type_count BIGINT DEFAULT 0;
    DECLARE v_ui_action_type_column_exists BIGINT DEFAULT 0;
    DECLARE v_legacy_crud_type_column_exists BIGINT DEFAULT 0;

    ALTER TABLE ui_menu
        ADD COLUMN IF NOT EXISTS ui_screen_type_code VARCHAR(99) NULL
            COMMENT 'UI Screen Type Code 코드. te_common.cm_common_code의 group_code=UI_SCREEN_TYPE을 해석한다. 허용 Code: DASHBOARD, DETAIL, FORM, LIST.'
            AFTER menu_url,
        ADD COLUMN IF NOT EXISTS ui_menu_type_code VARCHAR(99) NULL
            COMMENT 'UI Menu Type Code 코드. te_common.cm_common_code의 group_code=UI_MENU_TYPE을 해석한다. 허용 Code: GROUP, ITEM, ROOT.'
            AFTER ui_screen_type_code;

    SELECT COUNT(*)
      INTO v_ui_action_type_column_exists
      FROM information_schema.columns
     WHERE table_schema = DATABASE()
       AND table_name = 'ui_menu_action'
       AND column_name = 'ui_action_type_code';

    SELECT COUNT(*)
      INTO v_legacy_crud_type_column_exists
      FROM information_schema.columns
     WHERE table_schema = DATABASE()
       AND table_name = 'ui_menu_action'
       AND column_name = 'crud_type';

    IF v_ui_action_type_column_exists = 0
       AND v_legacy_crud_type_column_exists = 0 THEN
        SIGNAL SQLSTATE '45000'
            SET MESSAGE_TEXT = 'UI Action migration aborted: neither crud_type nor ui_action_type_code exists.';
    END IF;

    IF v_ui_action_type_column_exists = 0 THEN
        SELECT COUNT(*)
          INTO v_invalid_action_type_count
          FROM ui_menu_action
         WHERE crud_type IS NULL
            OR crud_type NOT IN ('CREATE', 'DELETE', 'EXECUTE', 'READ', 'UPDATE');

        IF v_invalid_action_type_count <> 0 THEN
            SIGNAL SQLSTATE '45000'
                SET MESSAGE_TEXT = 'UI Action migration aborted: crud_type contains values outside UI_ACTION_TYPE.';
        END IF;

        ALTER TABLE ui_menu_action
            CHANGE COLUMN crud_type ui_action_type_code VARCHAR(99) NOT NULL
                COMMENT 'UI Action Type Code 코드. te_common.cm_common_code의 group_code=UI_ACTION_TYPE을 해석한다. 허용 Code: CREATE, DELETE, EXECUTE, READ, UPDATE.';
    ELSE
        ALTER TABLE ui_menu_action
            MODIFY COLUMN ui_action_type_code VARCHAR(99) NOT NULL
                COMMENT 'UI Action Type Code 코드. te_common.cm_common_code의 group_code=UI_ACTION_TYPE을 해석한다. 허용 Code: CREATE, DELETE, EXECUTE, READ, UPDATE.';
    END IF;

    ALTER TABLE ui_menu_action_permission
        MODIFY COLUMN permission_type_code VARCHAR(99) NOT NULL
            COMMENT 'Permission Type Code 코드. te_common.cm_common_code의 group_code=UI_PERMISSION_TYPE을 해석한다. 허용 Code: CREATE, READ, UPDATE, DELETE, ALTER.';
END$$

DELIMITER ;

CALL migrate_ui_runtime_type_code_20260802();

DROP PROCEDURE IF EXISTS migrate_ui_runtime_type_code_20260802;

SELECT
    table_name,
    column_name,
    column_type,
    is_nullable,
    column_comment
FROM information_schema.columns
WHERE table_schema = DATABASE()
  AND (
      (table_name = 'ui_menu'
       AND column_name IN ('ui_screen_type_code', 'ui_menu_type_code'))
   OR (table_name = 'ui_menu_action'
       AND column_name = 'ui_action_type_code')
   OR (table_name = 'ui_menu_action_permission'
       AND column_name = 'permission_type_code')
  )
ORDER BY table_name, ordinal_position;

SELECT DISTINCT ui_action_type_code
FROM ui_menu_action
ORDER BY ui_action_type_code;

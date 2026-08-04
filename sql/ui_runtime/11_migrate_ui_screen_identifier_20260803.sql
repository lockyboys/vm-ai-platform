/*
 * File Story
 * UI Screen Instance Identifier를 ui_menu의 실제 화면 행에 보존한다.
 *
 * Change History
 * 20260803 | Codex | ui_menu에 ui_screen_id를 추가하여 SP_UI_SCREEN Identifier Engine 발급값을 health_report 등 화면 행에 연결한다.
 *
 * Contract
 * - ui_menu.ui_screen_id는 SP_UI_SCREEN Object metadata를 해석한 Identifier Engine 발급값만 저장한다.
 * - 화면 식별자는 menu_code와 별개의 변경 불가능한 Instance Identifier다.
 *
 * Safety
 * - 기존 행과 컬럼을 삭제하거나 변경하지 않는다.
 * - 기존 ui_screen_id 값은 보존한다.
 */
USE te_common;

ALTER TABLE ui_menu
    ADD COLUMN IF NOT EXISTS ui_screen_id VARCHAR(99) NULL
        COMMENT 'UI Screen Identifier. te_story_platform.sp_object의 object_code=SP_UI_SCREEN metadata를 Identifier Engine이 해석하여 발급한다.'
        AFTER menu_code;

CREATE UNIQUE INDEX IF NOT EXISTS uk_ui_menu_ui_screen_id
    ON ui_menu (ui_screen_id);

SELECT
    menu_code,
    menu_name,
    ui_screen_id,
    ui_screen_type_code,
    ui_menu_type_code,
    status_code
FROM ui_menu
WHERE deleted_dt IS NULL
ORDER BY menu_sort_no, menu_code;

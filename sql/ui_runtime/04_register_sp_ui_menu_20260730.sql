/* Register SP_UI_MENU through the existing Repository Object Procedure. */
USE te_story_platform;

SET @sp_ui_menu_object_id = COALESCE(
    (SELECT object_id FROM sp_object WHERE object_code = 'SP_UI_MENU' AND deleted_dt IS NULL LIMIT 1),
    @sp_ui_menu_object_id
);

CALL sp_register_repository_object(
    JSON_OBJECT(
        'object_id', @sp_ui_menu_object_id,
        'object_code', 'SP_UI_MENU',
        'object_name', 'UI Menu',
        'business_code', @ui_business_code,
        'domain_code', @ui_domain_code,
        'object_type_code', @ui_object_type_code,
        'object_description', 'COMMON.ui_menu를 UI Menu Repository의 공식 SSOT로 해석한다.',
        'object_level', @ui_object_level,
        'sort_no', 20,
        'status_code', 'ACTIVE',
        'active_yn', 'Y',
        'created_by', @ui_actor_id,
        'program_id', @ui_program_id,
        'client_ip', @ui_client_ip
    )
);

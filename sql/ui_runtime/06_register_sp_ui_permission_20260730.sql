/* Register SP_UI_PERMISSION through the existing Repository Object Procedure. */
USE te_story_platform;

SET @sp_ui_permission_object_id = COALESCE(
    (SELECT object_id FROM sp_object WHERE object_code = 'SP_UI_PERMISSION' AND deleted_dt IS NULL LIMIT 1),
    @sp_ui_permission_object_id
);

CALL sp_register_repository_object(
    JSON_OBJECT(
        'object_id', @sp_ui_permission_object_id,
        'object_code', 'SP_UI_PERMISSION',
        'object_name', 'UI Permission',
        'business_code', @ui_business_code,
        'domain_code', @ui_domain_code,
        'object_type_code', @ui_object_type_code,
        'object_description', 'COMMON.ui_menu_action_permission의 Action별 Member 또는 Rule 권한 행을 UI Permission 계약으로 해석한다.',
        'object_level', @ui_object_level,
        'sort_no', 40,
        'status_code', 'ACTIVE',
        'active_yn', 'Y',
        'created_by', @ui_actor_id,
        'program_id', @ui_program_id,
        'client_ip', @ui_client_ip
    )
);

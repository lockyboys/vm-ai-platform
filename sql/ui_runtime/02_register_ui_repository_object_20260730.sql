/*
 * UI Repository Object registration contract.
 * IdentifierCoordinator must issue a missing object_id before this script is run.
 * Existing object_ids are always read from sp_object; no fixed identifier is stored here.
 */
USE te_story_platform;

SET @ui_program_id = 'REGISTER_UI_REPOSITORY_OBJECT_20260730';
SET @ui_actor_id = 'SYSTEM';
SET @ui_client_ip = '127.0.0.1';

SET @ui_action_contract = (
    SELECT common_code_json
    FROM te_common.cm_common_code
    WHERE group_code = 'ACTION_TYPE'
      AND code = 'REGISTER_REPOSITORY_OBJECT'
      AND status_code = 'ACTIVE'
      AND deleted_dt IS NULL
);
SET @ui_business_code = JSON_UNQUOTE(JSON_EXTRACT(@ui_action_contract, '$.object_definition_business_code'));
SET @ui_domain_code = JSON_UNQUOTE(JSON_EXTRACT(@ui_action_contract, '$.object_definition_domain_code'));
SET @ui_object_type_code = JSON_UNQUOTE(JSON_EXTRACT(@ui_action_contract, '$.object_type_code'));
SET @ui_object_level = CAST(JSON_UNQUOTE(JSON_EXTRACT(@ui_action_contract, '$.object_level')) AS UNSIGNED);

SELECT
    object_code,
    object_id,
    CASE WHEN object_id IS NULL THEN 'IDENTIFIER_ISSUE_REQUIRED' ELSE 'REGISTERED' END AS registration_state
FROM
(
    SELECT 'SP_UI_SCREEN' AS object_code,
           (SELECT object_id FROM sp_object WHERE object_code = 'SP_UI_SCREEN' AND deleted_dt IS NULL LIMIT 1) AS object_id
    UNION ALL
    SELECT 'SP_UI_MENU',
           (SELECT object_id FROM sp_object WHERE object_code = 'SP_UI_MENU' AND deleted_dt IS NULL LIMIT 1)
    UNION ALL
    SELECT 'SP_UI_ACTION',
           (SELECT object_id FROM sp_object WHERE object_code = 'SP_UI_ACTION' AND deleted_dt IS NULL LIMIT 1)
    UNION ALL
    SELECT 'SP_UI_PERMISSION',
           (SELECT object_id FROM sp_object WHERE object_code = 'SP_UI_PERMISSION' AND deleted_dt IS NULL LIMIT 1)
) ui_object
ORDER BY object_code;

SELECT
    @ui_business_code AS business_code,
    @ui_domain_code AS domain_code,
    @ui_object_type_code AS object_type_code,
    @ui_object_level AS object_level;

/*
 * Apply the Rule contract's ERD Identifier Object level to existing metadata.
 *
 * No Identifier is fixed here.  The ERD object code and its level are both
 * resolved from the active REGISTER_REPOSITORY_OBJECT Rule action contract.
 * This does not change any database structure or issued sp_erd rows.
 */
START TRANSACTION;

UPDATE te_story_platform.sp_object AS object_metadata
JOIN te_common.cm_common_code AS action_contract
  ON action_contract.group_code = 'ACTION_TYPE'
 AND action_contract.code = 'REGISTER_REPOSITORY_OBJECT'
 AND action_contract.status_code = 'ACTIVE'
 AND action_contract.deleted_dt IS NULL
SET object_metadata.object_level = CAST(
        JSON_UNQUOTE(
            JSON_EXTRACT(
                action_contract.common_code_json,
                '$.identifier_object_definitions.erd.object_level'
            )
        ) AS UNSIGNED
    ),
    object_metadata.updated_dt = CURRENT_TIMESTAMP,
    object_metadata.updated_by = 'SYSTEM',
    object_metadata.client_ip = '127.0.0.1',
    object_metadata.program_id = 'SYNC_ERD_IDENTIFIER_OBJECT_LEVEL_20260731'
WHERE object_metadata.object_code = JSON_UNQUOTE(
        JSON_EXTRACT(
            action_contract.common_code_json,
            '$.identifier_object_codes.erd'
        )
    )
  AND object_metadata.status_code = 'ACTIVE'
  AND object_metadata.active_yn = 'Y'
  AND object_metadata.deleted_dt IS NULL;

SELECT
    object_metadata.object_id,
    object_metadata.object_code,
    object_metadata.object_level,
    JSON_UNQUOTE(
        JSON_EXTRACT(
            action_contract.common_code_json,
            '$.identifier_object_definitions.erd.object_level'
        )
    ) AS rule_object_level
FROM te_story_platform.sp_object AS object_metadata
JOIN te_common.cm_common_code AS action_contract
  ON action_contract.group_code = 'ACTION_TYPE'
 AND action_contract.code = 'REGISTER_REPOSITORY_OBJECT'
 AND action_contract.status_code = 'ACTIVE'
 AND action_contract.deleted_dt IS NULL
WHERE object_metadata.object_code = JSON_UNQUOTE(
        JSON_EXTRACT(
            action_contract.common_code_json,
            '$.identifier_object_codes.erd'
        )
    )
  AND object_metadata.status_code = 'ACTIVE'
  AND object_metadata.active_yn = 'Y'
  AND object_metadata.deleted_dt IS NULL;

COMMIT;

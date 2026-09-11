-- File Name : 01_update_mongodb_collection_name_20260830.sql
-- Purpose   : Synchronize active STORAGE_SEPARATION_TARGET metadata with the
--             renamed MongoDB collection and payload-field names.
-- Change History
-- 20260830 | CODEX | Correct renamed collection metadata; fixes the prior
--          sql_guard_executionr_message typo before payload columns are removed.
-- Execute before 02_backup_and_remove_migrated_payload_columns_20260830.sql.
-- This operational migration records the MariaDB execution account in updated_by.

UPDATE te_common.cm_common_code
SET common_code_json = JSON_SET(
        common_code_json,
        '$.mongodb_collection_name',
        CASE code
            WHEN 'HEALTH_REPORT_CONTENT' THEN 'health_report_content'
            WHEN 'SQL_GUARD_EXECUTION_DETAIL' THEN 'sql_guard_execution_message'
            WHEN 'SQL_GUARD_VERIFICATION_DETAIL' THEN 'sql_guard_verification_message'
            WHEN 'IMPACT_ANALYSIS_DETAIL' THEN 'sp_impact_analysis_text'
        END,
        '$.mongodb_payload_field_name',
        CASE code
            WHEN 'HEALTH_REPORT_CONTENT' THEN 'health_report_content'
            WHEN 'SQL_GUARD_EXECUTION_DETAIL' THEN 'sql_guard_execution_message'
            WHEN 'SQL_GUARD_VERIFICATION_DETAIL' THEN 'sql_guard_verification_message'
            WHEN 'IMPACT_ANALYSIS_DETAIL' THEN 'sp_impact_analysis_text'
        END
    ),
    updated_by = SUBSTRING_INDEX(CURRENT_USER(), '@', 1),
    updated_dt = CURRENT_TIMESTAMP,
    program_id = 'SPS_STORAGE_SEPARATION_MIGRATION_20260830',
    client_ip = '127.0.0.1'
WHERE group_code = 'STORAGE_SEPARATION_TARGET'
  AND code IN (
      'HEALTH_REPORT_CONTENT',
      'SQL_GUARD_EXECUTION_DETAIL',
      'SQL_GUARD_VERIFICATION_DETAIL',
      'IMPACT_ANALYSIS_DETAIL'
  )
  AND status_code = 'ACTIVE'
  AND deleted_dt IS NULL;

SELECT code,
       JSON_UNQUOTE(JSON_EXTRACT(common_code_json, '$.mongodb_collection_name'))
           AS mongodb_collection_name,
       JSON_UNQUOTE(JSON_EXTRACT(common_code_json, '$.mongodb_payload_field_name'))
           AS mongodb_payload_field_name
FROM te_common.cm_common_code
WHERE group_code = 'STORAGE_SEPARATION_TARGET'
  AND code IN (
      'HEALTH_REPORT_CONTENT',
      'SQL_GUARD_EXECUTION_DETAIL',
      'SQL_GUARD_VERIFICATION_DETAIL',
      'IMPACT_ANALYSIS_DETAIL'
  )
ORDER BY code;

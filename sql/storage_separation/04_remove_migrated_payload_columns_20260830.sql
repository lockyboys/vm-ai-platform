-- File Name : 04_remove_migrated_payload_columns_20260830.sql
-- Purpose   : Remove MariaDB payload columns only after backup and MongoDB
--             migration verification have completed for every source record.
-- Prerequisite: 01 metadata update, 02 backup, and all 03 migrations passed.
-- Safety    : MariaDB DDL auto-commits; execute once with --abort-source-on-error.

SELECT 'PRECHECK: rollback tables must exist before DDL' AS verification_step;

SELECT table_schema, table_name
FROM information_schema.tables
WHERE (table_schema, table_name) IN (
    ('te_common', 'health_report_payload_backup_20260830'),
    ('te_common', 'sql_guard_execution_log_payload_backup_20260830'),
    ('te_common', 'sql_guard_verification_log_payload_backup_20260830'),
    ('te_story_platform', 'sp_impact_analysis_result_payload_backup_20260830')
)
ORDER BY table_schema, table_name;

ALTER TABLE te_common.health_report
    DROP COLUMN report_content;

ALTER TABLE te_common.sql_guard_execution_log
    DROP COLUMN error_message;

ALTER TABLE te_common.sql_guard_verification_log
    DROP COLUMN message;

ALTER TABLE te_story_platform.sp_impact_analysis_result
    DROP INDEX idx_sp_impact_analysis_result_01,
    DROP COLUMN change_target_text,
    DROP COLUMN affected_text,
    DROP COLUMN analysis_note;

SELECT 'POSTCHECK: no migrated payload column remains' AS verification_step;

SELECT table_schema, table_name, column_name
FROM information_schema.columns
WHERE (table_schema, table_name, column_name) IN (
    ('te_common', 'health_report', 'report_content'),
    ('te_common', 'sql_guard_execution_log', 'error_message'),
    ('te_common', 'sql_guard_verification_log', 'message'),
    ('te_story_platform', 'sp_impact_analysis_result', 'change_target_text'),
    ('te_story_platform', 'sp_impact_analysis_result', 'affected_text'),
    ('te_story_platform', 'sp_impact_analysis_result', 'analysis_note')
);

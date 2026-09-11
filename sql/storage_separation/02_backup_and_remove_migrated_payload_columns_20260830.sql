-- File Name : 02_backup_migrated_payload_tables_20260830.sql
-- Purpose   : Create immutable rollback copies before MongoDB payload migration.
-- Scope     : Four existing MOVE_PAYLOAD contracts only.
-- Safety    : Execute once with --abort-source-on-error. Existing backup-table
--             names deliberately cause an error and prevent any overwrite.

SELECT 'PRECHECK: payload columns and backup-table names' AS verification_step;

SELECT table_schema, table_name, column_name, column_type
FROM information_schema.columns
WHERE (table_schema, table_name, column_name) IN (
    ('te_common', 'health_report', 'report_content'),
    ('te_common', 'sql_guard_execution_log', 'error_message'),
    ('te_common', 'sql_guard_verification_log', 'message'),
    ('te_story_platform', 'sp_impact_analysis_result', 'change_target_text'),
    ('te_story_platform', 'sp_impact_analysis_result', 'affected_text'),
    ('te_story_platform', 'sp_impact_analysis_result', 'analysis_note')
)
ORDER BY table_schema, table_name, ordinal_position;

CREATE TABLE te_common.health_report_payload_backup_20260830
LIKE te_common.health_report;
INSERT INTO te_common.health_report_payload_backup_20260830
SELECT * FROM te_common.health_report;

CREATE TABLE te_common.sql_guard_execution_log_payload_backup_20260830
LIKE te_common.sql_guard_execution_log;
INSERT INTO te_common.sql_guard_execution_log_payload_backup_20260830
SELECT * FROM te_common.sql_guard_execution_log;

CREATE TABLE te_common.sql_guard_verification_log_payload_backup_20260830
LIKE te_common.sql_guard_verification_log;
INSERT INTO te_common.sql_guard_verification_log_payload_backup_20260830
SELECT * FROM te_common.sql_guard_verification_log;

CREATE TABLE te_story_platform.sp_impact_analysis_result_payload_backup_20260830
LIKE te_story_platform.sp_impact_analysis_result;
INSERT INTO te_story_platform.sp_impact_analysis_result_payload_backup_20260830
SELECT * FROM te_story_platform.sp_impact_analysis_result;

SELECT 'BACKUP_ROW_COUNT' AS verification_step,
       'te_common.health_report' AS source_table,
       (SELECT COUNT(*) FROM te_common.health_report) AS source_count,
       (SELECT COUNT(*) FROM te_common.health_report_payload_backup_20260830) AS backup_count
UNION ALL
SELECT 'BACKUP_ROW_COUNT',
       'te_common.sql_guard_execution_log',
       (SELECT COUNT(*) FROM te_common.sql_guard_execution_log),
       (SELECT COUNT(*) FROM te_common.sql_guard_execution_log_payload_backup_20260830)
UNION ALL
SELECT 'BACKUP_ROW_COUNT',
       'te_common.sql_guard_verification_log',
       (SELECT COUNT(*) FROM te_common.sql_guard_verification_log),
       (SELECT COUNT(*) FROM te_common.sql_guard_verification_log_payload_backup_20260830)
UNION ALL
SELECT 'BACKUP_ROW_COUNT',
       'te_story_platform.sp_impact_analysis_result',
       (SELECT COUNT(*) FROM te_story_platform.sp_impact_analysis_result),
       (SELECT COUNT(*) FROM te_story_platform.sp_impact_analysis_result_payload_backup_20260830);

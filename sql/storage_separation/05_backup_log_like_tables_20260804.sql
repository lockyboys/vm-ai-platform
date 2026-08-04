-- ============================================================================
-- SPS Log-like MariaDB Tables Pre-Separation Backup
-- Date: 2026-08-04 KST
-- Scope: te_common log/result tables not governed by active sp_knowledge_hold.
-- Excluded: every active, non-deleted sp_knowledge_hold table decision.
-- Safety:
--   1. Static explicit targets only.
--   2. No DROP, DELETE, UPDATE, TRUNCATE, or source-table ALTER.
--   3. Existing backup name causes fail-closed CREATE TABLE error.
--   4. Data stays inside the original MariaDB schema.
--   5. Continue to storage separation only when every row count matches.
-- ============================================================================

-- te_common.cron_logs
CREATE TABLE `te_common`.`cron_logs_backup_20260804_01` LIKE `te_common`.`cron_logs`;
INSERT INTO `te_common`.`cron_logs_backup_20260804_01`
SELECT * FROM `te_common`.`cron_logs`;

-- te_common.model_history
CREATE TABLE `te_common`.`model_history_backup_20260804_01` LIKE `te_common`.`model_history`;
INSERT INTO `te_common`.`model_history_backup_20260804_01`
SELECT * FROM `te_common`.`model_history`;

-- te_common.pipeline_results
CREATE TABLE `te_common`.`pipeline_results_backup_20260804_01` LIKE `te_common`.`pipeline_results`;
INSERT INTO `te_common`.`pipeline_results_backup_20260804_01`
SELECT * FROM `te_common`.`pipeline_results`;

-- Verification: source_row_count must equal backup_row_count for every row.
SELECT 'te_common' AS table_schema, 'cron_logs' AS source_table_name, 'cron_logs_backup_20260804_01' AS backup_table_name, 0 AS inventory_row_estimate, (SELECT COUNT(*) FROM `te_common`.`cron_logs`) AS source_row_count, (SELECT COUNT(*) FROM `te_common`.`cron_logs_backup_20260804_01`) AS backup_row_count
UNION ALL
SELECT 'te_common' AS table_schema, 'model_history' AS source_table_name, 'model_history_backup_20260804_01' AS backup_table_name, 0 AS inventory_row_estimate, (SELECT COUNT(*) FROM `te_common`.`model_history`) AS source_row_count, (SELECT COUNT(*) FROM `te_common`.`model_history_backup_20260804_01`) AS backup_row_count
UNION ALL
SELECT 'te_common' AS table_schema, 'pipeline_results' AS source_table_name, 'pipeline_results_backup_20260804_01' AS backup_table_name, 0 AS inventory_row_estimate, (SELECT COUNT(*) FROM `te_common`.`pipeline_results`) AS source_row_count, (SELECT COUNT(*) FROM `te_common`.`pipeline_results_backup_20260804_01`) AS backup_row_count;

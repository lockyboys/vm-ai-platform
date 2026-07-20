/*
File Name : repository_column_rename_patch_20260720.sql
Purpose   : One-time hardcoded Repository column rename patch
Tables    : 13
Columns   : 18
*/

SET NAMES utf8mb4;

/* PATCH 001 - te_story_platform.sp_domain */

CREATE TABLE `te_story_platform`.`sp_domain_backup_rename_20260720_01`
LIKE `te_story_platform`.`sp_domain`;

START TRANSACTION;

INSERT INTO `te_story_platform`.`sp_domain_backup_rename_20260720_01`
SELECT * FROM `te_story_platform`.`sp_domain`;

COMMIT;

SELECT
    (SELECT COUNT(*) FROM `te_story_platform`.`sp_domain`) AS original_count,
    (SELECT COUNT(*) FROM `te_story_platform`.`sp_domain_backup_rename_20260720_01`) AS backup_count;

ALTER TABLE `te_story_platform`.`sp_domain`
    RENAME COLUMN `sort_order` TO `sort_no`;

SELECT column_name, column_type
FROM information_schema.columns
WHERE table_schema = 'te_story_platform'
  AND table_name = 'sp_domain'
  AND column_name IN (
      'sort_no'
  )
ORDER BY ordinal_position;

SELECT COUNT(*) AS row_count FROM `te_story_platform`.`sp_domain`;

/* PATCH 002 - te_story_platform.sp_execution_history */

CREATE TABLE `te_story_platform`.`sp_execution_history_backup_rename_20260720_01`
LIKE `te_story_platform`.`sp_execution_history`;

START TRANSACTION;

INSERT INTO `te_story_platform`.`sp_execution_history_backup_rename_20260720_01`
SELECT * FROM `te_story_platform`.`sp_execution_history`;

COMMIT;

SELECT
    (SELECT COUNT(*) FROM `te_story_platform`.`sp_execution_history`) AS original_count,
    (SELECT COUNT(*) FROM `te_story_platform`.`sp_execution_history_backup_rename_20260720_01`) AS backup_count;

ALTER TABLE `te_story_platform`.`sp_execution_history`
    RENAME COLUMN `repository_status` TO `repository_status_code`,
    RENAME COLUMN `mongodb_status` TO `mongodb_status_code`,
    RENAME COLUMN `execution_status` TO `execution_status_code`,
    RENAME COLUMN `history_status` TO `history_status_code`;

SELECT column_name, column_type
FROM information_schema.columns
WHERE table_schema = 'te_story_platform'
  AND table_name = 'sp_execution_history'
  AND column_name IN (
      'repository_status_code',
      'mongodb_status_code',
      'execution_status_code',
      'history_status_code'
  )
ORDER BY ordinal_position;

SELECT COUNT(*) AS row_count FROM `te_story_platform`.`sp_execution_history`;

/* PATCH 003 - te_story_platform.sp_identifier_sequence */

CREATE TABLE `te_story_platform`.`sp_identifier_sequence_backup_rename_20260720_01`
LIKE `te_story_platform`.`sp_identifier_sequence`;

START TRANSACTION;

INSERT INTO `te_story_platform`.`sp_identifier_sequence_backup_rename_20260720_01`
SELECT * FROM `te_story_platform`.`sp_identifier_sequence`;

COMMIT;

SELECT
    (SELECT COUNT(*) FROM `te_story_platform`.`sp_identifier_sequence`) AS original_count,
    (SELECT COUNT(*) FROM `te_story_platform`.`sp_identifier_sequence_backup_rename_20260720_01`) AS backup_count;

ALTER TABLE `te_story_platform`.`sp_identifier_sequence`
    RENAME COLUMN `sequence_date` TO `sequence_dt`;

SELECT column_name, column_type
FROM information_schema.columns
WHERE table_schema = 'te_story_platform'
  AND table_name = 'sp_identifier_sequence'
  AND column_name IN (
      'sequence_dt'
  )
ORDER BY ordinal_position;

SELECT COUNT(*) AS row_count FROM `te_story_platform`.`sp_identifier_sequence`;

/* PATCH 004 - te_story_platform.sp_knowledge_type_hold */

CREATE TABLE `te_story_platform`.`sp_knowledge_type_hold_backup_rename_20260720_01`
LIKE `te_story_platform`.`sp_knowledge_type_hold`;

START TRANSACTION;

INSERT INTO `te_story_platform`.`sp_knowledge_type_hold_backup_rename_20260720_01`
SELECT * FROM `te_story_platform`.`sp_knowledge_type_hold`;

COMMIT;

SELECT
    (SELECT COUNT(*) FROM `te_story_platform`.`sp_knowledge_type_hold`) AS original_count,
    (SELECT COUNT(*) FROM `te_story_platform`.`sp_knowledge_type_hold_backup_rename_20260720_01`) AS backup_count;

ALTER TABLE `te_story_platform`.`sp_knowledge_type_hold`
    RENAME COLUMN `sort_order` TO `sort_no`;

SELECT column_name, column_type
FROM information_schema.columns
WHERE table_schema = 'te_story_platform'
  AND table_name = 'sp_knowledge_type_hold'
  AND column_name IN (
      'sort_no'
  )
ORDER BY ordinal_position;

SELECT COUNT(*) AS row_count FROM `te_story_platform`.`sp_knowledge_type_hold`;

/* PATCH 005 - te_common.cm_data_lifecycle_index */

CREATE TABLE `te_common`.`cm_data_lifecycle_index_backup_rename_20260720_01`
LIKE `te_common`.`cm_data_lifecycle_index`;

START TRANSACTION;

INSERT INTO `te_common`.`cm_data_lifecycle_index_backup_rename_20260720_01`
SELECT * FROM `te_common`.`cm_data_lifecycle_index`;

COMMIT;

SELECT
    (SELECT COUNT(*) FROM `te_common`.`cm_data_lifecycle_index`) AS original_count,
    (SELECT COUNT(*) FROM `te_common`.`cm_data_lifecycle_index_backup_rename_20260720_01`) AS backup_count;

ALTER TABLE `te_common`.`cm_data_lifecycle_index`
    RENAME COLUMN `disposed_at` TO `disposed_dt`;

SELECT column_name, column_type
FROM information_schema.columns
WHERE table_schema = 'te_common'
  AND table_name = 'cm_data_lifecycle_index'
  AND column_name IN (
      'disposed_dt'
  )
ORDER BY ordinal_position;

SELECT COUNT(*) AS row_count FROM `te_common`.`cm_data_lifecycle_index`;

/* PATCH 006 - te_common.cm_member_private */

CREATE TABLE `te_common`.`cm_member_private_backup_rename_20260720_01`
LIKE `te_common`.`cm_member_private`;

START TRANSACTION;

INSERT INTO `te_common`.`cm_member_private_backup_rename_20260720_01`
SELECT * FROM `te_common`.`cm_member_private`;

COMMIT;

SELECT
    (SELECT COUNT(*) FROM `te_common`.`cm_member_private`) AS original_count,
    (SELECT COUNT(*) FROM `te_common`.`cm_member_private_backup_rename_20260720_01`) AS backup_count;

ALTER TABLE `te_common`.`cm_member_private`
    RENAME COLUMN `birth_date` TO `birth_dt`;

SELECT column_name, column_type
FROM information_schema.columns
WHERE table_schema = 'te_common'
  AND table_name = 'cm_member_private'
  AND column_name IN (
      'birth_dt'
  )
ORDER BY ordinal_position;

SELECT COUNT(*) AS row_count FROM `te_common`.`cm_member_private`;

/* PATCH 007 - te_common.cm_sequence */

CREATE TABLE `te_common`.`cm_sequence_backup_rename_20260720_01`
LIKE `te_common`.`cm_sequence`;

START TRANSACTION;

INSERT INTO `te_common`.`cm_sequence_backup_rename_20260720_01`
SELECT * FROM `te_common`.`cm_sequence`;

COMMIT;

SELECT
    (SELECT COUNT(*) FROM `te_common`.`cm_sequence`) AS original_count,
    (SELECT COUNT(*) FROM `te_common`.`cm_sequence_backup_rename_20260720_01`) AS backup_count;

ALTER TABLE `te_common`.`cm_sequence`
    RENAME COLUMN `sequence_date` TO `sequence_dt`;

SELECT column_name, column_type
FROM information_schema.columns
WHERE table_schema = 'te_common'
  AND table_name = 'cm_sequence'
  AND column_name IN (
      'sequence_dt'
  )
ORDER BY ordinal_position;

SELECT COUNT(*) AS row_count FROM `te_common`.`cm_sequence`;

/* PATCH 008 - te_common.cm_sequence_policy */

CREATE TABLE `te_common`.`cm_sequence_policy_backup_rename_20260720_01`
LIKE `te_common`.`cm_sequence_policy`;

START TRANSACTION;

INSERT INTO `te_common`.`cm_sequence_policy_backup_rename_20260720_01`
SELECT * FROM `te_common`.`cm_sequence_policy`;

COMMIT;

SELECT
    (SELECT COUNT(*) FROM `te_common`.`cm_sequence_policy`) AS original_count,
    (SELECT COUNT(*) FROM `te_common`.`cm_sequence_policy_backup_rename_20260720_01`) AS backup_count;

ALTER TABLE `te_common`.`cm_sequence_policy`
    RENAME COLUMN `sort_order` TO `sort_no`;

SELECT column_name, column_type
FROM information_schema.columns
WHERE table_schema = 'te_common'
  AND table_name = 'cm_sequence_policy'
  AND column_name IN (
      'sort_no'
  )
ORDER BY ordinal_position;

SELECT COUNT(*) AS row_count FROM `te_common`.`cm_sequence_policy`;

/* PATCH 009 - te_common.cm_sequence_policy_definition */

CREATE TABLE `te_common`.`cm_sequence_policy_definition_backup_rename_20260720_01`
LIKE `te_common`.`cm_sequence_policy_definition`;

START TRANSACTION;

INSERT INTO `te_common`.`cm_sequence_policy_definition_backup_rename_20260720_01`
SELECT * FROM `te_common`.`cm_sequence_policy_definition`;

COMMIT;

SELECT
    (SELECT COUNT(*) FROM `te_common`.`cm_sequence_policy_definition`) AS original_count,
    (SELECT COUNT(*) FROM `te_common`.`cm_sequence_policy_definition_backup_rename_20260720_01`) AS backup_count;

ALTER TABLE `te_common`.`cm_sequence_policy_definition`
    RENAME COLUMN `sequence_date_rule` TO `sequence_date_rule_code`;

SELECT column_name, column_type
FROM information_schema.columns
WHERE table_schema = 'te_common'
  AND table_name = 'cm_sequence_policy_definition'
  AND column_name IN (
      'sequence_date_rule_code'
  )
ORDER BY ordinal_position;

SELECT COUNT(*) AS row_count FROM `te_common`.`cm_sequence_policy_definition`;

/* PATCH 010 - te_common.cm_verified_sql_query */

CREATE TABLE `te_common`.`cm_verified_sql_query_backup_rename_20260720_01`
LIKE `te_common`.`cm_verified_sql_query`;

START TRANSACTION;

INSERT INTO `te_common`.`cm_verified_sql_query_backup_rename_20260720_01`
SELECT * FROM `te_common`.`cm_verified_sql_query`;

COMMIT;

SELECT
    (SELECT COUNT(*) FROM `te_common`.`cm_verified_sql_query`) AS original_count,
    (SELECT COUNT(*) FROM `te_common`.`cm_verified_sql_query_backup_rename_20260720_01`) AS backup_count;

ALTER TABLE `te_common`.`cm_verified_sql_query`
    RENAME COLUMN `created_ip_address` TO `created_ip`,
    RENAME COLUMN `updated_ip_address` TO `updated_ip`,
    RENAME COLUMN `deleted_ip_address` TO `deleted_ip`;

SELECT column_name, column_type
FROM information_schema.columns
WHERE table_schema = 'te_common'
  AND table_name = 'cm_verified_sql_query'
  AND column_name IN (
      'created_ip',
      'updated_ip',
      'deleted_ip'
  )
ORDER BY ordinal_position;

SELECT COUNT(*) AS row_count FROM `te_common`.`cm_verified_sql_query`;

/* PATCH 011 - te_common.sql_guard_execution_log */

CREATE TABLE `te_common`.`sql_guard_execution_log_backup_rename_20260720_01`
LIKE `te_common`.`sql_guard_execution_log`;

START TRANSACTION;

INSERT INTO `te_common`.`sql_guard_execution_log_backup_rename_20260720_01`
SELECT * FROM `te_common`.`sql_guard_execution_log`;

COMMIT;

SELECT
    (SELECT COUNT(*) FROM `te_common`.`sql_guard_execution_log`) AS original_count,
    (SELECT COUNT(*) FROM `te_common`.`sql_guard_execution_log_backup_rename_20260720_01`) AS backup_count;

ALTER TABLE `te_common`.`sql_guard_execution_log`
    RENAME COLUMN `executed_at` TO `executed_dt`;

SELECT column_name, column_type
FROM information_schema.columns
WHERE table_schema = 'te_common'
  AND table_name = 'sql_guard_execution_log'
  AND column_name IN (
      'executed_dt'
  )
ORDER BY ordinal_position;

SELECT COUNT(*) AS row_count FROM `te_common`.`sql_guard_execution_log`;

/* PATCH 012 - te_common.system_menu */

CREATE TABLE `te_common`.`system_menu_backup_rename_20260720_01`
LIKE `te_common`.`system_menu`;

START TRANSACTION;

INSERT INTO `te_common`.`system_menu_backup_rename_20260720_01`
SELECT * FROM `te_common`.`system_menu`;

COMMIT;

SELECT
    (SELECT COUNT(*) FROM `te_common`.`system_menu`) AS original_count,
    (SELECT COUNT(*) FROM `te_common`.`system_menu_backup_rename_20260720_01`) AS backup_count;

ALTER TABLE `te_common`.`system_menu`
    RENAME COLUMN `menu_sort_order` TO `menu_sort_no`;

SELECT column_name, column_type
FROM information_schema.columns
WHERE table_schema = 'te_common'
  AND table_name = 'system_menu'
  AND column_name IN (
      'menu_sort_no'
  )
ORDER BY ordinal_position;

SELECT COUNT(*) AS row_count FROM `te_common`.`system_menu`;

/* PATCH 013 - te_common.system_menu_button */

CREATE TABLE `te_common`.`system_menu_button_backup_rename_20260720_01`
LIKE `te_common`.`system_menu_button`;

START TRANSACTION;

INSERT INTO `te_common`.`system_menu_button_backup_rename_20260720_01`
SELECT * FROM `te_common`.`system_menu_button`;

COMMIT;

SELECT
    (SELECT COUNT(*) FROM `te_common`.`system_menu_button`) AS original_count,
    (SELECT COUNT(*) FROM `te_common`.`system_menu_button_backup_rename_20260720_01`) AS backup_count;

ALTER TABLE `te_common`.`system_menu_button`
    RENAME COLUMN `button_sort_order` TO `button_sort_no`;

SELECT column_name, column_type
FROM information_schema.columns
WHERE table_schema = 'te_common'
  AND table_name = 'system_menu_button'
  AND column_name IN (
      'button_sort_no'
  )
ORDER BY ordinal_position;

SELECT COUNT(*) AS row_count FROM `te_common`.`system_menu_button`;

/* FINAL VERIFICATION */
SELECT table_schema, table_name, column_name, column_type
FROM information_schema.columns
WHERE (table_schema, table_name, column_name) IN (
    ('te_story_platform', 'sp_domain', 'sort_no'),
    ('te_story_platform', 'sp_execution_history', 'repository_status_code'),
    ('te_story_platform', 'sp_execution_history', 'mongodb_status_code'),
    ('te_story_platform', 'sp_execution_history', 'execution_status_code'),
    ('te_story_platform', 'sp_execution_history', 'history_status_code'),
    ('te_story_platform', 'sp_identifier_sequence', 'sequence_dt'),
    ('te_story_platform', 'sp_knowledge_type_hold', 'sort_no'),
    ('te_common', 'cm_data_lifecycle_index', 'disposed_dt'),
    ('te_common', 'cm_member_private', 'birth_dt'),
    ('te_common', 'cm_sequence', 'sequence_dt'),
    ('te_common', 'cm_sequence_policy', 'sort_no'),
    ('te_common', 'cm_sequence_policy_definition', 'sequence_date_rule_code'),
    ('te_common', 'cm_verified_sql_query', 'created_ip'),
    ('te_common', 'cm_verified_sql_query', 'updated_ip'),
    ('te_common', 'cm_verified_sql_query', 'deleted_ip'),
    ('te_common', 'sql_guard_execution_log', 'executed_dt'),
    ('te_common', 'system_menu', 'menu_sort_no'),
    ('te_common', 'system_menu_button', 'button_sort_no')
)
ORDER BY table_schema, table_name, ordinal_position;

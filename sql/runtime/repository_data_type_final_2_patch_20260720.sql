/*
File Name : repository_data_type_final_2_patch_20260720.sql
Purpose   : Final two-column Repository Data Type maintenance
*/

SET NAMES utf8mb4;

/* =============================================================
PATCH 001 - te_health_companion.at_audit.target_pk_value
============================================================= */

CREATE TABLE `te_health_companion`.`at_audit_backup_20260720_final`
LIKE `te_health_companion`.`at_audit`;

START TRANSACTION;

INSERT INTO `te_health_companion`.`at_audit_backup_20260720_final`
SELECT *
FROM `te_health_companion`.`at_audit`;

COMMIT;

SELECT
    (SELECT COUNT(*) FROM `te_health_companion`.`at_audit`) AS original_count,
    (SELECT COUNT(*) FROM `te_health_companion`.`at_audit_backup_20260720_final`) AS backup_count;

ALTER TABLE `te_health_companion`.`at_audit`
    DROP INDEX `ix_at_audit_target`,
    MODIFY COLUMN `target_pk_value` VARCHAR(2000) NULL DEFAULT NULL
        COMMENT '대상 PK 값',
    ADD INDEX `ix_at_audit_target`
        (`target_table_name`, `target_pk_value`(500));

SELECT
    column_name,
    column_type,
    is_nullable,
    column_default,
    column_comment
FROM information_schema.columns
WHERE table_schema = 'te_health_companion'
  AND table_name = 'at_audit'
  AND column_name = 'target_pk_value';

SELECT COUNT(*) AS row_count
FROM `te_health_companion`.`at_audit`;

/* =============================================================
PATCH 002 - te_common.cm_verified_sql_query.certified_level
============================================================= */

CREATE TABLE `te_common`.`cm_verified_sql_query_backup_20260720_final`
LIKE `te_common`.`cm_verified_sql_query`;

START TRANSACTION;

INSERT INTO `te_common`.`cm_verified_sql_query_backup_20260720_final`
SELECT *
FROM `te_common`.`cm_verified_sql_query`;

COMMIT;

SELECT
    (SELECT COUNT(*) FROM `te_common`.`cm_verified_sql_query`) AS original_count,
    (SELECT COUNT(*) FROM `te_common`.`cm_verified_sql_query_backup_20260720_final`) AS backup_count;

ALTER TABLE `te_common`.`cm_verified_sql_query`
    CHANGE COLUMN `certified_level` `certified_level_code`
        VARCHAR(99) NULL DEFAULT NULL
        COMMENT '검증 인증 수준 코드';

SELECT
    column_name,
    column_type,
    is_nullable,
    column_default,
    column_comment
FROM information_schema.columns
WHERE table_schema = 'te_common'
  AND table_name = 'cm_verified_sql_query'
  AND column_name = 'certified_level_code';

SELECT
    certified_level_code,
    COUNT(*) AS row_count
FROM `te_common`.`cm_verified_sql_query`
GROUP BY certified_level_code
ORDER BY certified_level_code;

SELECT COUNT(*) AS row_count
FROM `te_common`.`cm_verified_sql_query`;

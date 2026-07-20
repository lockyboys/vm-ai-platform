/*
File Name : common_object_report_type_maintenance_20260720.sql
Purpose   : One-time hardcoded COMMON Object, Relation, Report and description field maintenance.
Scope     : 34 explicit columns across 19 tables.
Dependencies: cm_common_code_group and cm_common_code key columns are included for FK compatibility.
Safety    : No dynamic SQL. Existing NULL, DEFAULT, COMMENT and key attributes are preserved.
DDL Note  : MariaDB DDL auto-commits. Execute only after a database backup/snapshot.
*/

SET NAMES utf8mb4;

SELECT 'BEFORE' AS verification_step, table_name, column_name, column_type
FROM information_schema.columns WHERE table_schema='te_common' AND (table_name,column_name) IN
(
    ('cm_audit_policy', 'description'),
    ('cm_business_domain', 'description'),
    ('cm_change_history', 'change_story'),
    ('cm_common_code', 'code'),
    ('cm_common_code', 'group_code'),
    ('cm_common_code_group', 'group_code'),
    ('cm_consent_history', 'change_story'),
    ('cm_data_classification', 'description'),
    ('cm_data_lifecycle_index', 'change_story'),
    ('cm_data_type', 'description'),
    ('cm_sequence_format', 'description'),
    ('cm_sequence_policy', 'description'),
    ('cm_sequence_rule', 'description'),
    ('cm_storage_policy', 'change_story'),
    ('cm_storage_repository', 'change_story'),
    ('health_report', 'change_story'),
    ('health_report', 'health_report_id'),
    ('health_report', 'patient_id'),
    ('health_report', 'report_title'),
    ('health_report_backup_20260624', 'health_report_id'),
    ('health_report_backup_20260624', 'patient_id'),
    ('health_report_backup_20260624', 'report_title'),
    ('md_object', 'description'),
    ('md_object', 'md_object_id'),
    ('md_object', 'object_code'),
    ('md_object', 'object_name'),
    ('md_object', 'object_type_code'),
    ('md_object', 'object_type_group_code'),
    ('md_relation', 'description'),
    ('md_relation', 'md_relation_id'),
    ('md_relation', 'relation_type_code'),
    ('md_relation', 'source_md_object_id'),
    ('md_relation', 'target_md_object_id'),
    ('sql_guard_verification_log', 'change_story')
) ORDER BY table_name, ordinal_position;

/* Drop affected FK constraints. */
ALTER TABLE `te_common`.`cm_common_code` DROP FOREIGN KEY `fk_cm_common_code_group`;
ALTER TABLE `te_common`.`md_object` DROP FOREIGN KEY `fk_md_object_type`;
ALTER TABLE `te_common`.`md_relation` DROP FOREIGN KEY `fk_md_relation_source`;
ALTER TABLE `te_common`.`md_relation` DROP FOREIGN KEY `fk_md_relation_target`;

/* Remove AUTO_INCREMENT before converting health_report_id to VARCHAR(99). */
ALTER TABLE `te_common`.`health_report`
    MODIFY COLUMN `health_report_id` bigint(20) NOT NULL;

/* Explicit physical changes. */
ALTER TABLE `te_common`.`cm_audit_policy`
    MODIFY COLUMN `description` VARCHAR(2000) DEFAULT NULL COMMENT '설명';

ALTER TABLE `te_common`.`cm_business_domain`
    MODIFY COLUMN `description` VARCHAR(2000) DEFAULT NULL COMMENT '설명';

ALTER TABLE `te_common`.`cm_change_history`
    MODIFY COLUMN `change_story` VARCHAR(2000) NOT NULL COMMENT '변경 스토리: 목적어 + 동사';

ALTER TABLE `te_common`.`cm_common_code`
    MODIFY COLUMN `group_code` VARCHAR(99) NOT NULL,
    MODIFY COLUMN `code` VARCHAR(99) NOT NULL;

ALTER TABLE `te_common`.`cm_common_code_group`
    MODIFY COLUMN `group_code` VARCHAR(99) NOT NULL;

ALTER TABLE `te_common`.`cm_consent_history`
    MODIFY COLUMN `change_story` VARCHAR(2000) DEFAULT NULL;

ALTER TABLE `te_common`.`cm_data_classification`
    MODIFY COLUMN `description` VARCHAR(2000) DEFAULT NULL;

ALTER TABLE `te_common`.`cm_data_lifecycle_index`
    MODIFY COLUMN `change_story` VARCHAR(2000) DEFAULT NULL;

ALTER TABLE `te_common`.`cm_data_type`
    MODIFY COLUMN `description` VARCHAR(2000) DEFAULT NULL;

ALTER TABLE `te_common`.`cm_sequence_format`
    MODIFY COLUMN `description` VARCHAR(2000) DEFAULT NULL COMMENT '설명';

ALTER TABLE `te_common`.`cm_sequence_policy`
    MODIFY COLUMN `description` VARCHAR(2000) DEFAULT NULL COMMENT '설명';

ALTER TABLE `te_common`.`cm_sequence_rule`
    MODIFY COLUMN `description` VARCHAR(2000) DEFAULT NULL COMMENT '설명';

ALTER TABLE `te_common`.`cm_storage_policy`
    MODIFY COLUMN `change_story` VARCHAR(2000) DEFAULT NULL;

ALTER TABLE `te_common`.`cm_storage_repository`
    MODIFY COLUMN `change_story` VARCHAR(2000) DEFAULT NULL;

ALTER TABLE `te_common`.`health_report`
    MODIFY COLUMN `health_report_id` VARCHAR(99) NOT NULL,
    MODIFY COLUMN `patient_id` VARCHAR(99) NOT NULL,
    MODIFY COLUMN `report_title` VARCHAR(500) NOT NULL,
    MODIFY COLUMN `change_story` VARCHAR(2000) DEFAULT NULL;

ALTER TABLE `te_common`.`health_report_backup_20260624`
    MODIFY COLUMN `health_report_id` VARCHAR(99) NOT NULL DEFAULT 0,
    MODIFY COLUMN `patient_id` VARCHAR(99) NOT NULL,
    MODIFY COLUMN `report_title` VARCHAR(500) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL;

ALTER TABLE `te_common`.`md_object`
    MODIFY COLUMN `md_object_id` VARCHAR(99) NOT NULL,
    MODIFY COLUMN `object_type_group_code` VARCHAR(99) NOT NULL DEFAULT 'OBJECT_TYPE',
    MODIFY COLUMN `object_type_code` VARCHAR(99) NOT NULL,
    MODIFY COLUMN `object_code` VARCHAR(99) NOT NULL,
    MODIFY COLUMN `object_name` VARCHAR(150) NOT NULL,
    MODIFY COLUMN `description` VARCHAR(2000) DEFAULT NULL;

ALTER TABLE `te_common`.`md_relation`
    MODIFY COLUMN `md_relation_id` VARCHAR(99) NOT NULL,
    MODIFY COLUMN `source_md_object_id` VARCHAR(99) NOT NULL,
    MODIFY COLUMN `target_md_object_id` VARCHAR(99) NOT NULL,
    MODIFY COLUMN `relation_type_code` VARCHAR(99) NOT NULL,
    MODIFY COLUMN `description` VARCHAR(2000) DEFAULT NULL;

ALTER TABLE `te_common`.`sql_guard_verification_log`
    MODIFY COLUMN `change_story` VARCHAR(2000) DEFAULT NULL;

/* Restore original FK constraints. */
ALTER TABLE `te_common`.`cm_common_code` ADD CONSTRAINT `fk_cm_common_code_group` FOREIGN KEY (`group_code`) REFERENCES `cm_common_code_group` (`group_code`);
ALTER TABLE `te_common`.`md_object` ADD CONSTRAINT `fk_md_object_type` FOREIGN KEY (`object_type_group_code`, `object_type_code`) REFERENCES `cm_common_code` (`group_code`, `code`);
ALTER TABLE `te_common`.`md_relation` ADD CONSTRAINT `fk_md_relation_source` FOREIGN KEY (`source_md_object_id`) REFERENCES `md_object` (`md_object_id`);
ALTER TABLE `te_common`.`md_relation` ADD CONSTRAINT `fk_md_relation_target` FOREIGN KEY (`target_md_object_id`) REFERENCES `md_object` (`md_object_id`);

SELECT 'AFTER' AS verification_step, table_name, column_name, column_type
FROM information_schema.columns WHERE table_schema='te_common' AND (table_name,column_name) IN
(
    ('cm_audit_policy', 'description'),
    ('cm_business_domain', 'description'),
    ('cm_change_history', 'change_story'),
    ('cm_common_code', 'code'),
    ('cm_common_code', 'group_code'),
    ('cm_common_code_group', 'group_code'),
    ('cm_consent_history', 'change_story'),
    ('cm_data_classification', 'description'),
    ('cm_data_lifecycle_index', 'change_story'),
    ('cm_data_type', 'description'),
    ('cm_sequence_format', 'description'),
    ('cm_sequence_policy', 'description'),
    ('cm_sequence_rule', 'description'),
    ('cm_storage_policy', 'change_story'),
    ('cm_storage_repository', 'change_story'),
    ('health_report', 'change_story'),
    ('health_report', 'health_report_id'),
    ('health_report', 'patient_id'),
    ('health_report', 'report_title'),
    ('health_report_backup_20260624', 'health_report_id'),
    ('health_report_backup_20260624', 'patient_id'),
    ('health_report_backup_20260624', 'report_title'),
    ('md_object', 'description'),
    ('md_object', 'md_object_id'),
    ('md_object', 'object_code'),
    ('md_object', 'object_name'),
    ('md_object', 'object_type_code'),
    ('md_object', 'object_type_group_code'),
    ('md_relation', 'description'),
    ('md_relation', 'md_relation_id'),
    ('md_relation', 'relation_type_code'),
    ('md_relation', 'source_md_object_id'),
    ('md_relation', 'target_md_object_id'),
    ('sql_guard_verification_log', 'change_story')
) ORDER BY table_name, ordinal_position;

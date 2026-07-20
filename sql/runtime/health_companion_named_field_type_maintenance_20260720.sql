/*
File Name : health_companion_named_field_type_maintenance_20260720.sql
Purpose   : One-time hardcoded HEALTH_COMPANION named-field type maintenance.
Scope     : 45 explicit columns across 5 tables.
Directive : Includes every occurrence of the user-approved field names.
Safety    : No dynamic SQL. Existing NULL, DEFAULT, COMMENT and key attributes are preserved.
DDL Note  : MariaDB DDL auto-commits. Execute only after a database backup/snapshot.
*/

SET NAMES utf8mb4;

SIGNAL SQLSTATE '45000'
    SET MESSAGE_TEXT = 'CANCELLED: accepted report exceptions; no physical ALTER';

SELECT 'BEFORE' AS verification_step, table_name, column_name, column_type
FROM information_schema.columns WHERE table_schema='te_health_companion' AND (table_name,column_name) IN
(
    ('ac_action', 'action_id'),
    ('ac_action', 'action_code'),
    ('ac_action', 'decision_id'),
    ('ac_action', 'action_type_code'),
    ('ac_action', 'action_status_code'),
    ('ac_action', 'action_target_type_code'),
    ('ac_action', 'action_target_id'),
    ('ac_action', 'action_value'),
    ('ac_action', 'result_code'),
    ('ac_action', 'created_by'),
    ('ac_action', 'updated_by'),
    ('ac_action', 'deleted_by'),
    ('ac_action', 'program_id'),
    ('ac_action', 'client_ip'),
    ('at_audit', 'audit_id'),
    ('at_audit', 'audit_code'),
    ('at_audit', 'audit_type_code'),
    ('at_audit', 'business_domain_code'),
    ('at_audit', 'target_table_name'),
    ('at_audit', 'decision_id'),
    ('at_audit', 'action_id'),
    ('at_audit', 'created_by'),
    ('at_audit', 'updated_by'),
    ('at_audit', 'deleted_by'),
    ('at_audit', 'program_id'),
    ('at_audit', 'client_ip'),
    ('dc_decision', 'decision_id'),
    ('dc_decision', 'created_by'),
    ('dc_decision', 'updated_by'),
    ('dc_decision', 'deleted_by'),
    ('dc_decision', 'program_id'),
    ('dc_decision', 'client_ip'),
    ('dc_decision_detail', 'decision_id'),
    ('dc_decision_detail', 'created_by'),
    ('dc_decision_detail', 'updated_by'),
    ('dc_decision_detail', 'deleted_by'),
    ('dc_decision_detail', 'program_id'),
    ('dc_decision_detail', 'client_ip'),
    ('fb_feedback', 'decision_id'),
    ('fb_feedback', 'action_id'),
    ('fb_feedback', 'created_by'),
    ('fb_feedback', 'updated_by'),
    ('fb_feedback', 'deleted_by'),
    ('fb_feedback', 'program_id'),
    ('fb_feedback', 'client_ip')
) ORDER BY table_name, ordinal_position;

/* Drop every FK affected by action_id/decision_id changes. */
ALTER TABLE `te_health_companion`.`ac_action` DROP FOREIGN KEY `fk_ac_action_decision`;
ALTER TABLE `te_health_companion`.`dc_decision_detail` DROP FOREIGN KEY `fk_dc_detail_decision`;
ALTER TABLE `te_health_companion`.`fb_feedback` DROP FOREIGN KEY `fk_fb_feedback_action`;
ALTER TABLE `te_health_companion`.`fb_feedback` DROP FOREIGN KEY `fk_fb_feedback_decision`;

/* Explicit physical changes. */
ALTER TABLE `te_health_companion`.`ac_action`
    MODIFY COLUMN `action_id` VARCHAR(99) NOT NULL COMMENT '실행 ID',
    MODIFY COLUMN `action_code` VARCHAR(99) NOT NULL COMMENT '실행 코드',
    MODIFY COLUMN `decision_id` VARCHAR(99) NOT NULL COMMENT '판단 ID',
    MODIFY COLUMN `action_type_code` VARCHAR(99) NOT NULL COMMENT '실행 유형 코드',
    MODIFY COLUMN `action_status_code` VARCHAR(99) NOT NULL DEFAULT 'READY' COMMENT '실행 상태 코드',
    MODIFY COLUMN `action_target_type_code` VARCHAR(99) DEFAULT NULL COMMENT '실행 대상 유형 코드',
    MODIFY COLUMN `action_target_id` VARCHAR(99) DEFAULT NULL COMMENT '실행 대상 ID',
    MODIFY COLUMN `action_value` VARCHAR(2000) DEFAULT NULL COMMENT '실행 값',
    MODIFY COLUMN `result_code` VARCHAR(99) DEFAULT NULL COMMENT '결과 코드',
    MODIFY COLUMN `created_by` VARCHAR(99) NOT NULL DEFAULT 'SYSTEM',
    MODIFY COLUMN `updated_by` VARCHAR(99) NOT NULL DEFAULT 'SYSTEM',
    MODIFY COLUMN `deleted_by` VARCHAR(99) DEFAULT NULL,
    MODIFY COLUMN `program_id` VARCHAR(99) DEFAULT NULL,
    MODIFY COLUMN `client_ip` VARCHAR(99) DEFAULT NULL;

ALTER TABLE `te_health_companion`.`at_audit`
    MODIFY COLUMN `audit_id` VARCHAR(99) NOT NULL COMMENT '감사 ID',
    MODIFY COLUMN `audit_code` VARCHAR(99) NOT NULL COMMENT '감사 코드',
    MODIFY COLUMN `audit_type_code` VARCHAR(99) NOT NULL COMMENT '감사 유형 코드',
    MODIFY COLUMN `business_domain_code` VARCHAR(99) DEFAULT NULL COMMENT '업무 도메인 코드',
    MODIFY COLUMN `target_table_name` VARCHAR(150) DEFAULT NULL COMMENT '대상 테이블명',
    MODIFY COLUMN `decision_id` VARCHAR(99) DEFAULT NULL COMMENT '판단 ID',
    MODIFY COLUMN `action_id` VARCHAR(99) DEFAULT NULL COMMENT '실행 ID',
    MODIFY COLUMN `created_by` VARCHAR(99) NOT NULL DEFAULT 'SYSTEM',
    MODIFY COLUMN `updated_by` VARCHAR(99) NOT NULL DEFAULT 'SYSTEM',
    MODIFY COLUMN `deleted_by` VARCHAR(99) DEFAULT NULL,
    MODIFY COLUMN `program_id` VARCHAR(99) DEFAULT NULL,
    MODIFY COLUMN `client_ip` VARCHAR(99) DEFAULT NULL;

ALTER TABLE `te_health_companion`.`dc_decision`
    MODIFY COLUMN `decision_id` VARCHAR(99) NOT NULL COMMENT '판단 ID',
    MODIFY COLUMN `created_by` VARCHAR(99) NOT NULL DEFAULT 'SYSTEM',
    MODIFY COLUMN `updated_by` VARCHAR(99) NOT NULL DEFAULT 'SYSTEM',
    MODIFY COLUMN `deleted_by` VARCHAR(99) DEFAULT NULL,
    MODIFY COLUMN `program_id` VARCHAR(99) DEFAULT NULL,
    MODIFY COLUMN `client_ip` VARCHAR(99) DEFAULT NULL;

ALTER TABLE `te_health_companion`.`dc_decision_detail`
    MODIFY COLUMN `decision_id` VARCHAR(99) NOT NULL COMMENT '판단 ID',
    MODIFY COLUMN `created_by` VARCHAR(99) NOT NULL DEFAULT 'SYSTEM',
    MODIFY COLUMN `updated_by` VARCHAR(99) NOT NULL DEFAULT 'SYSTEM',
    MODIFY COLUMN `deleted_by` VARCHAR(99) DEFAULT NULL,
    MODIFY COLUMN `program_id` VARCHAR(99) DEFAULT NULL,
    MODIFY COLUMN `client_ip` VARCHAR(99) DEFAULT NULL;

ALTER TABLE `te_health_companion`.`fb_feedback`
    MODIFY COLUMN `decision_id` VARCHAR(99) DEFAULT NULL COMMENT '판단 ID',
    MODIFY COLUMN `action_id` VARCHAR(99) DEFAULT NULL COMMENT '실행 ID',
    MODIFY COLUMN `created_by` VARCHAR(99) NOT NULL DEFAULT 'SYSTEM',
    MODIFY COLUMN `updated_by` VARCHAR(99) NOT NULL DEFAULT 'SYSTEM',
    MODIFY COLUMN `deleted_by` VARCHAR(99) DEFAULT NULL,
    MODIFY COLUMN `program_id` VARCHAR(99) DEFAULT NULL,
    MODIFY COLUMN `client_ip` VARCHAR(99) DEFAULT NULL;

/* Restore original FK constraints. */
ALTER TABLE `te_health_companion`.`ac_action` ADD CONSTRAINT `fk_ac_action_decision` FOREIGN KEY (`decision_id`) REFERENCES `dc_decision` (`decision_id`);
ALTER TABLE `te_health_companion`.`dc_decision_detail` ADD CONSTRAINT `fk_dc_detail_decision` FOREIGN KEY (`decision_id`) REFERENCES `dc_decision` (`decision_id`);
ALTER TABLE `te_health_companion`.`fb_feedback` ADD CONSTRAINT `fk_fb_feedback_action` FOREIGN KEY (`action_id`) REFERENCES `ac_action` (`action_id`);
ALTER TABLE `te_health_companion`.`fb_feedback` ADD CONSTRAINT `fk_fb_feedback_decision` FOREIGN KEY (`decision_id`) REFERENCES `dc_decision` (`decision_id`);

SELECT 'AFTER' AS verification_step, table_name, column_name, column_type
FROM information_schema.columns WHERE table_schema='te_health_companion' AND (table_name,column_name) IN
(
    ('ac_action', 'action_id'),
    ('ac_action', 'action_code'),
    ('ac_action', 'decision_id'),
    ('ac_action', 'action_type_code'),
    ('ac_action', 'action_status_code'),
    ('ac_action', 'action_target_type_code'),
    ('ac_action', 'action_target_id'),
    ('ac_action', 'action_value'),
    ('ac_action', 'result_code'),
    ('ac_action', 'created_by'),
    ('ac_action', 'updated_by'),
    ('ac_action', 'deleted_by'),
    ('ac_action', 'program_id'),
    ('ac_action', 'client_ip'),
    ('at_audit', 'audit_id'),
    ('at_audit', 'audit_code'),
    ('at_audit', 'audit_type_code'),
    ('at_audit', 'business_domain_code'),
    ('at_audit', 'target_table_name'),
    ('at_audit', 'decision_id'),
    ('at_audit', 'action_id'),
    ('at_audit', 'created_by'),
    ('at_audit', 'updated_by'),
    ('at_audit', 'deleted_by'),
    ('at_audit', 'program_id'),
    ('at_audit', 'client_ip'),
    ('dc_decision', 'decision_id'),
    ('dc_decision', 'created_by'),
    ('dc_decision', 'updated_by'),
    ('dc_decision', 'deleted_by'),
    ('dc_decision', 'program_id'),
    ('dc_decision', 'client_ip'),
    ('dc_decision_detail', 'decision_id'),
    ('dc_decision_detail', 'created_by'),
    ('dc_decision_detail', 'updated_by'),
    ('dc_decision_detail', 'deleted_by'),
    ('dc_decision_detail', 'program_id'),
    ('dc_decision_detail', 'client_ip'),
    ('fb_feedback', 'decision_id'),
    ('fb_feedback', 'action_id'),
    ('fb_feedback', 'created_by'),
    ('fb_feedback', 'updated_by'),
    ('fb_feedback', 'deleted_by'),
    ('fb_feedback', 'program_id'),
    ('fb_feedback', 'client_ip')
) ORDER BY table_name, ordinal_position;

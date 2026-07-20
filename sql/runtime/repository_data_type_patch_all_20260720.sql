/*
File Name : repository_data_type_patch_all_20260720.sql
Purpose   : One-time hardcoded full Repository Data Type Patch.
Tables    : 69
Columns   : 398
HOLD      : 20 unsafe columns
*/

SET NAMES utf8mb4;
SET FOREIGN_KEY_CHECKS = 0;

/* =============================================================
PATCH 001 START
Database : te_health_companion
Table    : ac_action
Columns  : 1
Rows     : 2
Backup   : ac_action_backup_20260720_01
============================================================= */

-- 1. 변경 전 백업
CREATE TABLE `te_health_companion`.`ac_action_backup_20260720_01`
LIKE `te_health_companion`.`ac_action`;

START TRANSACTION;

INSERT INTO `te_health_companion`.`ac_action_backup_20260720_01`
SELECT *
FROM `te_health_companion`.`ac_action`;

COMMIT;

-- 2. 백업 검증
SELECT
    (SELECT COUNT(*) FROM `te_health_companion`.`ac_action`) AS original_count,
    (SELECT COUNT(*) FROM `te_health_companion`.`ac_action_backup_20260720_01`) AS backup_count;

-- 3. ALTER TABLE 문 실행
ALTER TABLE `te_health_companion`.`ac_action`
    MODIFY COLUMN `remark` VARCHAR(2000) NULL DEFAULT NULL COMMENT '비고';

-- 4. 변경 결과 확인
SELECT column_name, column_type
FROM information_schema.columns
WHERE table_schema = 'te_health_companion'
  AND table_name = 'ac_action'
  AND column_name IN (
      'remark'
  )
ORDER BY ordinal_position;

SELECT COUNT(*) AS row_count FROM `te_health_companion`.`ac_action`;

/* PATCH 001 END */

/* =============================================================
PATCH 002 START
Database : te_health_companion
Table    : at_audit
Columns  : 8
Rows     : 1
Backup   : at_audit_backup_20260720_01
============================================================= */

-- 1. 변경 전 백업
CREATE TABLE `te_health_companion`.`at_audit_backup_20260720_01`
LIKE `te_health_companion`.`at_audit`;

START TRANSACTION;

INSERT INTO `te_health_companion`.`at_audit_backup_20260720_01`
SELECT *
FROM `te_health_companion`.`at_audit`;

COMMIT;

-- 2. 백업 검증
SELECT
    (SELECT COUNT(*) FROM `te_health_companion`.`at_audit`) AS original_count,
    (SELECT COUNT(*) FROM `te_health_companion`.`at_audit_backup_20260720_01`) AS backup_count;

-- 3. ALTER TABLE 문 실행
ALTER TABLE `te_health_companion`.`at_audit`
    MODIFY COLUMN `target_pk_value` VARCHAR(2000) NULL DEFAULT NULL COMMENT '대상 PK 값',
    MODIFY COLUMN `engine_name` VARCHAR(150) NULL DEFAULT NULL COMMENT '엔진명',
    MODIFY COLUMN `rule_id` VARCHAR(99) NULL DEFAULT NULL COMMENT '규칙 ID',
    MODIFY COLUMN `evidence_id` VARCHAR(99) NULL DEFAULT NULL COMMENT '근거 ID',
    MODIFY COLUMN `audit_result_code` VARCHAR(99) NOT NULL DEFAULT '''SUCCESS''' COMMENT '감사 결과 코드',
    MODIFY COLUMN `ai_provider_code` VARCHAR(99) NULL DEFAULT NULL COMMENT 'AI 제공자 코드',
    MODIFY COLUMN `ai_model_name` VARCHAR(150) NULL DEFAULT NULL COMMENT 'AI 모델명',
    MODIFY COLUMN `remark` VARCHAR(2000) NULL DEFAULT NULL COMMENT '비고';

-- 4. 변경 결과 확인
SELECT column_name, column_type
FROM information_schema.columns
WHERE table_schema = 'te_health_companion'
  AND table_name = 'at_audit'
  AND column_name IN (
      'target_pk_value',
      'engine_name',
      'rule_id',
      'evidence_id',
      'audit_result_code',
      'ai_provider_code',
      'ai_model_name',
      'remark'
  )
ORDER BY ordinal_position;

SELECT COUNT(*) AS row_count FROM `te_health_companion`.`at_audit`;

/* PATCH 002 END */

/* =============================================================
PATCH 003 START
Database : te_health_companion
Table    : dc_decision_detail
Columns  : 8
Rows     : 1
Backup   : dc_decision_detail_backup_20260720_01
============================================================= */

-- 1. 변경 전 백업
CREATE TABLE `te_health_companion`.`dc_decision_detail_backup_20260720_01`
LIKE `te_health_companion`.`dc_decision_detail`;

START TRANSACTION;

INSERT INTO `te_health_companion`.`dc_decision_detail_backup_20260720_01`
SELECT *
FROM `te_health_companion`.`dc_decision_detail`;

COMMIT;

-- 2. 백업 검증
SELECT
    (SELECT COUNT(*) FROM `te_health_companion`.`dc_decision_detail`) AS original_count,
    (SELECT COUNT(*) FROM `te_health_companion`.`dc_decision_detail_backup_20260720_01`) AS backup_count;

-- 3. ALTER TABLE 문 실행
ALTER TABLE `te_health_companion`.`dc_decision_detail`
    MODIFY COLUMN `decision_detail_id` VARCHAR(99) NOT NULL COMMENT '판단 상세 ID',
    MODIFY COLUMN `rule_id` VARCHAR(99) NULL DEFAULT NULL COMMENT '적용 규칙 ID',
    MODIFY COLUMN `evidence_id` VARCHAR(99) NULL DEFAULT NULL COMMENT '적용 근거 ID',
    MODIFY COLUMN `input_field_code` VARCHAR(99) NULL DEFAULT NULL COMMENT '입력 필드 코드',
    MODIFY COLUMN `input_value` VARCHAR(2000) NULL DEFAULT NULL COMMENT '입력 값',
    MODIFY COLUMN `condition_result_code` VARCHAR(99) NULL DEFAULT NULL COMMENT '조건 결과 코드',
    MODIFY COLUMN `detail_summary` VARCHAR(2000) NULL DEFAULT NULL COMMENT '상세 요약',
    MODIFY COLUMN `remark` VARCHAR(2000) NULL DEFAULT NULL COMMENT '비고';

-- 4. 변경 결과 확인
SELECT column_name, column_type
FROM information_schema.columns
WHERE table_schema = 'te_health_companion'
  AND table_name = 'dc_decision_detail'
  AND column_name IN (
      'decision_detail_id',
      'rule_id',
      'evidence_id',
      'input_field_code',
      'input_value',
      'condition_result_code',
      'detail_summary',
      'remark'
  )
ORDER BY ordinal_position;

SELECT COUNT(*) AS row_count FROM `te_health_companion`.`dc_decision_detail`;

/* PATCH 003 END */

/* =============================================================
PATCH 004 START
Database : te_health_companion
Table    : fb_feedback
Columns  : 7
Rows     : 1
Backup   : fb_feedback_backup_20260720_01
============================================================= */

-- 1. 변경 전 백업
CREATE TABLE `te_health_companion`.`fb_feedback_backup_20260720_01`
LIKE `te_health_companion`.`fb_feedback`;

START TRANSACTION;

INSERT INTO `te_health_companion`.`fb_feedback_backup_20260720_01`
SELECT *
FROM `te_health_companion`.`fb_feedback`;

COMMIT;

-- 2. 백업 검증
SELECT
    (SELECT COUNT(*) FROM `te_health_companion`.`fb_feedback`) AS original_count,
    (SELECT COUNT(*) FROM `te_health_companion`.`fb_feedback_backup_20260720_01`) AS backup_count;

-- 3. ALTER TABLE 문 실행
ALTER TABLE `te_health_companion`.`fb_feedback`
    MODIFY COLUMN `feedback_id` VARCHAR(99) NOT NULL COMMENT '피드백 ID',
    MODIFY COLUMN `feedback_code` VARCHAR(99) NOT NULL COMMENT '피드백 코드',
    MODIFY COLUMN `user_id` VARCHAR(99) NOT NULL COMMENT '사용자 ID',
    MODIFY COLUMN `feedback_type_code` VARCHAR(99) NOT NULL COMMENT '피드백 유형 코드',
    MODIFY COLUMN `rating_score` DECIMAL(10,4) NULL DEFAULT NULL COMMENT '평점',
    MODIFY COLUMN `status_code` VARCHAR(99) NOT NULL DEFAULT '''ACTIVE''' COMMENT '상태 코드',
    MODIFY COLUMN `remark` VARCHAR(2000) NULL DEFAULT NULL COMMENT '비고';

-- 4. 변경 결과 확인
SELECT column_name, column_type
FROM information_schema.columns
WHERE table_schema = 'te_health_companion'
  AND table_name = 'fb_feedback'
  AND column_name IN (
      'feedback_id',
      'feedback_code',
      'user_id',
      'feedback_type_code',
      'rating_score',
      'status_code',
      'remark'
  )
ORDER BY ordinal_position;

SELECT COUNT(*) AS row_count FROM `te_health_companion`.`fb_feedback`;

/* PATCH 004 END */

/* =============================================================
PATCH 005 START
Database : te_story_platform
Table    : sp_attribute
Columns  : 8
Rows     : 0
Backup   : sp_attribute_backup_20260720_01
============================================================= */

-- 1. 변경 전 백업
CREATE TABLE `te_story_platform`.`sp_attribute_backup_20260720_01`
LIKE `te_story_platform`.`sp_attribute`;

START TRANSACTION;

INSERT INTO `te_story_platform`.`sp_attribute_backup_20260720_01`
SELECT *
FROM `te_story_platform`.`sp_attribute`;

COMMIT;

-- 2. 백업 검증
SELECT
    (SELECT COUNT(*) FROM `te_story_platform`.`sp_attribute`) AS original_count,
    (SELECT COUNT(*) FROM `te_story_platform`.`sp_attribute_backup_20260720_01`) AS backup_count;

-- 3. ALTER TABLE 문 실행
ALTER TABLE `te_story_platform`.`sp_attribute`
    MODIFY COLUMN `attribute_id` VARCHAR(99) NOT NULL COMMENT 'Attribute ID. SPS Repository에서 Attribute Knowledge를 고유하게 식별하기 위해 사용한다.',
    MODIFY COLUMN `entity_id` VARCHAR(99) NOT NULL COMMENT 'Entity ID. Attribute가 어느 Entity에 속하는지 연결하기 위해 사용한다. 참조: te_story_platform.sp_entity.entity_id',
    MODIFY COLUMN `attribute_name` VARCHAR(150) NOT NULL COMMENT 'Attribute Name. Attribute Knowledge를 사람이 이해할 수 있는 이름으로 표현하기 위해 사용한다.',
    MODIFY COLUMN `created_by` VARCHAR(99) NOT NULL DEFAULT '''SYSTEM''' COMMENT 'Created By. Attribute를 최초 생성한 주체를 추적하기 위해 사용한다.',
    MODIFY COLUMN `updated_by` VARCHAR(99) NULL DEFAULT NULL COMMENT 'Updated By. Attribute를 마지막으로 수정한 주체를 추적하기 위해 사용한다.',
    MODIFY COLUMN `deleted_by` VARCHAR(99) NULL DEFAULT NULL COMMENT 'Deleted By. Attribute를 삭제 처리한 주체를 추적하기 위해 사용한다.',
    MODIFY COLUMN `client_ip` VARCHAR(99) NULL DEFAULT NULL COMMENT 'Client IP. Attribute 변경 요청이 발생한 클라이언트 IP를 추적하기 위해 사용한다.',
    MODIFY COLUMN `program_id` VARCHAR(99) NULL DEFAULT NULL COMMENT 'Program ID. Attribute 변경을 수행한 프로그램 또는 Generator를 추적하기 위해 사용한다.';

-- 4. 변경 결과 확인
SELECT column_name, column_type
FROM information_schema.columns
WHERE table_schema = 'te_story_platform'
  AND table_name = 'sp_attribute'
  AND column_name IN (
      'attribute_id',
      'entity_id',
      'attribute_name',
      'created_by',
      'updated_by',
      'deleted_by',
      'client_ip',
      'program_id'
  )
ORDER BY ordinal_position;

SELECT COUNT(*) AS row_count FROM `te_story_platform`.`sp_attribute`;

/* PATCH 005 END */

/* =============================================================
PATCH 006 START
Database : te_story_platform
Table    : sp_business
Columns  : 7
Rows     : 5
Backup   : sp_business_backup_20260720_01
============================================================= */

-- 1. 변경 전 백업
CREATE TABLE `te_story_platform`.`sp_business_backup_20260720_01`
LIKE `te_story_platform`.`sp_business`;

START TRANSACTION;

INSERT INTO `te_story_platform`.`sp_business_backup_20260720_01`
SELECT *
FROM `te_story_platform`.`sp_business`;

COMMIT;

-- 2. 백업 검증
SELECT
    (SELECT COUNT(*) FROM `te_story_platform`.`sp_business`) AS original_count,
    (SELECT COUNT(*) FROM `te_story_platform`.`sp_business_backup_20260720_01`) AS backup_count;

-- 3. ALTER TABLE 문 실행
ALTER TABLE `te_story_platform`.`sp_business`
    MODIFY COLUMN `business_code` VARCHAR(99) NOT NULL COMMENT 'Business Code',
    MODIFY COLUMN `business_name` VARCHAR(150) NOT NULL COMMENT 'Business Name',
    MODIFY COLUMN `created_by` VARCHAR(99) NOT NULL DEFAULT '''SYSTEM''' COMMENT 'Created By',
    MODIFY COLUMN `updated_by` VARCHAR(99) NULL DEFAULT NULL COMMENT 'Updated By',
    MODIFY COLUMN `deleted_by` VARCHAR(99) NULL DEFAULT NULL COMMENT 'Deleted By',
    MODIFY COLUMN `client_ip` VARCHAR(99) NULL DEFAULT NULL COMMENT 'Client IP',
    MODIFY COLUMN `program_id` VARCHAR(99) NULL DEFAULT NULL COMMENT 'Program ID';

-- 4. 변경 결과 확인
SELECT column_name, column_type
FROM information_schema.columns
WHERE table_schema = 'te_story_platform'
  AND table_name = 'sp_business'
  AND column_name IN (
      'business_code',
      'business_name',
      'created_by',
      'updated_by',
      'deleted_by',
      'client_ip',
      'program_id'
  )
ORDER BY ordinal_position;

SELECT COUNT(*) AS row_count FROM `te_story_platform`.`sp_business`;

/* PATCH 006 END */

/* =============================================================
PATCH 007 START
Database : te_story_platform
Table    : sp_domain
Columns  : 8
Rows     : 6
Backup   : sp_domain_backup_20260720_01
============================================================= */

-- 1. 변경 전 백업
CREATE TABLE `te_story_platform`.`sp_domain_backup_20260720_01`
LIKE `te_story_platform`.`sp_domain`;

START TRANSACTION;

INSERT INTO `te_story_platform`.`sp_domain_backup_20260720_01`
SELECT *
FROM `te_story_platform`.`sp_domain`;

COMMIT;

-- 2. 백업 검증
SELECT
    (SELECT COUNT(*) FROM `te_story_platform`.`sp_domain`) AS original_count,
    (SELECT COUNT(*) FROM `te_story_platform`.`sp_domain_backup_20260720_01`) AS backup_count;

-- 3. ALTER TABLE 문 실행
ALTER TABLE `te_story_platform`.`sp_domain`
    MODIFY COLUMN `domain_code` VARCHAR(99) NOT NULL COMMENT 'Domain Code',
    MODIFY COLUMN `business_code` VARCHAR(99) NOT NULL COMMENT 'Business Code',
    MODIFY COLUMN `domain_name` VARCHAR(150) NOT NULL COMMENT 'Domain Name',
    MODIFY COLUMN `created_by` VARCHAR(99) NOT NULL DEFAULT '''SYSTEM''' COMMENT 'Created By',
    MODIFY COLUMN `updated_by` VARCHAR(99) NULL DEFAULT NULL COMMENT 'Updated By. 마지막 수정 주체.',
    MODIFY COLUMN `deleted_by` VARCHAR(99) NULL DEFAULT NULL COMMENT 'Deleted By. 논리 삭제 처리 주체.',
    MODIFY COLUMN `program_id` VARCHAR(99) NULL DEFAULT NULL COMMENT 'Program Identifier. 변경 수행 프로그램.',
    MODIFY COLUMN `client_ip` VARCHAR(99) NULL DEFAULT NULL COMMENT 'Client IP. IPv4 또는 IPv6 주소.';

-- 4. 변경 결과 확인
SELECT column_name, column_type
FROM information_schema.columns
WHERE table_schema = 'te_story_platform'
  AND table_name = 'sp_domain'
  AND column_name IN (
      'domain_code',
      'business_code',
      'domain_name',
      'created_by',
      'updated_by',
      'deleted_by',
      'program_id',
      'client_ip'
  )
ORDER BY ordinal_position;

SELECT COUNT(*) AS row_count FROM `te_story_platform`.`sp_domain`;

/* PATCH 007 END */

/* =============================================================
PATCH 008 START
Database : te_story_platform
Table    : sp_entity
Columns  : 10
Rows     : 0
Backup   : sp_entity_backup_20260720_01
============================================================= */

-- 1. 변경 전 백업
CREATE TABLE `te_story_platform`.`sp_entity_backup_20260720_01`
LIKE `te_story_platform`.`sp_entity`;

START TRANSACTION;

INSERT INTO `te_story_platform`.`sp_entity_backup_20260720_01`
SELECT *
FROM `te_story_platform`.`sp_entity`;

COMMIT;

-- 2. 백업 검증
SELECT
    (SELECT COUNT(*) FROM `te_story_platform`.`sp_entity`) AS original_count,
    (SELECT COUNT(*) FROM `te_story_platform`.`sp_entity_backup_20260720_01`) AS backup_count;

-- 3. ALTER TABLE 문 실행
ALTER TABLE `te_story_platform`.`sp_entity`
    MODIFY COLUMN `entity_id` VARCHAR(99) NOT NULL COMMENT 'Entity ID. SPS Repository에서 Entity Knowledge를 고유하게 식별하기 위해 사용한다.',
    MODIFY COLUMN `entity_name` VARCHAR(150) NOT NULL COMMENT 'Entity Name. Entity Knowledge를 사람이 이해할 수 있는 이름으로 표현하기 위해 사용한다.',
    MODIFY COLUMN `business_code` VARCHAR(99) NOT NULL COMMENT 'Business Code. Entity가 어느 Business에 속하는지 식별하기 위해 사용한다. 참조: te_story_platform.sp_business.business_code',
    MODIFY COLUMN `domain_code` VARCHAR(99) NOT NULL COMMENT 'Entity가 어느 SPS Domain 공통코드에 속하는지 식별하기 위해 사용한다. (te_common.cm_common_code, group_code=SPS_DOMAIN)',
    MODIFY COLUMN `entity_type_code` VARCHAR(99) NOT NULL DEFAULT '''MASTER''' COMMENT 'Entity Type Code. Entity의 성격을 구분하고 Engine과 Generator의 처리 방식을 결정하기 위해 사용한다.',
    MODIFY COLUMN `created_by` VARCHAR(99) NOT NULL DEFAULT '''SYSTEM''' COMMENT 'Created By. Entity를 최초 생성한 주체를 추적하기 위해 사용한다.',
    MODIFY COLUMN `updated_by` VARCHAR(99) NULL DEFAULT NULL COMMENT 'Updated By. Entity를 마지막으로 수정한 주체를 추적하기 위해 사용한다.',
    MODIFY COLUMN `deleted_by` VARCHAR(99) NULL DEFAULT NULL COMMENT 'Deleted By. Entity를 삭제 처리한 주체를 추적하기 위해 사용한다.',
    MODIFY COLUMN `client_ip` VARCHAR(99) NULL DEFAULT NULL COMMENT 'Client IP. Entity 변경 요청이 발생한 클라이언트 IP를 추적하기 위해 사용한다.',
    MODIFY COLUMN `program_id` VARCHAR(99) NULL DEFAULT NULL COMMENT 'Program ID. Entity 변경을 수행한 프로그램 또는 Generator를 추적하기 위해 사용한다.';

-- 4. 변경 결과 확인
SELECT column_name, column_type
FROM information_schema.columns
WHERE table_schema = 'te_story_platform'
  AND table_name = 'sp_entity'
  AND column_name IN (
      'entity_id',
      'entity_name',
      'business_code',
      'domain_code',
      'entity_type_code',
      'created_by',
      'updated_by',
      'deleted_by',
      'client_ip',
      'program_id'
  )
ORDER BY ordinal_position;

SELECT COUNT(*) AS row_count FROM `te_story_platform`.`sp_entity`;

/* PATCH 008 END */

/* =============================================================
PATCH 009 START
Database : te_story_platform
Table    : sp_erd
Columns  : 9
Rows     : 0
Backup   : sp_erd_backup_20260720_01
============================================================= */

-- 1. 변경 전 백업
CREATE TABLE `te_story_platform`.`sp_erd_backup_20260720_01`
LIKE `te_story_platform`.`sp_erd`;

START TRANSACTION;

INSERT INTO `te_story_platform`.`sp_erd_backup_20260720_01`
SELECT *
FROM `te_story_platform`.`sp_erd`;

COMMIT;

-- 2. 백업 검증
SELECT
    (SELECT COUNT(*) FROM `te_story_platform`.`sp_erd`) AS original_count,
    (SELECT COUNT(*) FROM `te_story_platform`.`sp_erd_backup_20260720_01`) AS backup_count;

-- 3. ALTER TABLE 문 실행
ALTER TABLE `te_story_platform`.`sp_erd`
    MODIFY COLUMN `erd_id` VARCHAR(99) NOT NULL COMMENT 'ERD ID',
    MODIFY COLUMN `erd_code` VARCHAR(99) NOT NULL COMMENT 'ERD Code',
    MODIFY COLUMN `business_code` VARCHAR(99) NOT NULL COMMENT 'Business Code',
    MODIFY COLUMN `domain_code` VARCHAR(99) NOT NULL COMMENT 'Domain Code',
    MODIFY COLUMN `created_by` VARCHAR(99) NOT NULL DEFAULT '''SYSTEM''' COMMENT 'Created By',
    MODIFY COLUMN `updated_by` VARCHAR(99) NULL DEFAULT NULL COMMENT 'Updated By',
    MODIFY COLUMN `deleted_by` VARCHAR(99) NULL DEFAULT NULL COMMENT 'Deleted By',
    MODIFY COLUMN `client_ip` VARCHAR(99) NULL DEFAULT NULL COMMENT 'Client IP',
    MODIFY COLUMN `program_id` VARCHAR(99) NULL DEFAULT NULL COMMENT 'Program ID';

-- 4. 변경 결과 확인
SELECT column_name, column_type
FROM information_schema.columns
WHERE table_schema = 'te_story_platform'
  AND table_name = 'sp_erd'
  AND column_name IN (
      'erd_id',
      'erd_code',
      'business_code',
      'domain_code',
      'created_by',
      'updated_by',
      'deleted_by',
      'client_ip',
      'program_id'
  )
ORDER BY ordinal_position;

SELECT COUNT(*) AS row_count FROM `te_story_platform`.`sp_erd`;

/* PATCH 009 END */

/* =============================================================
PATCH 010 START
Database : te_story_platform
Table    : sp_execution_history
Columns  : 9
Rows     : 12
Backup   : sp_execution_history_backup_20260720_01
============================================================= */

-- 1. 변경 전 백업
CREATE TABLE `te_story_platform`.`sp_execution_history_backup_20260720_01`
LIKE `te_story_platform`.`sp_execution_history`;

START TRANSACTION;

INSERT INTO `te_story_platform`.`sp_execution_history_backup_20260720_01`
SELECT *
FROM `te_story_platform`.`sp_execution_history`;

COMMIT;

-- 2. 백업 검증
SELECT
    (SELECT COUNT(*) FROM `te_story_platform`.`sp_execution_history`) AS original_count,
    (SELECT COUNT(*) FROM `te_story_platform`.`sp_execution_history_backup_20260720_01`) AS backup_count;

-- 3. ALTER TABLE 문 실행
ALTER TABLE `te_story_platform`.`sp_execution_history`
    MODIFY COLUMN `trace_id` VARCHAR(99) NOT NULL,
    MODIFY COLUMN `engine_code` VARCHAR(99) NOT NULL,
    MODIFY COLUMN `object_code` VARCHAR(99) NOT NULL,
    MODIFY COLUMN `object_id` VARCHAR(99) NULL DEFAULT NULL,
    MODIFY COLUMN `created_by` VARCHAR(99) NOT NULL DEFAULT '''SYSTEM''' COMMENT 'Created By. 실행 이력 생성 주체.',
    MODIFY COLUMN `updated_by` VARCHAR(99) NULL DEFAULT NULL COMMENT 'Updated By. 실행 이력 수정 주체.',
    MODIFY COLUMN `deleted_by` VARCHAR(99) NULL DEFAULT NULL COMMENT 'Deleted By. 논리 삭제 처리 주체.',
    MODIFY COLUMN `program_id` VARCHAR(99) NULL DEFAULT NULL COMMENT 'Program Identifier. 실행 프로그램 또는 Generator.',
    MODIFY COLUMN `client_ip` VARCHAR(99) NULL DEFAULT NULL COMMENT 'Client IP. IPv4 또는 IPv6 주소.';

-- 4. 변경 결과 확인
SELECT column_name, column_type
FROM information_schema.columns
WHERE table_schema = 'te_story_platform'
  AND table_name = 'sp_execution_history'
  AND column_name IN (
      'trace_id',
      'engine_code',
      'object_code',
      'object_id',
      'created_by',
      'updated_by',
      'deleted_by',
      'program_id',
      'client_ip'
  )
ORDER BY ordinal_position;

SELECT COUNT(*) AS row_count FROM `te_story_platform`.`sp_execution_history`;

/* PATCH 010 END */

/* =============================================================
PATCH 011 START
Database : te_story_platform
Table    : sp_identifier_blueprint
Columns  : 4
Rows     : 5
Backup   : sp_identifier_blueprint_backup_20260720_01
============================================================= */

-- 1. 변경 전 백업
CREATE TABLE `te_story_platform`.`sp_identifier_blueprint_backup_20260720_01`
LIKE `te_story_platform`.`sp_identifier_blueprint`;

START TRANSACTION;

INSERT INTO `te_story_platform`.`sp_identifier_blueprint_backup_20260720_01`
SELECT *
FROM `te_story_platform`.`sp_identifier_blueprint`;

COMMIT;

-- 2. 백업 검증
SELECT
    (SELECT COUNT(*) FROM `te_story_platform`.`sp_identifier_blueprint`) AS original_count,
    (SELECT COUNT(*) FROM `te_story_platform`.`sp_identifier_blueprint_backup_20260720_01`) AS backup_count;

-- 3. ALTER TABLE 문 실행
ALTER TABLE `te_story_platform`.`sp_identifier_blueprint`
    MODIFY COLUMN `created_by` VARCHAR(99) NOT NULL DEFAULT '''SYSTEM''' COMMENT 'Created By',
    MODIFY COLUMN `updated_by` VARCHAR(99) NOT NULL DEFAULT '''SYSTEM''' COMMENT 'Updated By',
    MODIFY COLUMN `deleted_by` VARCHAR(99) NULL DEFAULT NULL COMMENT 'Deleted By',
    MODIFY COLUMN `program_id` VARCHAR(99) NULL DEFAULT NULL COMMENT 'Program ID';

-- 4. 변경 결과 확인
SELECT column_name, column_type
FROM information_schema.columns
WHERE table_schema = 'te_story_platform'
  AND table_name = 'sp_identifier_blueprint'
  AND column_name IN (
      'created_by',
      'updated_by',
      'deleted_by',
      'program_id'
  )
ORDER BY ordinal_position;

SELECT COUNT(*) AS row_count FROM `te_story_platform`.`sp_identifier_blueprint`;

/* PATCH 011 END */

/* =============================================================
PATCH 012 START
Database : te_story_platform
Table    : sp_identifier_sequence
Columns  : 9
Rows     : 20
Backup   : sp_identifier_sequence_backup_20260720_01
============================================================= */

-- 1. 변경 전 백업
CREATE TABLE `te_story_platform`.`sp_identifier_sequence_backup_20260720_01`
LIKE `te_story_platform`.`sp_identifier_sequence`;

START TRANSACTION;

INSERT INTO `te_story_platform`.`sp_identifier_sequence_backup_20260720_01`
SELECT *
FROM `te_story_platform`.`sp_identifier_sequence`;

COMMIT;

-- 2. 백업 검증
SELECT
    (SELECT COUNT(*) FROM `te_story_platform`.`sp_identifier_sequence`) AS original_count,
    (SELECT COUNT(*) FROM `te_story_platform`.`sp_identifier_sequence_backup_20260720_01`) AS backup_count;

-- 3. ALTER TABLE 문 실행
ALTER TABLE `te_story_platform`.`sp_identifier_sequence`
    MODIFY COLUMN `identifier_sequence_id` VARCHAR(99) NOT NULL COMMENT 'Identifier Sequence ID. 채번 기준 자체를 식별하는 Repository ID.',
    MODIFY COLUMN `identifier_target_code` VARCHAR(99) NOT NULL COMMENT '채번 대상 코드. 예: BUSINESS, DOMAIN, OBJECT, ENTITY, ATTRIBUTE, RELATIONSHIP, METADATA, SQL, DOCUMENT, API, GENERATOR, ENGINE.',
    MODIFY COLUMN `sequence_date` DATETIME NOT NULL COMMENT '채번 기준 일자. YYYYMMDD.',
    MODIFY COLUMN `status_code` VARCHAR(99) NOT NULL DEFAULT '''ACTIVE''' COMMENT '상태 코드. ACTIVE/INACTIVE.',
    MODIFY COLUMN `created_by` VARCHAR(99) NOT NULL DEFAULT '''SYSTEM''' COMMENT '생성자.',
    MODIFY COLUMN `updated_by` VARCHAR(99) NOT NULL DEFAULT '''SYSTEM''' COMMENT '수정자.',
    MODIFY COLUMN `deleted_by` VARCHAR(99) NULL DEFAULT NULL COMMENT '삭제자.',
    MODIFY COLUMN `client_ip` VARCHAR(99) NULL DEFAULT NULL COMMENT '요청 클라이언트 IP.',
    MODIFY COLUMN `program_id` VARCHAR(99) NULL DEFAULT NULL COMMENT '요청 프로그램 ID.';

-- 4. 변경 결과 확인
SELECT column_name, column_type
FROM information_schema.columns
WHERE table_schema = 'te_story_platform'
  AND table_name = 'sp_identifier_sequence'
  AND column_name IN (
      'identifier_sequence_id',
      'identifier_target_code',
      'sequence_date',
      'status_code',
      'created_by',
      'updated_by',
      'deleted_by',
      'client_ip',
      'program_id'
  )
ORDER BY ordinal_position;

SELECT COUNT(*) AS row_count FROM `te_story_platform`.`sp_identifier_sequence`;

/* PATCH 012 END */

/* =============================================================
PATCH 013 START
Database : te_story_platform
Table    : sp_impact_analysis_result
Columns  : 10
Rows     : 5
Backup   : sp_impact_analysis_result_backup_20260720_01
============================================================= */

-- 1. 변경 전 백업
CREATE TABLE `te_story_platform`.`sp_impact_analysis_result_backup_20260720_01`
LIKE `te_story_platform`.`sp_impact_analysis_result`;

START TRANSACTION;

INSERT INTO `te_story_platform`.`sp_impact_analysis_result_backup_20260720_01`
SELECT *
FROM `te_story_platform`.`sp_impact_analysis_result`;

COMMIT;

-- 2. 백업 검증
SELECT
    (SELECT COUNT(*) FROM `te_story_platform`.`sp_impact_analysis_result`) AS original_count,
    (SELECT COUNT(*) FROM `te_story_platform`.`sp_impact_analysis_result_backup_20260720_01`) AS backup_count;

-- 3. ALTER TABLE 문 실행
ALTER TABLE `te_story_platform`.`sp_impact_analysis_result`
    MODIFY COLUMN `impact_analysis_id` VARCHAR(99) NOT NULL,
    MODIFY COLUMN `change_type_code` VARCHAR(99) NOT NULL,
    MODIFY COLUMN `affected_object_type_code` VARCHAR(99) NOT NULL,
    MODIFY COLUMN `affected_object_name` VARCHAR(150) NOT NULL,
    MODIFY COLUMN `risk_level_code` VARCHAR(99) NOT NULL DEFAULT '''MEDIUM''',
    MODIFY COLUMN `created_by` VARCHAR(99) NOT NULL DEFAULT '''SYSTEM''',
    MODIFY COLUMN `updated_by` VARCHAR(99) NULL DEFAULT NULL,
    MODIFY COLUMN `deleted_by` VARCHAR(99) NULL DEFAULT NULL,
    MODIFY COLUMN `client_ip` VARCHAR(99) NULL DEFAULT NULL,
    MODIFY COLUMN `program_id` VARCHAR(99) NULL DEFAULT NULL;

-- 4. 변경 결과 확인
SELECT column_name, column_type
FROM information_schema.columns
WHERE table_schema = 'te_story_platform'
  AND table_name = 'sp_impact_analysis_result'
  AND column_name IN (
      'impact_analysis_id',
      'change_type_code',
      'affected_object_type_code',
      'affected_object_name',
      'risk_level_code',
      'created_by',
      'updated_by',
      'deleted_by',
      'client_ip',
      'program_id'
  )
ORDER BY ordinal_position;

SELECT COUNT(*) AS row_count FROM `te_story_platform`.`sp_impact_analysis_result`;

/* PATCH 013 END */

/* =============================================================
PATCH 014 START
Database : te_story_platform
Table    : sp_knowledge_hold
Columns  : 9
Rows     : 79
Backup   : sp_knowledge_hold_backup_20260720_01
============================================================= */

-- 1. 변경 전 백업
CREATE TABLE `te_story_platform`.`sp_knowledge_hold_backup_20260720_01`
LIKE `te_story_platform`.`sp_knowledge_hold`;

START TRANSACTION;

INSERT INTO `te_story_platform`.`sp_knowledge_hold_backup_20260720_01`
SELECT *
FROM `te_story_platform`.`sp_knowledge_hold`;

COMMIT;

-- 2. 백업 검증
SELECT
    (SELECT COUNT(*) FROM `te_story_platform`.`sp_knowledge_hold`) AS original_count,
    (SELECT COUNT(*) FROM `te_story_platform`.`sp_knowledge_hold_backup_20260720_01`) AS backup_count;

-- 3. ALTER TABLE 문 실행
ALTER TABLE `te_story_platform`.`sp_knowledge_hold`
    MODIFY COLUMN `knowledge_identifier` VARCHAR(99) NOT NULL,
    MODIFY COLUMN `knowledge_type_id` VARCHAR(99) NOT NULL,
    MODIFY COLUMN `knowledge_name` VARCHAR(150) NOT NULL,
    MODIFY COLUMN `knowledge_description` VARCHAR(2000) NULL DEFAULT NULL,
    MODIFY COLUMN `created_by` VARCHAR(99) NOT NULL DEFAULT '''SYSTEM''',
    MODIFY COLUMN `updated_by` VARCHAR(99) NULL DEFAULT NULL,
    MODIFY COLUMN `deleted_by` VARCHAR(99) NULL DEFAULT NULL,
    MODIFY COLUMN `client_ip` VARCHAR(99) NULL DEFAULT NULL,
    MODIFY COLUMN `program_id` VARCHAR(99) NULL DEFAULT NULL;

-- 4. 변경 결과 확인
SELECT column_name, column_type
FROM information_schema.columns
WHERE table_schema = 'te_story_platform'
  AND table_name = 'sp_knowledge_hold'
  AND column_name IN (
      'knowledge_identifier',
      'knowledge_type_id',
      'knowledge_name',
      'knowledge_description',
      'created_by',
      'updated_by',
      'deleted_by',
      'client_ip',
      'program_id'
  )
ORDER BY ordinal_position;

SELECT COUNT(*) AS row_count FROM `te_story_platform`.`sp_knowledge_hold`;

/* PATCH 014 END */

/* =============================================================
PATCH 015 START
Database : te_story_platform
Table    : sp_knowledge_relationship_hold
Columns  : 9
Rows     : 53
Backup   : sp_knowledge_relationship_hold_backup_20260720_01
============================================================= */

-- 1. 변경 전 백업
CREATE TABLE `te_story_platform`.`sp_knowledge_relationship_hold_backup_20260720_01`
LIKE `te_story_platform`.`sp_knowledge_relationship_hold`;

START TRANSACTION;

INSERT INTO `te_story_platform`.`sp_knowledge_relationship_hold_backup_20260720_01`
SELECT *
FROM `te_story_platform`.`sp_knowledge_relationship_hold`;

COMMIT;

-- 2. 백업 검증
SELECT
    (SELECT COUNT(*) FROM `te_story_platform`.`sp_knowledge_relationship_hold`) AS original_count,
    (SELECT COUNT(*) FROM `te_story_platform`.`sp_knowledge_relationship_hold_backup_20260720_01`) AS backup_count;

-- 3. ALTER TABLE 문 실행
ALTER TABLE `te_story_platform`.`sp_knowledge_relationship_hold`
    MODIFY COLUMN `source_knowledge_id` VARCHAR(99) NOT NULL,
    MODIFY COLUMN `target_knowledge_id` VARCHAR(99) NOT NULL,
    MODIFY COLUMN `relationship_type_code` VARCHAR(99) NOT NULL,
    MODIFY COLUMN `relationship_description` VARCHAR(2000) NULL DEFAULT NULL,
    MODIFY COLUMN `created_by` VARCHAR(99) NOT NULL DEFAULT '''SYSTEM''',
    MODIFY COLUMN `updated_by` VARCHAR(99) NULL DEFAULT NULL,
    MODIFY COLUMN `deleted_by` VARCHAR(99) NULL DEFAULT NULL,
    MODIFY COLUMN `client_ip` VARCHAR(99) NULL DEFAULT NULL,
    MODIFY COLUMN `program_id` VARCHAR(99) NULL DEFAULT NULL;

-- 4. 변경 결과 확인
SELECT column_name, column_type
FROM information_schema.columns
WHERE table_schema = 'te_story_platform'
  AND table_name = 'sp_knowledge_relationship_hold'
  AND column_name IN (
      'source_knowledge_id',
      'target_knowledge_id',
      'relationship_type_code',
      'relationship_description',
      'created_by',
      'updated_by',
      'deleted_by',
      'client_ip',
      'program_id'
  )
ORDER BY ordinal_position;

SELECT COUNT(*) AS row_count FROM `te_story_platform`.`sp_knowledge_relationship_hold`;

/* PATCH 015 END */

/* =============================================================
PATCH 016 START
Database : te_story_platform
Table    : sp_knowledge_type_hold
Columns  : 9
Rows     : 15
Backup   : sp_knowledge_type_hold_backup_20260720_01
============================================================= */

-- 1. 변경 전 백업
CREATE TABLE `te_story_platform`.`sp_knowledge_type_hold_backup_20260720_01`
LIKE `te_story_platform`.`sp_knowledge_type_hold`;

START TRANSACTION;

INSERT INTO `te_story_platform`.`sp_knowledge_type_hold_backup_20260720_01`
SELECT *
FROM `te_story_platform`.`sp_knowledge_type_hold`;

COMMIT;

-- 2. 백업 검증
SELECT
    (SELECT COUNT(*) FROM `te_story_platform`.`sp_knowledge_type_hold`) AS original_count,
    (SELECT COUNT(*) FROM `te_story_platform`.`sp_knowledge_type_hold_backup_20260720_01`) AS backup_count;

-- 3. ALTER TABLE 문 실행
ALTER TABLE `te_story_platform`.`sp_knowledge_type_hold`
    MODIFY COLUMN `knowledge_type_code` VARCHAR(99) NOT NULL,
    MODIFY COLUMN `knowledge_type_name` VARCHAR(150) NOT NULL,
    MODIFY COLUMN `parent_knowledge_type_id` VARCHAR(99) NULL DEFAULT NULL,
    MODIFY COLUMN `knowledge_type_description` VARCHAR(2000) NULL DEFAULT NULL,
    MODIFY COLUMN `created_by` VARCHAR(99) NOT NULL DEFAULT '''SYSTEM''',
    MODIFY COLUMN `updated_by` VARCHAR(99) NULL DEFAULT NULL,
    MODIFY COLUMN `deleted_by` VARCHAR(99) NULL DEFAULT NULL,
    MODIFY COLUMN `client_ip` VARCHAR(99) NULL DEFAULT NULL,
    MODIFY COLUMN `program_id` VARCHAR(99) NULL DEFAULT NULL;

-- 4. 변경 결과 확인
SELECT column_name, column_type
FROM information_schema.columns
WHERE table_schema = 'te_story_platform'
  AND table_name = 'sp_knowledge_type_hold'
  AND column_name IN (
      'knowledge_type_code',
      'knowledge_type_name',
      'parent_knowledge_type_id',
      'knowledge_type_description',
      'created_by',
      'updated_by',
      'deleted_by',
      'client_ip',
      'program_id'
  )
ORDER BY ordinal_position;

SELECT COUNT(*) AS row_count FROM `te_story_platform`.`sp_knowledge_type_hold`;

/* PATCH 016 END */

/* =============================================================
PATCH 017 START
Database : te_story_platform
Table    : sp_metadata
Columns  : 5
Rows     : 123
Backup   : sp_metadata_backup_20260720_01
============================================================= */

-- 1. 변경 전 백업
CREATE TABLE `te_story_platform`.`sp_metadata_backup_20260720_01`
LIKE `te_story_platform`.`sp_metadata`;

START TRANSACTION;

INSERT INTO `te_story_platform`.`sp_metadata_backup_20260720_01`
SELECT *
FROM `te_story_platform`.`sp_metadata`;

COMMIT;

-- 2. 백업 검증
SELECT
    (SELECT COUNT(*) FROM `te_story_platform`.`sp_metadata`) AS original_count,
    (SELECT COUNT(*) FROM `te_story_platform`.`sp_metadata_backup_20260720_01`) AS backup_count;

-- 3. ALTER TABLE 문 실행
ALTER TABLE `te_story_platform`.`sp_metadata`
    MODIFY COLUMN `created_by` VARCHAR(99) NOT NULL DEFAULT '''SYSTEM''' COMMENT 'Created By. Metadata를 최초 생성한 주체.',
    MODIFY COLUMN `updated_by` VARCHAR(99) NULL DEFAULT NULL COMMENT 'Updated By. Metadata를 마지막으로 수정한 주체.',
    MODIFY COLUMN `deleted_by` VARCHAR(99) NULL DEFAULT NULL COMMENT 'Deleted By. Metadata를 삭제 처리한 주체.',
    MODIFY COLUMN `client_ip` VARCHAR(99) NULL DEFAULT NULL COMMENT 'Client IP. Metadata 변경 요청이 발생한 클라이언트 IP.',
    MODIFY COLUMN `program_id` VARCHAR(99) NULL DEFAULT NULL COMMENT 'Program ID. Metadata 등록 또는 변경을 수행한 Runtime, Engine, Generator 식별자.';

-- 4. 변경 결과 확인
SELECT column_name, column_type
FROM information_schema.columns
WHERE table_schema = 'te_story_platform'
  AND table_name = 'sp_metadata'
  AND column_name IN (
      'created_by',
      'updated_by',
      'deleted_by',
      'client_ip',
      'program_id'
  )
ORDER BY ordinal_position;

SELECT COUNT(*) AS row_count FROM `te_story_platform`.`sp_metadata`;

/* PATCH 017 END */

/* =============================================================
PATCH 018 START
Database : te_story_platform
Table    : sp_object
Columns  : 6
Rows     : 9
Backup   : sp_object_backup_20260720_01
============================================================= */

-- 1. 변경 전 백업
CREATE TABLE `te_story_platform`.`sp_object_backup_20260720_01`
LIKE `te_story_platform`.`sp_object`;

START TRANSACTION;

INSERT INTO `te_story_platform`.`sp_object_backup_20260720_01`
SELECT *
FROM `te_story_platform`.`sp_object`;

COMMIT;

-- 2. 백업 검증
SELECT
    (SELECT COUNT(*) FROM `te_story_platform`.`sp_object`) AS original_count,
    (SELECT COUNT(*) FROM `te_story_platform`.`sp_object_backup_20260720_01`) AS backup_count;

-- 3. ALTER TABLE 문 실행
ALTER TABLE `te_story_platform`.`sp_object`
    MODIFY COLUMN `object_description` VARCHAR(2000) NULL DEFAULT NULL COMMENT 'Object Description. Knowledge Object의 목적, 의미, 범위를 설명하기 위해 사용한다.',
    MODIFY COLUMN `created_by` VARCHAR(99) NOT NULL DEFAULT '''SYSTEM''' COMMENT 'Created By. Object를 최초 생성한 주체를 추적하기 위해 사용한다.',
    MODIFY COLUMN `updated_by` VARCHAR(99) NULL DEFAULT NULL COMMENT 'Updated By. Object를 마지막으로 수정한 주체를 추적하기 위해 사용한다.',
    MODIFY COLUMN `deleted_by` VARCHAR(99) NULL DEFAULT NULL COMMENT 'Deleted By. Object를 삭제 처리한 주체를 추적하기 위해 사용한다.',
    MODIFY COLUMN `client_ip` VARCHAR(99) NULL DEFAULT NULL COMMENT 'Client IP. Object 변경 요청이 발생한 클라이언트 IP를 추적하기 위해 사용한다.',
    MODIFY COLUMN `program_id` VARCHAR(99) NULL DEFAULT NULL COMMENT 'Program ID. Object 변경을 수행한 프로그램 또는 Generator를 추적하기 위해 사용한다.';

-- 4. 변경 결과 확인
SELECT column_name, column_type
FROM information_schema.columns
WHERE table_schema = 'te_story_platform'
  AND table_name = 'sp_object'
  AND column_name IN (
      'object_description',
      'created_by',
      'updated_by',
      'deleted_by',
      'client_ip',
      'program_id'
  )
ORDER BY ordinal_position;

SELECT COUNT(*) AS row_count FROM `te_story_platform`.`sp_object`;

/* PATCH 018 END */

/* =============================================================
PATCH 019 START
Database : te_story_platform
Table    : sp_object_execution_link
Columns  : 5
Rows     : 0
Backup   : sp_object_execution_link_backup_20260720_01
============================================================= */

-- 1. 변경 전 백업
CREATE TABLE `te_story_platform`.`sp_object_execution_link_backup_20260720_01`
LIKE `te_story_platform`.`sp_object_execution_link`;

START TRANSACTION;

INSERT INTO `te_story_platform`.`sp_object_execution_link_backup_20260720_01`
SELECT *
FROM `te_story_platform`.`sp_object_execution_link`;

COMMIT;

-- 2. 백업 검증
SELECT
    (SELECT COUNT(*) FROM `te_story_platform`.`sp_object_execution_link`) AS original_count,
    (SELECT COUNT(*) FROM `te_story_platform`.`sp_object_execution_link_backup_20260720_01`) AS backup_count;

-- 3. ALTER TABLE 문 실행
ALTER TABLE `te_story_platform`.`sp_object_execution_link`
    MODIFY COLUMN `created_by` VARCHAR(99) NOT NULL DEFAULT '''SYSTEM''' COMMENT 'Created By. 생성자. 모든 _by 계열 컬럼은 VARCHAR(150)를 표준으로 한다.',
    MODIFY COLUMN `updated_by` VARCHAR(99) NULL DEFAULT NULL COMMENT 'Updated By. 수정자. 모든 _by 계열 컬럼은 VARCHAR(150)를 표준으로 한다.',
    MODIFY COLUMN `deleted_by` VARCHAR(99) NULL DEFAULT NULL COMMENT 'Deleted By. 삭제자. 모든 _by 계열 컬럼은 VARCHAR(150)를 표준으로 한다.',
    MODIFY COLUMN `client_ip` VARCHAR(99) NULL DEFAULT NULL COMMENT 'Client IP. IPv4/IPv6 주소. _ip 계열 컬럼은 VARCHAR(45)를 표준으로 한다.',
    MODIFY COLUMN `program_id` VARCHAR(99) NULL DEFAULT NULL COMMENT 'Program Identifier. 실행 프로그램 또는 모듈 식별자. program_id는 VARCHAR(150)를 표준으로 한다.';

-- 4. 변경 결과 확인
SELECT column_name, column_type
FROM information_schema.columns
WHERE table_schema = 'te_story_platform'
  AND table_name = 'sp_object_execution_link'
  AND column_name IN (
      'created_by',
      'updated_by',
      'deleted_by',
      'client_ip',
      'program_id'
  )
ORDER BY ordinal_position;

SELECT COUNT(*) AS row_count FROM `te_story_platform`.`sp_object_execution_link`;

/* PATCH 019 END */

/* =============================================================
PATCH 020 START
Database : te_story_platform
Table    : sp_object_lifecycle
Columns  : 9
Rows     : 1
Backup   : sp_object_lifecycle_backup_20260720_01
============================================================= */

-- 1. 변경 전 백업
CREATE TABLE `te_story_platform`.`sp_object_lifecycle_backup_20260720_01`
LIKE `te_story_platform`.`sp_object_lifecycle`;

START TRANSACTION;

INSERT INTO `te_story_platform`.`sp_object_lifecycle_backup_20260720_01`
SELECT *
FROM `te_story_platform`.`sp_object_lifecycle`;

COMMIT;

-- 2. 백업 검증
SELECT
    (SELECT COUNT(*) FROM `te_story_platform`.`sp_object_lifecycle`) AS original_count,
    (SELECT COUNT(*) FROM `te_story_platform`.`sp_object_lifecycle_backup_20260720_01`) AS backup_count;

-- 3. ALTER TABLE 문 실행
ALTER TABLE `te_story_platform`.`sp_object_lifecycle`
    MODIFY COLUMN `object_lifecycle_id` VARCHAR(99) NOT NULL,
    MODIFY COLUMN `object_id` VARCHAR(99) NOT NULL,
    MODIFY COLUMN `lifecycle_status_code` VARCHAR(99) NOT NULL,
    MODIFY COLUMN `lifecycle_event_code` VARCHAR(99) NOT NULL,
    MODIFY COLUMN `created_by` VARCHAR(99) NOT NULL DEFAULT '''SYSTEM''',
    MODIFY COLUMN `updated_by` VARCHAR(99) NULL DEFAULT NULL,
    MODIFY COLUMN `deleted_by` VARCHAR(99) NULL DEFAULT NULL,
    MODIFY COLUMN `client_ip` VARCHAR(99) NULL DEFAULT NULL,
    MODIFY COLUMN `program_id` VARCHAR(99) NULL DEFAULT NULL;

-- 4. 변경 결과 확인
SELECT column_name, column_type
FROM information_schema.columns
WHERE table_schema = 'te_story_platform'
  AND table_name = 'sp_object_lifecycle'
  AND column_name IN (
      'object_lifecycle_id',
      'object_id',
      'lifecycle_status_code',
      'lifecycle_event_code',
      'created_by',
      'updated_by',
      'deleted_by',
      'client_ip',
      'program_id'
  )
ORDER BY ordinal_position;

SELECT COUNT(*) AS row_count FROM `te_story_platform`.`sp_object_lifecycle`;

/* PATCH 020 END */

/* =============================================================
PATCH 021 START
Database : te_story_platform
Table    : sp_relationship_attribute
Columns  : 9
Rows     : 0
Backup   : sp_relationship_attribute_backup_20260720_01
============================================================= */

-- 1. 변경 전 백업
CREATE TABLE `te_story_platform`.`sp_relationship_attribute_backup_20260720_01`
LIKE `te_story_platform`.`sp_relationship_attribute`;

START TRANSACTION;

INSERT INTO `te_story_platform`.`sp_relationship_attribute_backup_20260720_01`
SELECT *
FROM `te_story_platform`.`sp_relationship_attribute`;

COMMIT;

-- 2. 백업 검증
SELECT
    (SELECT COUNT(*) FROM `te_story_platform`.`sp_relationship_attribute`) AS original_count,
    (SELECT COUNT(*) FROM `te_story_platform`.`sp_relationship_attribute_backup_20260720_01`) AS backup_count;

-- 3. ALTER TABLE 문 실행
ALTER TABLE `te_story_platform`.`sp_relationship_attribute`
    MODIFY COLUMN `relationship_attribute_id` VARCHAR(99) NOT NULL COMMENT 'Relationship Attribute ID',
    MODIFY COLUMN `relationship_id` VARCHAR(99) NOT NULL COMMENT 'Relationship Object ID',
    MODIFY COLUMN `source_attribute_id` VARCHAR(99) NOT NULL COMMENT 'Source Attribute ID',
    MODIFY COLUMN `target_attribute_id` VARCHAR(99) NOT NULL COMMENT 'Target Attribute ID',
    MODIFY COLUMN `created_by` VARCHAR(99) NOT NULL DEFAULT '''SYSTEM''' COMMENT 'Created By',
    MODIFY COLUMN `updated_by` VARCHAR(99) NULL DEFAULT NULL COMMENT 'Updated By',
    MODIFY COLUMN `deleted_by` VARCHAR(99) NULL DEFAULT NULL COMMENT 'Deleted By',
    MODIFY COLUMN `client_ip` VARCHAR(99) NULL DEFAULT NULL COMMENT 'Client IP',
    MODIFY COLUMN `program_id` VARCHAR(99) NULL DEFAULT NULL COMMENT 'Program ID';

-- 4. 변경 결과 확인
SELECT column_name, column_type
FROM information_schema.columns
WHERE table_schema = 'te_story_platform'
  AND table_name = 'sp_relationship_attribute'
  AND column_name IN (
      'relationship_attribute_id',
      'relationship_id',
      'source_attribute_id',
      'target_attribute_id',
      'created_by',
      'updated_by',
      'deleted_by',
      'client_ip',
      'program_id'
  )
ORDER BY ordinal_position;

SELECT COUNT(*) AS row_count FROM `te_story_platform`.`sp_relationship_attribute`;

/* PATCH 021 END */

/* =============================================================
PATCH 022 START
Database : te_story_platform
Table    : sp_work_asset
Columns  : 3
Rows     : 0
Backup   : sp_work_asset_backup_20260720_01
============================================================= */

-- 1. 변경 전 백업
CREATE TABLE `te_story_platform`.`sp_work_asset_backup_20260720_01`
LIKE `te_story_platform`.`sp_work_asset`;

START TRANSACTION;

INSERT INTO `te_story_platform`.`sp_work_asset_backup_20260720_01`
SELECT *
FROM `te_story_platform`.`sp_work_asset`;

COMMIT;

-- 2. 백업 검증
SELECT
    (SELECT COUNT(*) FROM `te_story_platform`.`sp_work_asset`) AS original_count,
    (SELECT COUNT(*) FROM `te_story_platform`.`sp_work_asset_backup_20260720_01`) AS backup_count;

-- 3. ALTER TABLE 문 실행
ALTER TABLE `te_story_platform`.`sp_work_asset`
    MODIFY COLUMN `created_by` VARCHAR(99) NOT NULL,
    MODIFY COLUMN `updated_by` VARCHAR(99) NULL DEFAULT NULL,
    MODIFY COLUMN `deleted_by` VARCHAR(99) NULL DEFAULT NULL;

-- 4. 변경 결과 확인
SELECT column_name, column_type
FROM information_schema.columns
WHERE table_schema = 'te_story_platform'
  AND table_name = 'sp_work_asset'
  AND column_name IN (
      'created_by',
      'updated_by',
      'deleted_by'
  )
ORDER BY ordinal_position;

SELECT COUNT(*) AS row_count FROM `te_story_platform`.`sp_work_asset`;

/* PATCH 022 END */

/* =============================================================
PATCH 023 START
Database : te_story_platform
Table    : sp_work_item
Columns  : 3
Rows     : 0
Backup   : sp_work_item_backup_20260720_01
============================================================= */

-- 1. 변경 전 백업
CREATE TABLE `te_story_platform`.`sp_work_item_backup_20260720_01`
LIKE `te_story_platform`.`sp_work_item`;

START TRANSACTION;

INSERT INTO `te_story_platform`.`sp_work_item_backup_20260720_01`
SELECT *
FROM `te_story_platform`.`sp_work_item`;

COMMIT;

-- 2. 백업 검증
SELECT
    (SELECT COUNT(*) FROM `te_story_platform`.`sp_work_item`) AS original_count,
    (SELECT COUNT(*) FROM `te_story_platform`.`sp_work_item_backup_20260720_01`) AS backup_count;

-- 3. ALTER TABLE 문 실행
ALTER TABLE `te_story_platform`.`sp_work_item`
    MODIFY COLUMN `created_by` VARCHAR(99) NOT NULL,
    MODIFY COLUMN `updated_by` VARCHAR(99) NULL DEFAULT NULL,
    MODIFY COLUMN `deleted_by` VARCHAR(99) NULL DEFAULT NULL;

-- 4. 변경 결과 확인
SELECT column_name, column_type
FROM information_schema.columns
WHERE table_schema = 'te_story_platform'
  AND table_name = 'sp_work_item'
  AND column_name IN (
      'created_by',
      'updated_by',
      'deleted_by'
  )
ORDER BY ordinal_position;

SELECT COUNT(*) AS row_count FROM `te_story_platform`.`sp_work_item`;

/* PATCH 023 END */

/* =============================================================
PATCH 024 START
Database : te_story_platform
Table    : sp_work_session
Columns  : 3
Rows     : 0
Backup   : sp_work_session_backup_20260720_01
============================================================= */

-- 1. 변경 전 백업
CREATE TABLE `te_story_platform`.`sp_work_session_backup_20260720_01`
LIKE `te_story_platform`.`sp_work_session`;

START TRANSACTION;

INSERT INTO `te_story_platform`.`sp_work_session_backup_20260720_01`
SELECT *
FROM `te_story_platform`.`sp_work_session`;

COMMIT;

-- 2. 백업 검증
SELECT
    (SELECT COUNT(*) FROM `te_story_platform`.`sp_work_session`) AS original_count,
    (SELECT COUNT(*) FROM `te_story_platform`.`sp_work_session_backup_20260720_01`) AS backup_count;

-- 3. ALTER TABLE 문 실행
ALTER TABLE `te_story_platform`.`sp_work_session`
    MODIFY COLUMN `created_by` VARCHAR(99) NOT NULL,
    MODIFY COLUMN `updated_by` VARCHAR(99) NULL DEFAULT NULL,
    MODIFY COLUMN `deleted_by` VARCHAR(99) NULL DEFAULT NULL;

-- 4. 변경 결과 확인
SELECT column_name, column_type
FROM information_schema.columns
WHERE table_schema = 'te_story_platform'
  AND table_name = 'sp_work_session'
  AND column_name IN (
      'created_by',
      'updated_by',
      'deleted_by'
  )
ORDER BY ordinal_position;

SELECT COUNT(*) AS row_count FROM `te_story_platform`.`sp_work_session`;

/* PATCH 024 END */

/* =============================================================
PATCH 025 START
Database : te_common
Table    : cm_audit_policy
Columns  : 3
Rows     : 3
Backup   : cm_audit_policy_backup_20260720_01
============================================================= */

-- 1. 변경 전 백업
CREATE TABLE `te_common`.`cm_audit_policy_backup_20260720_01`
LIKE `te_common`.`cm_audit_policy`;

START TRANSACTION;

INSERT INTO `te_common`.`cm_audit_policy_backup_20260720_01`
SELECT *
FROM `te_common`.`cm_audit_policy`;

COMMIT;

-- 2. 백업 검증
SELECT
    (SELECT COUNT(*) FROM `te_common`.`cm_audit_policy`) AS original_count,
    (SELECT COUNT(*) FROM `te_common`.`cm_audit_policy_backup_20260720_01`) AS backup_count;

-- 3. ALTER TABLE 문 실행
ALTER TABLE `te_common`.`cm_audit_policy`
    MODIFY COLUMN `audit_policy_id` VARCHAR(99) NOT NULL COMMENT '감사 정책 ID',
    MODIFY COLUMN `audit_policy_code` VARCHAR(99) NOT NULL COMMENT '감사 정책 코드',
    MODIFY COLUMN `audit_policy_name` VARCHAR(150) NOT NULL COMMENT '감사 정책명';

-- 4. 변경 결과 확인
SELECT column_name, column_type
FROM information_schema.columns
WHERE table_schema = 'te_common'
  AND table_name = 'cm_audit_policy'
  AND column_name IN (
      'audit_policy_id',
      'audit_policy_code',
      'audit_policy_name'
  )
ORDER BY ordinal_position;

SELECT COUNT(*) AS row_count FROM `te_common`.`cm_audit_policy`;

/* PATCH 025 END */

/* =============================================================
PATCH 026 START
Database : te_common
Table    : cm_business_domain
Columns  : 3
Rows     : 7
Backup   : cm_business_domain_backup_20260720_01
============================================================= */

-- 1. 변경 전 백업
CREATE TABLE `te_common`.`cm_business_domain_backup_20260720_01`
LIKE `te_common`.`cm_business_domain`;

START TRANSACTION;

INSERT INTO `te_common`.`cm_business_domain_backup_20260720_01`
SELECT *
FROM `te_common`.`cm_business_domain`;

COMMIT;

-- 2. 백업 검증
SELECT
    (SELECT COUNT(*) FROM `te_common`.`cm_business_domain`) AS original_count,
    (SELECT COUNT(*) FROM `te_common`.`cm_business_domain_backup_20260720_01`) AS backup_count;

-- 3. ALTER TABLE 문 실행
ALTER TABLE `te_common`.`cm_business_domain`
    MODIFY COLUMN `business_domain_id` VARCHAR(99) NOT NULL COMMENT '업무 도메인 ID',
    MODIFY COLUMN `business_domain_code` VARCHAR(99) NOT NULL COMMENT '업무 도메인 코드',
    MODIFY COLUMN `business_domain_name` VARCHAR(150) NOT NULL COMMENT '업무 도메인명';

-- 4. 변경 결과 확인
SELECT column_name, column_type
FROM information_schema.columns
WHERE table_schema = 'te_common'
  AND table_name = 'cm_business_domain'
  AND column_name IN (
      'business_domain_id',
      'business_domain_code',
      'business_domain_name'
  )
ORDER BY ordinal_position;

SELECT COUNT(*) AS row_count FROM `te_common`.`cm_business_domain`;

/* PATCH 026 END */

/* =============================================================
PATCH 027 START
Database : te_common
Table    : cm_change_history
Columns  : 4
Rows     : 2
Backup   : cm_change_history_backup_20260720_01
============================================================= */

-- 1. 변경 전 백업
CREATE TABLE `te_common`.`cm_change_history_backup_20260720_01`
LIKE `te_common`.`cm_change_history`;

START TRANSACTION;

INSERT INTO `te_common`.`cm_change_history_backup_20260720_01`
SELECT *
FROM `te_common`.`cm_change_history`;

COMMIT;

-- 2. 백업 검증
SELECT
    (SELECT COUNT(*) FROM `te_common`.`cm_change_history`) AS original_count,
    (SELECT COUNT(*) FROM `te_common`.`cm_change_history_backup_20260720_01`) AS backup_count;

-- 3. ALTER TABLE 문 실행
ALTER TABLE `te_common`.`cm_change_history`
    MODIFY COLUMN `target_database_name` VARCHAR(150) NOT NULL COMMENT '대상 DB명',
    MODIFY COLUMN `target_table_name` VARCHAR(150) NOT NULL COMMENT '대상 테이블명',
    MODIFY COLUMN `target_record_id` VARCHAR(99) NOT NULL COMMENT '대상 레코드 ID',
    MODIFY COLUMN `action_type` VARCHAR(99) NOT NULL COMMENT '작업 유형 공통코드 CHANGE_ACTION_TYPE';

-- 4. 변경 결과 확인
SELECT column_name, column_type
FROM information_schema.columns
WHERE table_schema = 'te_common'
  AND table_name = 'cm_change_history'
  AND column_name IN (
      'target_database_name',
      'target_table_name',
      'target_record_id',
      'action_type'
  )
ORDER BY ordinal_position;

SELECT COUNT(*) AS row_count FROM `te_common`.`cm_change_history`;

/* PATCH 027 END */

/* =============================================================
PATCH 028 START
Database : te_common
Table    : cm_code_inspection_result
Columns  : 8
Rows     : 0
Backup   : cm_code_inspection_result_backup_20260720_01
============================================================= */

-- 1. 변경 전 백업
CREATE TABLE `te_common`.`cm_code_inspection_result_backup_20260720_01`
LIKE `te_common`.`cm_code_inspection_result`;

START TRANSACTION;

INSERT INTO `te_common`.`cm_code_inspection_result_backup_20260720_01`
SELECT *
FROM `te_common`.`cm_code_inspection_result`;

COMMIT;

-- 2. 백업 검증
SELECT
    (SELECT COUNT(*) FROM `te_common`.`cm_code_inspection_result`) AS original_count,
    (SELECT COUNT(*) FROM `te_common`.`cm_code_inspection_result_backup_20260720_01`) AS backup_count;

-- 3. ALTER TABLE 문 실행
ALTER TABLE `te_common`.`cm_code_inspection_result`
    MODIFY COLUMN `inspection_id` VARCHAR(99) NOT NULL,
    MODIFY COLUMN `inspection_type` VARCHAR(99) NOT NULL,
    MODIFY COLUMN `group_code` VARCHAR(99) NOT NULL,
    MODIFY COLUMN `code` VARCHAR(99) NULL DEFAULT NULL,
    MODIFY COLUMN `code_name` VARCHAR(150) NULL DEFAULT NULL,
    MODIFY COLUMN `related_codes` VARCHAR(2000) NULL DEFAULT NULL,
    MODIFY COLUMN `message` TEXT NOT NULL,
    MODIFY COLUMN `severity_code` VARCHAR(99) NOT NULL DEFAULT '''WARNING''';

-- 4. 변경 결과 확인
SELECT column_name, column_type
FROM information_schema.columns
WHERE table_schema = 'te_common'
  AND table_name = 'cm_code_inspection_result'
  AND column_name IN (
      'inspection_id',
      'inspection_type',
      'group_code',
      'code',
      'code_name',
      'related_codes',
      'message',
      'severity_code'
  )
ORDER BY ordinal_position;

SELECT COUNT(*) AS row_count FROM `te_common`.`cm_code_inspection_result`;

/* PATCH 028 END */

/* =============================================================
PATCH 029 START
Database : te_common
Table    : cm_common_code
Columns  : 1
Rows     : 344
Backup   : cm_common_code_backup_20260720_01
============================================================= */

-- 1. 변경 전 백업
CREATE TABLE `te_common`.`cm_common_code_backup_20260720_01`
LIKE `te_common`.`cm_common_code`;

START TRANSACTION;

INSERT INTO `te_common`.`cm_common_code_backup_20260720_01`
SELECT *
FROM `te_common`.`cm_common_code`;

COMMIT;

-- 2. 백업 검증
SELECT
    (SELECT COUNT(*) FROM `te_common`.`cm_common_code`) AS original_count,
    (SELECT COUNT(*) FROM `te_common`.`cm_common_code_backup_20260720_01`) AS backup_count;

-- 3. ALTER TABLE 문 실행
ALTER TABLE `te_common`.`cm_common_code`
    MODIFY COLUMN `code_name` VARCHAR(150) NOT NULL;

-- 4. 변경 결과 확인
SELECT column_name, column_type
FROM information_schema.columns
WHERE table_schema = 'te_common'
  AND table_name = 'cm_common_code'
  AND column_name IN (
      'code_name'
  )
ORDER BY ordinal_position;

SELECT COUNT(*) AS row_count FROM `te_common`.`cm_common_code`;

/* PATCH 029 END */

/* =============================================================
PATCH 030 START
Database : te_common
Table    : cm_common_code_group
Columns  : 2
Rows     : 51
Backup   : cm_common_code_group_backup_20260720_01
============================================================= */

-- 1. 변경 전 백업
CREATE TABLE `te_common`.`cm_common_code_group_backup_20260720_01`
LIKE `te_common`.`cm_common_code_group`;

START TRANSACTION;

INSERT INTO `te_common`.`cm_common_code_group_backup_20260720_01`
SELECT *
FROM `te_common`.`cm_common_code_group`;

COMMIT;

-- 2. 백업 검증
SELECT
    (SELECT COUNT(*) FROM `te_common`.`cm_common_code_group`) AS original_count,
    (SELECT COUNT(*) FROM `te_common`.`cm_common_code_group_backup_20260720_01`) AS backup_count;

-- 3. ALTER TABLE 문 실행
ALTER TABLE `te_common`.`cm_common_code_group`
    MODIFY COLUMN `group_name` VARCHAR(150) NOT NULL,
    MODIFY COLUMN `group_description` VARCHAR(2000) NULL DEFAULT NULL COMMENT '그룹 설명';

-- 4. 변경 결과 확인
SELECT column_name, column_type
FROM information_schema.columns
WHERE table_schema = 'te_common'
  AND table_name = 'cm_common_code_group'
  AND column_name IN (
      'group_name',
      'group_description'
  )
ORDER BY ordinal_position;

SELECT COUNT(*) AS row_count FROM `te_common`.`cm_common_code_group`;

/* PATCH 030 END */

/* =============================================================
PATCH 031 START
Database : te_common
Table    : cm_consent_history
Columns  : 2
Rows     : 0
Backup   : cm_consent_history_backup_20260720_01
============================================================= */

-- 1. 변경 전 백업
CREATE TABLE `te_common`.`cm_consent_history_backup_20260720_01`
LIKE `te_common`.`cm_consent_history`;

START TRANSACTION;

INSERT INTO `te_common`.`cm_consent_history_backup_20260720_01`
SELECT *
FROM `te_common`.`cm_consent_history`;

COMMIT;

-- 2. 백업 검증
SELECT
    (SELECT COUNT(*) FROM `te_common`.`cm_consent_history`) AS original_count,
    (SELECT COUNT(*) FROM `te_common`.`cm_consent_history_backup_20260720_01`) AS backup_count;

-- 3. ALTER TABLE 문 실행
ALTER TABLE `te_common`.`cm_consent_history`
    MODIFY COLUMN `user_id` VARCHAR(99) NOT NULL,
    MODIFY COLUMN `consent_type` VARCHAR(99) NOT NULL;

-- 4. 변경 결과 확인
SELECT column_name, column_type
FROM information_schema.columns
WHERE table_schema = 'te_common'
  AND table_name = 'cm_consent_history'
  AND column_name IN (
      'user_id',
      'consent_type'
  )
ORDER BY ordinal_position;

SELECT COUNT(*) AS row_count FROM `te_common`.`cm_consent_history`;

/* PATCH 031 END */

/* =============================================================
PATCH 032 START
Database : te_common
Table    : cm_country
Columns  : 3
Rows     : 5
Backup   : cm_country_backup_20260720_01
============================================================= */

-- 1. 변경 전 백업
CREATE TABLE `te_common`.`cm_country_backup_20260720_01`
LIKE `te_common`.`cm_country`;

START TRANSACTION;

INSERT INTO `te_common`.`cm_country_backup_20260720_01`
SELECT *
FROM `te_common`.`cm_country`;

COMMIT;

-- 2. 백업 검증
SELECT
    (SELECT COUNT(*) FROM `te_common`.`cm_country`) AS original_count,
    (SELECT COUNT(*) FROM `te_common`.`cm_country_backup_20260720_01`) AS backup_count;

-- 3. ALTER TABLE 문 실행
ALTER TABLE `te_common`.`cm_country`
    MODIFY COLUMN `country_code` VARCHAR(99) NOT NULL,
    MODIFY COLUMN `country_name` VARCHAR(150) NOT NULL,
    MODIFY COLUMN `native_name` VARCHAR(150) NULL DEFAULT NULL;

-- 4. 변경 결과 확인
SELECT column_name, column_type
FROM information_schema.columns
WHERE table_schema = 'te_common'
  AND table_name = 'cm_country'
  AND column_name IN (
      'country_code',
      'country_name',
      'native_name'
  )
ORDER BY ordinal_position;

SELECT COUNT(*) AS row_count FROM `te_common`.`cm_country`;

/* PATCH 032 END */

/* =============================================================
PATCH 033 START
Database : te_common
Table    : cm_data_classification
Columns  : 2
Rows     : 5
Backup   : cm_data_classification_backup_20260720_01
============================================================= */

-- 1. 변경 전 백업
CREATE TABLE `te_common`.`cm_data_classification_backup_20260720_01`
LIKE `te_common`.`cm_data_classification`;

START TRANSACTION;

INSERT INTO `te_common`.`cm_data_classification_backup_20260720_01`
SELECT *
FROM `te_common`.`cm_data_classification`;

COMMIT;

-- 2. 백업 검증
SELECT
    (SELECT COUNT(*) FROM `te_common`.`cm_data_classification`) AS original_count,
    (SELECT COUNT(*) FROM `te_common`.`cm_data_classification_backup_20260720_01`) AS backup_count;

-- 3. ALTER TABLE 문 실행
ALTER TABLE `te_common`.`cm_data_classification`
    MODIFY COLUMN `classification_code` VARCHAR(99) NOT NULL COMMENT '데이터 등급 코드',
    MODIFY COLUMN `classification_name` VARCHAR(150) NOT NULL COMMENT '데이터 등급';

-- 4. 변경 결과 확인
SELECT column_name, column_type
FROM information_schema.columns
WHERE table_schema = 'te_common'
  AND table_name = 'cm_data_classification'
  AND column_name IN (
      'classification_code',
      'classification_name'
  )
ORDER BY ordinal_position;

SELECT COUNT(*) AS row_count FROM `te_common`.`cm_data_classification`;

/* PATCH 033 END */

/* =============================================================
PATCH 034 START
Database : te_common
Table    : cm_data_lifecycle_index
Columns  : 10
Rows     : 0
Backup   : cm_data_lifecycle_index_backup_20260720_01
============================================================= */

-- 1. 변경 전 백업
CREATE TABLE `te_common`.`cm_data_lifecycle_index_backup_20260720_01`
LIKE `te_common`.`cm_data_lifecycle_index`;

START TRANSACTION;

INSERT INTO `te_common`.`cm_data_lifecycle_index_backup_20260720_01`
SELECT *
FROM `te_common`.`cm_data_lifecycle_index`;

COMMIT;

-- 2. 백업 검증
SELECT
    (SELECT COUNT(*) FROM `te_common`.`cm_data_lifecycle_index`) AS original_count,
    (SELECT COUNT(*) FROM `te_common`.`cm_data_lifecycle_index_backup_20260720_01`) AS backup_count;

-- 3. ALTER TABLE 문 실행
ALTER TABLE `te_common`.`cm_data_lifecycle_index`
    MODIFY COLUMN `user_id` VARCHAR(99) NOT NULL COMMENT '사용자 ID',
    MODIFY COLUMN `data_asset_id` VARCHAR(99) NOT NULL COMMENT '데이터 자산 ID',
    MODIFY COLUMN `data_type` VARCHAR(99) NOT NULL COMMENT '데이터 유형',
    MODIFY COLUMN `repository_id` VARCHAR(99) NOT NULL COMMENT '저장소 ID',
    MODIFY COLUMN `storage_database` VARCHAR(150) NULL DEFAULT NULL COMMENT 'DB명',
    MODIFY COLUMN `storage_collection` VARCHAR(150) NULL DEFAULT NULL COMMENT 'Mongo Collection',
    MODIFY COLUMN `storage_table` VARCHAR(150) NULL DEFAULT NULL COMMENT 'MariaDB Table',
    MODIFY COLUMN `storage_record_id` VARCHAR(99) NULL DEFAULT NULL COMMENT '레코드 ID',
    MODIFY COLUMN `storage_document_id` VARCHAR(99) NULL DEFAULT NULL COMMENT 'Mongo Document ID',
    MODIFY COLUMN `disposal_reason` VARCHAR(2000) NULL DEFAULT NULL COMMENT '폐기사유';

-- 4. 변경 결과 확인
SELECT column_name, column_type
FROM information_schema.columns
WHERE table_schema = 'te_common'
  AND table_name = 'cm_data_lifecycle_index'
  AND column_name IN (
      'user_id',
      'data_asset_id',
      'data_type',
      'repository_id',
      'storage_database',
      'storage_collection',
      'storage_table',
      'storage_record_id',
      'storage_document_id',
      'disposal_reason'
  )
ORDER BY ordinal_position;

SELECT COUNT(*) AS row_count FROM `te_common`.`cm_data_lifecycle_index`;

/* PATCH 034 END */

/* =============================================================
PATCH 035 START
Database : te_common
Table    : cm_data_type
Columns  : 5
Rows     : 19
Backup   : cm_data_type_backup_20260720_01
============================================================= */

-- 1. 변경 전 백업
CREATE TABLE `te_common`.`cm_data_type_backup_20260720_01`
LIKE `te_common`.`cm_data_type`;

START TRANSACTION;

INSERT INTO `te_common`.`cm_data_type_backup_20260720_01`
SELECT *
FROM `te_common`.`cm_data_type`;

COMMIT;

-- 2. 백업 검증
SELECT
    (SELECT COUNT(*) FROM `te_common`.`cm_data_type`) AS original_count,
    (SELECT COUNT(*) FROM `te_common`.`cm_data_type_backup_20260720_01`) AS backup_count;

-- 3. ALTER TABLE 문 실행
ALTER TABLE `te_common`.`cm_data_type`
    MODIFY COLUMN `data_type_code` VARCHAR(99) NOT NULL,
    MODIFY COLUMN `data_type_name` VARCHAR(150) NULL DEFAULT NULL,
    MODIFY COLUMN `default_classification_code` VARCHAR(99) NULL DEFAULT NULL,
    MODIFY COLUMN `default_storage_type` VARCHAR(99) NULL DEFAULT NULL,
    MODIFY COLUMN `default_retention_policy_code` VARCHAR(99) NULL DEFAULT NULL;

-- 4. 변경 결과 확인
SELECT column_name, column_type
FROM information_schema.columns
WHERE table_schema = 'te_common'
  AND table_name = 'cm_data_type'
  AND column_name IN (
      'data_type_code',
      'data_type_name',
      'default_classification_code',
      'default_storage_type',
      'default_retention_policy_code'
  )
ORDER BY ordinal_position;

SELECT COUNT(*) AS row_count FROM `te_common`.`cm_data_type`;

/* PATCH 035 END */

/* =============================================================
PATCH 036 START
Database : te_common
Table    : cm_language
Columns  : 3
Rows     : 4
Backup   : cm_language_backup_20260720_01
============================================================= */

-- 1. 변경 전 백업
CREATE TABLE `te_common`.`cm_language_backup_20260720_01`
LIKE `te_common`.`cm_language`;

START TRANSACTION;

INSERT INTO `te_common`.`cm_language_backup_20260720_01`
SELECT *
FROM `te_common`.`cm_language`;

COMMIT;

-- 2. 백업 검증
SELECT
    (SELECT COUNT(*) FROM `te_common`.`cm_language`) AS original_count,
    (SELECT COUNT(*) FROM `te_common`.`cm_language_backup_20260720_01`) AS backup_count;

-- 3. ALTER TABLE 문 실행
ALTER TABLE `te_common`.`cm_language`
    MODIFY COLUMN `language_code` VARCHAR(99) NOT NULL,
    MODIFY COLUMN `language_name` VARCHAR(150) NOT NULL,
    MODIFY COLUMN `native_name` VARCHAR(150) NOT NULL;

-- 4. 변경 결과 확인
SELECT column_name, column_type
FROM information_schema.columns
WHERE table_schema = 'te_common'
  AND table_name = 'cm_language'
  AND column_name IN (
      'language_code',
      'language_name',
      'native_name'
  )
ORDER BY ordinal_position;

SELECT COUNT(*) AS row_count FROM `te_common`.`cm_language`;

/* PATCH 036 END */

/* =============================================================
PATCH 037 START
Database : te_common
Table    : cm_legal_retention_policy
Columns  : 4
Rows     : 4
Backup   : cm_legal_retention_policy_backup_20260720_01
============================================================= */

-- 1. 변경 전 백업
CREATE TABLE `te_common`.`cm_legal_retention_policy_backup_20260720_01`
LIKE `te_common`.`cm_legal_retention_policy`;

START TRANSACTION;

INSERT INTO `te_common`.`cm_legal_retention_policy_backup_20260720_01`
SELECT *
FROM `te_common`.`cm_legal_retention_policy`;

COMMIT;

-- 2. 백업 검증
SELECT
    (SELECT COUNT(*) FROM `te_common`.`cm_legal_retention_policy`) AS original_count,
    (SELECT COUNT(*) FROM `te_common`.`cm_legal_retention_policy_backup_20260720_01`) AS backup_count;

-- 3. ALTER TABLE 문 실행
ALTER TABLE `te_common`.`cm_legal_retention_policy`
    MODIFY COLUMN `data_type` VARCHAR(99) NOT NULL COMMENT '데이터 유형',
    MODIFY COLUMN `legal_basis_code` VARCHAR(99) NOT NULL COMMENT '법적 근거 코드',
    MODIFY COLUMN `retention_reason` VARCHAR(2000) NOT NULL COMMENT '보존 사유',
    MODIFY COLUMN `disposal_action_code` VARCHAR(99) NOT NULL COMMENT '보존기간 만료 후 처리 방식';

-- 4. 변경 결과 확인
SELECT column_name, column_type
FROM information_schema.columns
WHERE table_schema = 'te_common'
  AND table_name = 'cm_legal_retention_policy'
  AND column_name IN (
      'data_type',
      'legal_basis_code',
      'retention_reason',
      'disposal_action_code'
  )
ORDER BY ordinal_position;

SELECT COUNT(*) AS row_count FROM `te_common`.`cm_legal_retention_policy`;

/* PATCH 037 END */

/* =============================================================
PATCH 038 START
Database : te_common
Table    : cm_locale
Columns  : 10
Rows     : 5
Backup   : cm_locale_backup_20260720_01
============================================================= */

-- 1. 변경 전 백업
CREATE TABLE `te_common`.`cm_locale_backup_20260720_01`
LIKE `te_common`.`cm_locale`;

START TRANSACTION;

INSERT INTO `te_common`.`cm_locale_backup_20260720_01`
SELECT *
FROM `te_common`.`cm_locale`;

COMMIT;

-- 2. 백업 검증
SELECT
    (SELECT COUNT(*) FROM `te_common`.`cm_locale`) AS original_count,
    (SELECT COUNT(*) FROM `te_common`.`cm_locale_backup_20260720_01`) AS backup_count;

-- 3. ALTER TABLE 문 실행
ALTER TABLE `te_common`.`cm_locale`
    MODIFY COLUMN `locale_code` VARCHAR(99) NOT NULL,
    MODIFY COLUMN `language_code` VARCHAR(99) NOT NULL,
    MODIFY COLUMN `country_code` VARCHAR(99) NOT NULL,
    MODIFY COLUMN `locale_name` VARCHAR(150) NOT NULL,
    MODIFY COLUMN `native_name` VARCHAR(150) NOT NULL,
    MODIFY COLUMN `date_format` VARCHAR(99) NULL DEFAULT NULL,
    MODIFY COLUMN `time_format` VARCHAR(99) NULL DEFAULT NULL,
    MODIFY COLUMN `datetime_format` VARCHAR(99) NULL DEFAULT NULL,
    MODIFY COLUMN `number_format` VARCHAR(99) NULL DEFAULT NULL,
    MODIFY COLUMN `timezone_id` VARCHAR(99) NULL DEFAULT NULL;

-- 4. 변경 결과 확인
SELECT column_name, column_type
FROM information_schema.columns
WHERE table_schema = 'te_common'
  AND table_name = 'cm_locale'
  AND column_name IN (
      'locale_code',
      'language_code',
      'country_code',
      'locale_name',
      'native_name',
      'date_format',
      'time_format',
      'datetime_format',
      'number_format',
      'timezone_id'
  )
ORDER BY ordinal_position;

SELECT COUNT(*) AS row_count FROM `te_common`.`cm_locale`;

/* PATCH 038 END */

/* =============================================================
PATCH 039 START
Database : te_common
Table    : cm_login_history
Columns  : 4
Rows     : 0
Backup   : cm_login_history_backup_20260720_01
============================================================= */

-- 1. 변경 전 백업
CREATE TABLE `te_common`.`cm_login_history_backup_20260720_01`
LIKE `te_common`.`cm_login_history`;

START TRANSACTION;

INSERT INTO `te_common`.`cm_login_history_backup_20260720_01`
SELECT *
FROM `te_common`.`cm_login_history`;

COMMIT;

-- 2. 백업 검증
SELECT
    (SELECT COUNT(*) FROM `te_common`.`cm_login_history`) AS original_count,
    (SELECT COUNT(*) FROM `te_common`.`cm_login_history_backup_20260720_01`) AS backup_count;

-- 3. ALTER TABLE 문 실행
ALTER TABLE `te_common`.`cm_login_history`
    MODIFY COLUMN `login_history_id` VARCHAR(99) NOT NULL,
    MODIFY COLUMN `member_id` VARCHAR(99) NULL DEFAULT NULL,
    MODIFY COLUMN `login_id` VARCHAR(99) NOT NULL,
    MODIFY COLUMN `login_status_code` VARCHAR(99) NOT NULL;

-- 4. 변경 결과 확인
SELECT column_name, column_type
FROM information_schema.columns
WHERE table_schema = 'te_common'
  AND table_name = 'cm_login_history'
  AND column_name IN (
      'login_history_id',
      'member_id',
      'login_id',
      'login_status_code'
  )
ORDER BY ordinal_position;

SELECT COUNT(*) AS row_count FROM `te_common`.`cm_login_history`;

/* PATCH 039 END */

/* =============================================================
PATCH 040 START
Database : te_common
Table    : cm_member
Columns  : 5
Rows     : 1
Backup   : cm_member_backup_20260720_01
============================================================= */

-- 1. 변경 전 백업
CREATE TABLE `te_common`.`cm_member_backup_20260720_01`
LIKE `te_common`.`cm_member`;

START TRANSACTION;

INSERT INTO `te_common`.`cm_member_backup_20260720_01`
SELECT *
FROM `te_common`.`cm_member`;

COMMIT;

-- 2. 백업 검증
SELECT
    (SELECT COUNT(*) FROM `te_common`.`cm_member`) AS original_count,
    (SELECT COUNT(*) FROM `te_common`.`cm_member_backup_20260720_01`) AS backup_count;

-- 3. ALTER TABLE 문 실행
ALTER TABLE `te_common`.`cm_member`
    MODIFY COLUMN `member_id` VARCHAR(99) NOT NULL,
    MODIFY COLUMN `email` VARCHAR(500) NOT NULL,
    MODIFY COLUMN `password_hash` VARCHAR(128) NOT NULL,
    MODIFY COLUMN `member_name` VARCHAR(150) NOT NULL,
    MODIFY COLUMN `member_type_code` VARCHAR(99) NOT NULL;

-- 4. 변경 결과 확인
SELECT column_name, column_type
FROM information_schema.columns
WHERE table_schema = 'te_common'
  AND table_name = 'cm_member'
  AND column_name IN (
      'member_id',
      'email',
      'password_hash',
      'member_name',
      'member_type_code'
  )
ORDER BY ordinal_position;

SELECT COUNT(*) AS row_count FROM `te_common`.`cm_member`;

/* PATCH 040 END */

/* =============================================================
PATCH 041 START
Database : te_common
Table    : cm_member_private
Columns  : 4
Rows     : 0
Backup   : cm_member_private_backup_20260720_01
============================================================= */

-- 1. 변경 전 백업
CREATE TABLE `te_common`.`cm_member_private_backup_20260720_01`
LIKE `te_common`.`cm_member_private`;

START TRANSACTION;

INSERT INTO `te_common`.`cm_member_private_backup_20260720_01`
SELECT *
FROM `te_common`.`cm_member_private`;

COMMIT;

-- 2. 백업 검증
SELECT
    (SELECT COUNT(*) FROM `te_common`.`cm_member_private`) AS original_count,
    (SELECT COUNT(*) FROM `te_common`.`cm_member_private_backup_20260720_01`) AS backup_count;

-- 3. ALTER TABLE 문 실행
ALTER TABLE `te_common`.`cm_member_private`
    MODIFY COLUMN `member_id` VARCHAR(99) NOT NULL,
    MODIFY COLUMN `birth_date` DATETIME NULL DEFAULT NULL,
    MODIFY COLUMN `phone` VARCHAR(50) NULL DEFAULT NULL,
    MODIFY COLUMN `email` VARCHAR(500) NULL DEFAULT NULL;

-- 4. 변경 결과 확인
SELECT column_name, column_type
FROM information_schema.columns
WHERE table_schema = 'te_common'
  AND table_name = 'cm_member_private'
  AND column_name IN (
      'member_id',
      'birth_date',
      'phone',
      'email'
  )
ORDER BY ordinal_position;

SELECT COUNT(*) AS row_count FROM `te_common`.`cm_member_private`;

/* PATCH 041 END */

/* =============================================================
PATCH 042 START
Database : te_common
Table    : cm_member_role
Columns  : 3
Rows     : 1
Backup   : cm_member_role_backup_20260720_01
============================================================= */

-- 1. 변경 전 백업
CREATE TABLE `te_common`.`cm_member_role_backup_20260720_01`
LIKE `te_common`.`cm_member_role`;

START TRANSACTION;

INSERT INTO `te_common`.`cm_member_role_backup_20260720_01`
SELECT *
FROM `te_common`.`cm_member_role`;

COMMIT;

-- 2. 백업 검증
SELECT
    (SELECT COUNT(*) FROM `te_common`.`cm_member_role`) AS original_count,
    (SELECT COUNT(*) FROM `te_common`.`cm_member_role_backup_20260720_01`) AS backup_count;

-- 3. ALTER TABLE 문 실행
ALTER TABLE `te_common`.`cm_member_role`
    MODIFY COLUMN `member_role_id` VARCHAR(99) NOT NULL,
    MODIFY COLUMN `member_id` VARCHAR(99) NOT NULL,
    MODIFY COLUMN `role_id` VARCHAR(99) NOT NULL;

-- 4. 변경 결과 확인
SELECT column_name, column_type
FROM information_schema.columns
WHERE table_schema = 'te_common'
  AND table_name = 'cm_member_role'
  AND column_name IN (
      'member_role_id',
      'member_id',
      'role_id'
  )
ORDER BY ordinal_position;

SELECT COUNT(*) AS row_count FROM `te_common`.`cm_member_role`;

/* PATCH 042 END */

/* =============================================================
PATCH 043 START
Database : te_common
Table    : cm_repository
Columns  : 11
Rows     : 3
Backup   : cm_repository_backup_20260720_01
============================================================= */

-- 1. 변경 전 백업
CREATE TABLE `te_common`.`cm_repository_backup_20260720_01`
LIKE `te_common`.`cm_repository`;

START TRANSACTION;

INSERT INTO `te_common`.`cm_repository_backup_20260720_01`
SELECT *
FROM `te_common`.`cm_repository`;

COMMIT;

-- 2. 백업 검증
SELECT
    (SELECT COUNT(*) FROM `te_common`.`cm_repository`) AS original_count,
    (SELECT COUNT(*) FROM `te_common`.`cm_repository_backup_20260720_01`) AS backup_count;

-- 3. ALTER TABLE 문 실행
ALTER TABLE `te_common`.`cm_repository`
    MODIFY COLUMN `repository_id` VARCHAR(99) NOT NULL COMMENT 'Repository ID',
    MODIFY COLUMN `book_code` VARCHAR(99) NULL DEFAULT NULL COMMENT 'Story Book 코드',
    MODIFY COLUMN `chapter_code` VARCHAR(99) NULL DEFAULT NULL COMMENT 'Chapter 코드',
    MODIFY COLUMN `section_code` VARCHAR(99) NULL DEFAULT NULL COMMENT 'Section 코드',
    MODIFY COLUMN `business_code` VARCHAR(99) NOT NULL COMMENT '업무분류 코드',
    MODIFY COLUMN `domain_code` VARCHAR(99) NOT NULL COMMENT '도메인 코드',
    MODIFY COLUMN `data_type_code` VARCHAR(99) NOT NULL COMMENT '자료구분 코드',
    MODIFY COLUMN `data_code` VARCHAR(99) NOT NULL COMMENT '자료 코드',
    MODIFY COLUMN `data_name` VARCHAR(150) NOT NULL COMMENT '자료명',
    MODIFY COLUMN `data_version` VARCHAR(99) NOT NULL DEFAULT '''v1.0''' COMMENT '자료 버전',
    MODIFY COLUMN `code_description` VARCHAR(2000) NULL DEFAULT NULL COMMENT '설명';

-- 4. 변경 결과 확인
SELECT column_name, column_type
FROM information_schema.columns
WHERE table_schema = 'te_common'
  AND table_name = 'cm_repository'
  AND column_name IN (
      'repository_id',
      'book_code',
      'chapter_code',
      'section_code',
      'business_code',
      'domain_code',
      'data_type_code',
      'data_code',
      'data_name',
      'data_version',
      'code_description'
  )
ORDER BY ordinal_position;

SELECT COUNT(*) AS row_count FROM `te_common`.`cm_repository`;

/* PATCH 043 END */

/* =============================================================
PATCH 044 START
Database : te_common
Table    : cm_role
Columns  : 3
Rows     : 1
Backup   : cm_role_backup_20260720_01
============================================================= */

-- 1. 변경 전 백업
CREATE TABLE `te_common`.`cm_role_backup_20260720_01`
LIKE `te_common`.`cm_role`;

START TRANSACTION;

INSERT INTO `te_common`.`cm_role_backup_20260720_01`
SELECT *
FROM `te_common`.`cm_role`;

COMMIT;

-- 2. 백업 검증
SELECT
    (SELECT COUNT(*) FROM `te_common`.`cm_role`) AS original_count,
    (SELECT COUNT(*) FROM `te_common`.`cm_role_backup_20260720_01`) AS backup_count;

-- 3. ALTER TABLE 문 실행
ALTER TABLE `te_common`.`cm_role`
    MODIFY COLUMN `role_id` VARCHAR(99) NOT NULL,
    MODIFY COLUMN `role_code` VARCHAR(99) NOT NULL,
    MODIFY COLUMN `role_name` VARCHAR(150) NOT NULL;

-- 4. 변경 결과 확인
SELECT column_name, column_type
FROM information_schema.columns
WHERE table_schema = 'te_common'
  AND table_name = 'cm_role'
  AND column_name IN (
      'role_id',
      'role_code',
      'role_name'
  )
ORDER BY ordinal_position;

SELECT COUNT(*) AS row_count FROM `te_common`.`cm_role`;

/* PATCH 044 END */

/* =============================================================
PATCH 045 START
Database : te_common
Table    : cm_role_rule
Columns  : 2
Rows     : 0
Backup   : cm_role_rule_backup_20260720_01
============================================================= */

-- 1. 변경 전 백업
CREATE TABLE `te_common`.`cm_role_rule_backup_20260720_01`
LIKE `te_common`.`cm_role_rule`;

START TRANSACTION;

INSERT INTO `te_common`.`cm_role_rule_backup_20260720_01`
SELECT *
FROM `te_common`.`cm_role_rule`;

COMMIT;

-- 2. 백업 검증
SELECT
    (SELECT COUNT(*) FROM `te_common`.`cm_role_rule`) AS original_count,
    (SELECT COUNT(*) FROM `te_common`.`cm_role_rule_backup_20260720_01`) AS backup_count;

-- 3. ALTER TABLE 문 실행
ALTER TABLE `te_common`.`cm_role_rule`
    MODIFY COLUMN `role_id` VARCHAR(99) NOT NULL COMMENT 'Role 식별자. cm_role.role_id 참조',
    MODIFY COLUMN `rule_id` VARCHAR(99) NOT NULL COMMENT 'Rule 식별자. rl_rule.rule_id 참조';

-- 4. 변경 결과 확인
SELECT column_name, column_type
FROM information_schema.columns
WHERE table_schema = 'te_common'
  AND table_name = 'cm_role_rule'
  AND column_name IN (
      'role_id',
      'rule_id'
  )
ORDER BY ordinal_position;

SELECT COUNT(*) AS row_count FROM `te_common`.`cm_role_rule`;

/* PATCH 045 END */

/* =============================================================
PATCH 046 START
Database : te_common
Table    : cm_sequence
Columns  : 9
Rows     : 1
Backup   : cm_sequence_backup_20260720_01
============================================================= */

-- 1. 변경 전 백업
CREATE TABLE `te_common`.`cm_sequence_backup_20260720_01`
LIKE `te_common`.`cm_sequence`;

START TRANSACTION;

INSERT INTO `te_common`.`cm_sequence_backup_20260720_01`
SELECT *
FROM `te_common`.`cm_sequence`;

COMMIT;

-- 2. 백업 검증
SELECT
    (SELECT COUNT(*) FROM `te_common`.`cm_sequence`) AS original_count,
    (SELECT COUNT(*) FROM `te_common`.`cm_sequence_backup_20260720_01`) AS backup_count;

-- 3. ALTER TABLE 문 실행
ALTER TABLE `te_common`.`cm_sequence`
    MODIFY COLUMN `sequence_code` VARCHAR(99) NOT NULL,
    MODIFY COLUMN `sequence_date` DATETIME NOT NULL,
    MODIFY COLUMN `current_value` VARCHAR(2000) NOT NULL DEFAULT '0',
    MODIFY COLUMN `created_by` VARCHAR(99) NOT NULL DEFAULT '''SYSTEM''',
    MODIFY COLUMN `updated_by` VARCHAR(99) NULL DEFAULT NULL,
    MODIFY COLUMN `deleted_by` VARCHAR(99) NULL DEFAULT NULL,
    MODIFY COLUMN `client_ip` VARCHAR(99) NULL DEFAULT NULL,
    MODIFY COLUMN `program_id` VARCHAR(99) NULL DEFAULT NULL,
    MODIFY COLUMN `status_code` VARCHAR(99) NOT NULL DEFAULT '''ACTIVE''';

-- 4. 변경 결과 확인
SELECT column_name, column_type
FROM information_schema.columns
WHERE table_schema = 'te_common'
  AND table_name = 'cm_sequence'
  AND column_name IN (
      'sequence_code',
      'sequence_date',
      'current_value',
      'created_by',
      'updated_by',
      'deleted_by',
      'client_ip',
      'program_id',
      'status_code'
  )
ORDER BY ordinal_position;

SELECT COUNT(*) AS row_count FROM `te_common`.`cm_sequence`;

/* PATCH 046 END */

/* =============================================================
PATCH 047 START
Database : te_common
Table    : cm_sequence_definition
Columns  : 8
Rows     : 0
Backup   : cm_sequence_definition_backup_20260720_01
============================================================= */

-- 1. 변경 전 백업
CREATE TABLE `te_common`.`cm_sequence_definition_backup_20260720_01`
LIKE `te_common`.`cm_sequence_definition`;

START TRANSACTION;

INSERT INTO `te_common`.`cm_sequence_definition_backup_20260720_01`
SELECT *
FROM `te_common`.`cm_sequence_definition`;

COMMIT;

-- 2. 백업 검증
SELECT
    (SELECT COUNT(*) FROM `te_common`.`cm_sequence_definition`) AS original_count,
    (SELECT COUNT(*) FROM `te_common`.`cm_sequence_definition_backup_20260720_01`) AS backup_count;

-- 3. ALTER TABLE 문 실행
ALTER TABLE `te_common`.`cm_sequence_definition`
    MODIFY COLUMN `sequence_code` VARCHAR(99) NOT NULL COMMENT '시퀀스 코드',
    MODIFY COLUMN `sequence_name` VARCHAR(150) NOT NULL COMMENT '시퀀스명',
    MODIFY COLUMN `function_code` VARCHAR(99) NOT NULL COMMENT '기능 코드',
    MODIFY COLUMN `domain_code` VARCHAR(99) NOT NULL COMMENT '도메인 코드',
    MODIFY COLUMN `policy_code` VARCHAR(99) NOT NULL COMMENT '시퀀스 정책 코드',
    MODIFY COLUMN `format_code` VARCHAR(99) NOT NULL COMMENT '시퀀스 포맷 코드',
    MODIFY COLUMN `prefix_code` VARCHAR(99) NULL DEFAULT NULL COMMENT 'Prefix 코드',
    MODIFY COLUMN `code_description` VARCHAR(2000) NULL DEFAULT NULL COMMENT '설명';

-- 4. 변경 결과 확인
SELECT column_name, column_type
FROM information_schema.columns
WHERE table_schema = 'te_common'
  AND table_name = 'cm_sequence_definition'
  AND column_name IN (
      'sequence_code',
      'sequence_name',
      'function_code',
      'domain_code',
      'policy_code',
      'format_code',
      'prefix_code',
      'code_description'
  )
ORDER BY ordinal_position;

SELECT COUNT(*) AS row_count FROM `te_common`.`cm_sequence_definition`;

/* PATCH 047 END */

/* =============================================================
PATCH 048 START
Database : te_common
Table    : cm_sequence_format
Columns  : 3
Rows     : 4
Backup   : cm_sequence_format_backup_20260720_01
============================================================= */

-- 1. 변경 전 백업
CREATE TABLE `te_common`.`cm_sequence_format_backup_20260720_01`
LIKE `te_common`.`cm_sequence_format`;

START TRANSACTION;

INSERT INTO `te_common`.`cm_sequence_format_backup_20260720_01`
SELECT *
FROM `te_common`.`cm_sequence_format`;

COMMIT;

-- 2. 백업 검증
SELECT
    (SELECT COUNT(*) FROM `te_common`.`cm_sequence_format`) AS original_count,
    (SELECT COUNT(*) FROM `te_common`.`cm_sequence_format_backup_20260720_01`) AS backup_count;

-- 3. ALTER TABLE 문 실행
ALTER TABLE `te_common`.`cm_sequence_format`
    MODIFY COLUMN `format_code` VARCHAR(99) NOT NULL COMMENT '시퀀스 포맷 코드',
    MODIFY COLUMN `format_name` VARCHAR(150) NOT NULL COMMENT '시퀀스 포맷명',
    MODIFY COLUMN `format_pattern` VARCHAR(500) NOT NULL COMMENT '시퀀스 생성 패턴';

-- 4. 변경 결과 확인
SELECT column_name, column_type
FROM information_schema.columns
WHERE table_schema = 'te_common'
  AND table_name = 'cm_sequence_format'
  AND column_name IN (
      'format_code',
      'format_name',
      'format_pattern'
  )
ORDER BY ordinal_position;

SELECT COUNT(*) AS row_count FROM `te_common`.`cm_sequence_format`;

/* PATCH 048 END */

/* =============================================================
PATCH 049 START
Database : te_common
Table    : cm_sequence_format_definition
Columns  : 4
Rows     : 0
Backup   : cm_sequence_format_definition_backup_20260720_01
============================================================= */

-- 1. 변경 전 백업
CREATE TABLE `te_common`.`cm_sequence_format_definition_backup_20260720_01`
LIKE `te_common`.`cm_sequence_format_definition`;

START TRANSACTION;

INSERT INTO `te_common`.`cm_sequence_format_definition_backup_20260720_01`
SELECT *
FROM `te_common`.`cm_sequence_format_definition`;

COMMIT;

-- 2. 백업 검증
SELECT
    (SELECT COUNT(*) FROM `te_common`.`cm_sequence_format_definition`) AS original_count,
    (SELECT COUNT(*) FROM `te_common`.`cm_sequence_format_definition_backup_20260720_01`) AS backup_count;

-- 3. ALTER TABLE 문 실행
ALTER TABLE `te_common`.`cm_sequence_format_definition`
    MODIFY COLUMN `format_code` VARCHAR(99) NOT NULL COMMENT '시퀀스 포맷 코드',
    MODIFY COLUMN `format_name` VARCHAR(150) NOT NULL COMMENT '시퀀스 포맷명',
    MODIFY COLUMN `format_pattern` VARCHAR(500) NOT NULL COMMENT '생성 패턴',
    MODIFY COLUMN `code_description` VARCHAR(2000) NULL DEFAULT NULL COMMENT '설명';

-- 4. 변경 결과 확인
SELECT column_name, column_type
FROM information_schema.columns
WHERE table_schema = 'te_common'
  AND table_name = 'cm_sequence_format_definition'
  AND column_name IN (
      'format_code',
      'format_name',
      'format_pattern',
      'code_description'
  )
ORDER BY ordinal_position;

SELECT COUNT(*) AS row_count FROM `te_common`.`cm_sequence_format_definition`;

/* PATCH 049 END */

/* =============================================================
PATCH 050 START
Database : te_common
Table    : cm_sequence_policy
Columns  : 3
Rows     : 4
Backup   : cm_sequence_policy_backup_20260720_01
============================================================= */

-- 1. 변경 전 백업
CREATE TABLE `te_common`.`cm_sequence_policy_backup_20260720_01`
LIKE `te_common`.`cm_sequence_policy`;

START TRANSACTION;

INSERT INTO `te_common`.`cm_sequence_policy_backup_20260720_01`
SELECT *
FROM `te_common`.`cm_sequence_policy`;

COMMIT;

-- 2. 백업 검증
SELECT
    (SELECT COUNT(*) FROM `te_common`.`cm_sequence_policy`) AS original_count,
    (SELECT COUNT(*) FROM `te_common`.`cm_sequence_policy_backup_20260720_01`) AS backup_count;

-- 3. ALTER TABLE 문 실행
ALTER TABLE `te_common`.`cm_sequence_policy`
    MODIFY COLUMN `policy_code` VARCHAR(99) NOT NULL COMMENT '시퀀스 초기화 정책 코드',
    MODIFY COLUMN `policy_name` VARCHAR(150) NOT NULL COMMENT '시퀀스 초기화 정책명',
    MODIFY COLUMN `date_format` VARCHAR(99) NOT NULL COMMENT '날짜 키 생성 형식';

-- 4. 변경 결과 확인
SELECT column_name, column_type
FROM information_schema.columns
WHERE table_schema = 'te_common'
  AND table_name = 'cm_sequence_policy'
  AND column_name IN (
      'policy_code',
      'policy_name',
      'date_format'
  )
ORDER BY ordinal_position;

SELECT COUNT(*) AS row_count FROM `te_common`.`cm_sequence_policy`;

/* PATCH 050 END */

/* =============================================================
PATCH 051 START
Database : te_common
Table    : cm_sequence_policy_definition
Columns  : 5
Rows     : 0
Backup   : cm_sequence_policy_definition_backup_20260720_01
============================================================= */

-- 1. 변경 전 백업
CREATE TABLE `te_common`.`cm_sequence_policy_definition_backup_20260720_01`
LIKE `te_common`.`cm_sequence_policy_definition`;

START TRANSACTION;

INSERT INTO `te_common`.`cm_sequence_policy_definition_backup_20260720_01`
SELECT *
FROM `te_common`.`cm_sequence_policy_definition`;

COMMIT;

-- 2. 백업 검증
SELECT
    (SELECT COUNT(*) FROM `te_common`.`cm_sequence_policy_definition`) AS original_count,
    (SELECT COUNT(*) FROM `te_common`.`cm_sequence_policy_definition_backup_20260720_01`) AS backup_count;

-- 3. ALTER TABLE 문 실행
ALTER TABLE `te_common`.`cm_sequence_policy_definition`
    MODIFY COLUMN `policy_code` VARCHAR(99) NOT NULL COMMENT '시퀀스 정책 코드',
    MODIFY COLUMN `policy_name` VARCHAR(150) NOT NULL COMMENT '시퀀스 정책명',
    MODIFY COLUMN `sequence_date_type` VARCHAR(99) NOT NULL COMMENT 'NO_RESET/YEARLY/MONTHLY/DAILY',
    MODIFY COLUMN `sequence_date_rule` VARCHAR(99) NOT NULL COMMENT '00000000/YYYY0000/YYYYMM00/YYYYMMDD',
    MODIFY COLUMN `code_description` VARCHAR(2000) NULL DEFAULT NULL COMMENT '설명';

-- 4. 변경 결과 확인
SELECT column_name, column_type
FROM information_schema.columns
WHERE table_schema = 'te_common'
  AND table_name = 'cm_sequence_policy_definition'
  AND column_name IN (
      'policy_code',
      'policy_name',
      'sequence_date_type',
      'sequence_date_rule',
      'code_description'
  )
ORDER BY ordinal_position;

SELECT COUNT(*) AS row_count FROM `te_common`.`cm_sequence_policy_definition`;

/* PATCH 051 END */

/* =============================================================
PATCH 052 START
Database : te_common
Table    : cm_sequence_rule
Columns  : 8
Rows     : 1
Backup   : cm_sequence_rule_backup_20260720_01
============================================================= */

-- 1. 변경 전 백업
CREATE TABLE `te_common`.`cm_sequence_rule_backup_20260720_01`
LIKE `te_common`.`cm_sequence_rule`;

START TRANSACTION;

INSERT INTO `te_common`.`cm_sequence_rule_backup_20260720_01`
SELECT *
FROM `te_common`.`cm_sequence_rule`;

COMMIT;

-- 2. 백업 검증
SELECT
    (SELECT COUNT(*) FROM `te_common`.`cm_sequence_rule`) AS original_count,
    (SELECT COUNT(*) FROM `te_common`.`cm_sequence_rule_backup_20260720_01`) AS backup_count;

-- 3. ALTER TABLE 문 실행
ALTER TABLE `te_common`.`cm_sequence_rule`
    MODIFY COLUMN `sequence_code` VARCHAR(99) NOT NULL COMMENT '시퀀스 코드',
    MODIFY COLUMN `sequence_name` VARCHAR(150) NOT NULL COMMENT '시퀀스명',
    MODIFY COLUMN `classification_code` VARCHAR(99) NULL DEFAULT NULL COMMENT '분류 코드',
    MODIFY COLUMN `domain_code` VARCHAR(99) NULL DEFAULT NULL COMMENT '도메인 코드',
    MODIFY COLUMN `work_type_code` VARCHAR(99) NULL DEFAULT NULL COMMENT '업무유형 코드',
    MODIFY COLUMN `policy_code` VARCHAR(99) NOT NULL COMMENT '초기화 정책 코드',
    MODIFY COLUMN `format_code` VARCHAR(99) NOT NULL COMMENT '포맷 코드',
    MODIFY COLUMN `prefix_code` VARCHAR(99) NULL DEFAULT NULL COMMENT 'Prefix 코드';

-- 4. 변경 결과 확인
SELECT column_name, column_type
FROM information_schema.columns
WHERE table_schema = 'te_common'
  AND table_name = 'cm_sequence_rule'
  AND column_name IN (
      'sequence_code',
      'sequence_name',
      'classification_code',
      'domain_code',
      'work_type_code',
      'policy_code',
      'format_code',
      'prefix_code'
  )
ORDER BY ordinal_position;

SELECT COUNT(*) AS row_count FROM `te_common`.`cm_sequence_rule`;

/* PATCH 052 END */

/* =============================================================
PATCH 053 START
Database : te_common
Table    : cm_storage_policy
Columns  : 2
Rows     : 6
Backup   : cm_storage_policy_backup_20260720_01
============================================================= */

-- 1. 변경 전 백업
CREATE TABLE `te_common`.`cm_storage_policy_backup_20260720_01`
LIKE `te_common`.`cm_storage_policy`;

START TRANSACTION;

INSERT INTO `te_common`.`cm_storage_policy_backup_20260720_01`
SELECT *
FROM `te_common`.`cm_storage_policy`;

COMMIT;

-- 2. 백업 검증
SELECT
    (SELECT COUNT(*) FROM `te_common`.`cm_storage_policy`) AS original_count,
    (SELECT COUNT(*) FROM `te_common`.`cm_storage_policy_backup_20260720_01`) AS backup_count;

-- 3. ALTER TABLE 문 실행
ALTER TABLE `te_common`.`cm_storage_policy`
    MODIFY COLUMN `data_type` VARCHAR(99) NOT NULL COMMENT '데이터유형',
    MODIFY COLUMN `repository_id` VARCHAR(99) NOT NULL COMMENT '저장소ID';

-- 4. 변경 결과 확인
SELECT column_name, column_type
FROM information_schema.columns
WHERE table_schema = 'te_common'
  AND table_name = 'cm_storage_policy'
  AND column_name IN (
      'data_type',
      'repository_id'
  )
ORDER BY ordinal_position;

SELECT COUNT(*) AS row_count FROM `te_common`.`cm_storage_policy`;

/* PATCH 053 END */

/* =============================================================
PATCH 054 START
Database : te_common
Table    : cm_storage_repository
Columns  : 5
Rows     : 7
Backup   : cm_storage_repository_backup_20260720_01
============================================================= */

-- 1. 변경 전 백업
CREATE TABLE `te_common`.`cm_storage_repository_backup_20260720_01`
LIKE `te_common`.`cm_storage_repository`;

START TRANSACTION;

INSERT INTO `te_common`.`cm_storage_repository_backup_20260720_01`
SELECT *
FROM `te_common`.`cm_storage_repository`;

COMMIT;

-- 2. 백업 검증
SELECT
    (SELECT COUNT(*) FROM `te_common`.`cm_storage_repository`) AS original_count,
    (SELECT COUNT(*) FROM `te_common`.`cm_storage_repository_backup_20260720_01`) AS backup_count;

-- 3. ALTER TABLE 문 실행
ALTER TABLE `te_common`.`cm_storage_repository`
    MODIFY COLUMN `repository_id` VARCHAR(99) NOT NULL COMMENT '저장소ID',
    MODIFY COLUMN `repository_name` VARCHAR(150) NOT NULL COMMENT '저장소명',
    MODIFY COLUMN `repository_type` VARCHAR(99) NOT NULL COMMENT '저장소유형',
    MODIFY COLUMN `database_name` VARCHAR(150) NULL DEFAULT NULL COMMENT 'DB명',
    MODIFY COLUMN `connection_host` VARCHAR(500) NULL DEFAULT NULL COMMENT '접속주소';

-- 4. 변경 결과 확인
SELECT column_name, column_type
FROM information_schema.columns
WHERE table_schema = 'te_common'
  AND table_name = 'cm_storage_repository'
  AND column_name IN (
      'repository_id',
      'repository_name',
      'repository_type',
      'database_name',
      'connection_host'
  )
ORDER BY ordinal_position;

SELECT COUNT(*) AS row_count FROM `te_common`.`cm_storage_repository`;

/* PATCH 054 END */

/* =============================================================
PATCH 055 START
Database : te_common
Table    : cm_verified_sql_query
Columns  : 17
Rows     : 5
Backup   : cm_verified_sql_query_backup_20260720_01
============================================================= */

-- 1. 변경 전 백업
CREATE TABLE `te_common`.`cm_verified_sql_query_backup_20260720_01`
LIKE `te_common`.`cm_verified_sql_query`;

START TRANSACTION;

INSERT INTO `te_common`.`cm_verified_sql_query_backup_20260720_01`
SELECT *
FROM `te_common`.`cm_verified_sql_query`;

COMMIT;

-- 2. 백업 검증
SELECT
    (SELECT COUNT(*) FROM `te_common`.`cm_verified_sql_query`) AS original_count,
    (SELECT COUNT(*) FROM `te_common`.`cm_verified_sql_query_backup_20260720_01`) AS backup_count;

-- 3. ALTER TABLE 문 실행
ALTER TABLE `te_common`.`cm_verified_sql_query`
    MODIFY COLUMN `query_id` VARCHAR(99) NOT NULL,
    MODIFY COLUMN `query_name` VARCHAR(150) NOT NULL,
    MODIFY COLUMN `crud_type` VARCHAR(99) NOT NULL,
    MODIFY COLUMN `sql_text` TEXT NOT NULL,
    MODIFY COLUMN `verified_by` VARCHAR(99) NULL DEFAULT NULL,
    MODIFY COLUMN `created_user_id` VARCHAR(99) NULL DEFAULT NULL COMMENT '생성 사용자 ID',
    MODIFY COLUMN `created_user_login_id` VARCHAR(99) NULL DEFAULT NULL COMMENT '생성 사용자 로그인 ID',
    MODIFY COLUMN `created_ip_address` VARCHAR(99) NULL DEFAULT NULL COMMENT '생성 IP 주소',
    MODIFY COLUMN `created_program_id` VARCHAR(99) NULL DEFAULT NULL COMMENT '생성 프로그램 ID',
    MODIFY COLUMN `updated_user_id` VARCHAR(99) NULL DEFAULT NULL COMMENT '수정 사용자 ID',
    MODIFY COLUMN `updated_user_login_id` VARCHAR(99) NULL DEFAULT NULL COMMENT '수정 사용자 로그인 ID',
    MODIFY COLUMN `updated_ip_address` VARCHAR(99) NULL DEFAULT NULL COMMENT '수정 IP 주소',
    MODIFY COLUMN `updated_program_id` VARCHAR(99) NULL DEFAULT NULL COMMENT '수정 프로그램 ID',
    MODIFY COLUMN `deleted_user_id` VARCHAR(99) NULL DEFAULT NULL COMMENT '삭제 사용자 ID',
    MODIFY COLUMN `deleted_user_login_id` VARCHAR(99) NULL DEFAULT NULL COMMENT '삭제 사용자 로그인 ID',
    MODIFY COLUMN `deleted_ip_address` VARCHAR(99) NULL DEFAULT NULL COMMENT '삭제 IP 주소',
    MODIFY COLUMN `deleted_program_id` VARCHAR(99) NULL DEFAULT NULL COMMENT '삭제 프로그램 ID';

-- 4. 변경 결과 확인
SELECT column_name, column_type
FROM information_schema.columns
WHERE table_schema = 'te_common'
  AND table_name = 'cm_verified_sql_query'
  AND column_name IN (
      'query_id',
      'query_name',
      'crud_type',
      'sql_text',
      'verified_by',
      'created_user_id',
      'created_user_login_id',
      'created_ip_address',
      'created_program_id',
      'updated_user_id',
      'updated_user_login_id',
      'updated_ip_address',
      'updated_program_id',
      'deleted_user_id',
      'deleted_user_login_id',
      'deleted_ip_address',
      'deleted_program_id'
  )
ORDER BY ordinal_position;

SELECT COUNT(*) AS row_count FROM `te_common`.`cm_verified_sql_query`;

/* PATCH 055 END */

/* =============================================================
PATCH 056 START
Database : te_common
Table    : ev_evidence
Columns  : 12
Rows     : 1
Backup   : ev_evidence_backup_20260720_01
============================================================= */

-- 1. 변경 전 백업
CREATE TABLE `te_common`.`ev_evidence_backup_20260720_01`
LIKE `te_common`.`ev_evidence`;

START TRANSACTION;

INSERT INTO `te_common`.`ev_evidence_backup_20260720_01`
SELECT *
FROM `te_common`.`ev_evidence`;

COMMIT;

-- 2. 백업 검증
SELECT
    (SELECT COUNT(*) FROM `te_common`.`ev_evidence`) AS original_count,
    (SELECT COUNT(*) FROM `te_common`.`ev_evidence_backup_20260720_01`) AS backup_count;

-- 3. ALTER TABLE 문 실행
ALTER TABLE `te_common`.`ev_evidence`
    MODIFY COLUMN `evidence_id` VARCHAR(99) NOT NULL COMMENT '근거 ID',
    MODIFY COLUMN `evidence_code` VARCHAR(99) NOT NULL COMMENT '근거 코드',
    MODIFY COLUMN `evidence_name` VARCHAR(150) NOT NULL COMMENT '근거명',
    MODIFY COLUMN `evidence_level_code` VARCHAR(99) NOT NULL COMMENT '근거수준 A/B/C/D',
    MODIFY COLUMN `evidence_category_code` VARCHAR(99) NOT NULL COMMENT '근거 분류 코드',
    MODIFY COLUMN `organization_name` VARCHAR(150) NULL DEFAULT NULL COMMENT '기관명',
    MODIFY COLUMN `source_title` VARCHAR(500) NULL DEFAULT NULL COMMENT '출처 제목',
    MODIFY COLUMN `published_dt` DATETIME NULL DEFAULT NULL COMMENT '발행일',
    MODIFY COLUMN `effective_from_dt` DATETIME NULL DEFAULT NULL COMMENT '적용 시작일',
    MODIFY COLUMN `effective_to_dt` DATETIME NULL DEFAULT NULL COMMENT '적용 종료일',
    MODIFY COLUMN `summary` VARCHAR(2000) NULL DEFAULT NULL COMMENT '요약',
    MODIFY COLUMN `remark` VARCHAR(2000) NULL DEFAULT NULL COMMENT '비고';

-- 4. 변경 결과 확인
SELECT column_name, column_type
FROM information_schema.columns
WHERE table_schema = 'te_common'
  AND table_name = 'ev_evidence'
  AND column_name IN (
      'evidence_id',
      'evidence_code',
      'evidence_name',
      'evidence_level_code',
      'evidence_category_code',
      'organization_name',
      'source_title',
      'published_dt',
      'effective_from_dt',
      'effective_to_dt',
      'summary',
      'remark'
  )
ORDER BY ordinal_position;

SELECT COUNT(*) AS row_count FROM `te_common`.`ev_evidence`;

/* PATCH 056 END */

/* =============================================================
PATCH 057 START
Database : te_common
Table    : ev_evidence_reference
Columns  : 12
Rows     : 1
Backup   : ev_evidence_reference_backup_20260720_01
============================================================= */

-- 1. 변경 전 백업
CREATE TABLE `te_common`.`ev_evidence_reference_backup_20260720_01`
LIKE `te_common`.`ev_evidence_reference`;

START TRANSACTION;

INSERT INTO `te_common`.`ev_evidence_reference_backup_20260720_01`
SELECT *
FROM `te_common`.`ev_evidence_reference`;

COMMIT;

-- 2. 백업 검증
SELECT
    (SELECT COUNT(*) FROM `te_common`.`ev_evidence_reference`) AS original_count,
    (SELECT COUNT(*) FROM `te_common`.`ev_evidence_reference_backup_20260720_01`) AS backup_count;

-- 3. ALTER TABLE 문 실행
ALTER TABLE `te_common`.`ev_evidence_reference`
    MODIFY COLUMN `reference_id` VARCHAR(99) NOT NULL COMMENT '근거 참조 ID',
    MODIFY COLUMN `evidence_id` VARCHAR(99) NOT NULL COMMENT '근거 ID',
    MODIFY COLUMN `reference_type_code` VARCHAR(99) NOT NULL COMMENT '참조 유형 코드',
    MODIFY COLUMN `reference_title` VARCHAR(500) NOT NULL COMMENT '참조 제목',
    MODIFY COLUMN `organization_name` VARCHAR(150) NULL DEFAULT NULL COMMENT '기관명',
    MODIFY COLUMN `author_name` VARCHAR(150) NULL DEFAULT NULL COMMENT '저자명',
    MODIFY COLUMN `journal_name` VARCHAR(150) NULL DEFAULT NULL COMMENT '학술지명',
    MODIFY COLUMN `doi` VARCHAR(500) NULL DEFAULT NULL COMMENT 'DOI',
    MODIFY COLUMN `pmid` VARCHAR(99) NULL DEFAULT NULL COMMENT 'PubMed ID',
    MODIFY COLUMN `reference_url` VARCHAR(2000) NULL DEFAULT NULL COMMENT '참조 URL',
    MODIFY COLUMN `published_dt` DATETIME NULL DEFAULT NULL COMMENT '발행일',
    MODIFY COLUMN `remark` VARCHAR(2000) NULL DEFAULT NULL COMMENT '비고';

-- 4. 변경 결과 확인
SELECT column_name, column_type
FROM information_schema.columns
WHERE table_schema = 'te_common'
  AND table_name = 'ev_evidence_reference'
  AND column_name IN (
      'reference_id',
      'evidence_id',
      'reference_type_code',
      'reference_title',
      'organization_name',
      'author_name',
      'journal_name',
      'doi',
      'pmid',
      'reference_url',
      'published_dt',
      'remark'
  )
ORDER BY ordinal_position;

SELECT COUNT(*) AS row_count FROM `te_common`.`ev_evidence_reference`;

/* PATCH 057 END */

/* =============================================================
PATCH 058 START
Database : te_common
Table    : ev_evidence_version
Columns  : 6
Rows     : 1
Backup   : ev_evidence_version_backup_20260720_01
============================================================= */

-- 1. 변경 전 백업
CREATE TABLE `te_common`.`ev_evidence_version_backup_20260720_01`
LIKE `te_common`.`ev_evidence_version`;

START TRANSACTION;

INSERT INTO `te_common`.`ev_evidence_version_backup_20260720_01`
SELECT *
FROM `te_common`.`ev_evidence_version`;

COMMIT;

-- 2. 백업 검증
SELECT
    (SELECT COUNT(*) FROM `te_common`.`ev_evidence_version`) AS original_count,
    (SELECT COUNT(*) FROM `te_common`.`ev_evidence_version_backup_20260720_01`) AS backup_count;

-- 3. ALTER TABLE 문 실행
ALTER TABLE `te_common`.`ev_evidence_version`
    MODIFY COLUMN `evidence_version_id` VARCHAR(99) NOT NULL COMMENT '근거 버전 ID',
    MODIFY COLUMN `evidence_id` VARCHAR(99) NOT NULL COMMENT '근거 ID',
    MODIFY COLUMN `effective_from_dt` DATETIME NOT NULL COMMENT '적용 시작일',
    MODIFY COLUMN `effective_to_dt` DATETIME NULL DEFAULT NULL COMMENT '적용 종료일',
    MODIFY COLUMN `change_summary` VARCHAR(2000) NULL DEFAULT NULL COMMENT '변경 요약',
    MODIFY COLUMN `remark` VARCHAR(2000) NULL DEFAULT NULL COMMENT '비고';

-- 4. 변경 결과 확인
SELECT column_name, column_type
FROM information_schema.columns
WHERE table_schema = 'te_common'
  AND table_name = 'ev_evidence_version'
  AND column_name IN (
      'evidence_version_id',
      'evidence_id',
      'effective_from_dt',
      'effective_to_dt',
      'change_summary',
      'remark'
  )
ORDER BY ordinal_position;

SELECT COUNT(*) AS row_count FROM `te_common`.`ev_evidence_version`;

/* PATCH 058 END */

/* =============================================================
PATCH 059 START
Database : te_common
Table    : md_relation
Columns  : 2
Rows     : 0
Backup   : md_relation_backup_20260720_01
============================================================= */

-- 1. 변경 전 백업
CREATE TABLE `te_common`.`md_relation_backup_20260720_01`
LIKE `te_common`.`md_relation`;

START TRANSACTION;

INSERT INTO `te_common`.`md_relation_backup_20260720_01`
SELECT *
FROM `te_common`.`md_relation`;

COMMIT;

-- 2. 백업 검증
SELECT
    (SELECT COUNT(*) FROM `te_common`.`md_relation`) AS original_count,
    (SELECT COUNT(*) FROM `te_common`.`md_relation_backup_20260720_01`) AS backup_count;

-- 3. ALTER TABLE 문 실행
ALTER TABLE `te_common`.`md_relation`
    MODIFY COLUMN `direction_code` VARCHAR(99) NOT NULL DEFAULT '''UNI''',
    MODIFY COLUMN `cardinality_code` VARCHAR(99) NOT NULL DEFAULT '''N:N''';

-- 4. 변경 결과 확인
SELECT column_name, column_type
FROM information_schema.columns
WHERE table_schema = 'te_common'
  AND table_name = 'md_relation'
  AND column_name IN (
      'direction_code',
      'cardinality_code'
  )
ORDER BY ordinal_position;

SELECT COUNT(*) AS row_count FROM `te_common`.`md_relation`;

/* PATCH 059 END */

/* =============================================================
PATCH 060 START
Database : te_common
Table    : rl_rule
Columns  : 6
Rows     : 2
Backup   : rl_rule_backup_20260720_01
============================================================= */

-- 1. 변경 전 백업
CREATE TABLE `te_common`.`rl_rule_backup_20260720_01`
LIKE `te_common`.`rl_rule`;

START TRANSACTION;

INSERT INTO `te_common`.`rl_rule_backup_20260720_01`
SELECT *
FROM `te_common`.`rl_rule`;

COMMIT;

-- 2. 백업 검증
SELECT
    (SELECT COUNT(*) FROM `te_common`.`rl_rule`) AS original_count,
    (SELECT COUNT(*) FROM `te_common`.`rl_rule_backup_20260720_01`) AS backup_count;

-- 3. ALTER TABLE 문 실행
ALTER TABLE `te_common`.`rl_rule`
    MODIFY COLUMN `rule_id` VARCHAR(99) NOT NULL COMMENT '규칙 ID',
    MODIFY COLUMN `rule_code` VARCHAR(99) NOT NULL COMMENT '규칙 코드',
    MODIFY COLUMN `rule_name` VARCHAR(150) NOT NULL COMMENT '규칙명',
    MODIFY COLUMN `rule_type_code` VARCHAR(99) NOT NULL COMMENT '규칙 유형 코드',
    MODIFY COLUMN `rule_group_code` VARCHAR(99) NULL DEFAULT NULL COMMENT '규칙 그룹 코드',
    MODIFY COLUMN `remark` VARCHAR(2000) NULL DEFAULT NULL COMMENT '비고';

-- 4. 변경 결과 확인
SELECT column_name, column_type
FROM information_schema.columns
WHERE table_schema = 'te_common'
  AND table_name = 'rl_rule'
  AND column_name IN (
      'rule_id',
      'rule_code',
      'rule_name',
      'rule_type_code',
      'rule_group_code',
      'remark'
  )
ORDER BY ordinal_position;

SELECT COUNT(*) AS row_count FROM `te_common`.`rl_rule`;

/* PATCH 060 END */

/* =============================================================
PATCH 061 START
Database : te_common
Table    : rl_rule_action
Columns  : 5
Rows     : 3
Backup   : rl_rule_action_backup_20260720_01
============================================================= */

-- 1. 변경 전 백업
CREATE TABLE `te_common`.`rl_rule_action_backup_20260720_01`
LIKE `te_common`.`rl_rule_action`;

START TRANSACTION;

INSERT INTO `te_common`.`rl_rule_action_backup_20260720_01`
SELECT *
FROM `te_common`.`rl_rule_action`;

COMMIT;

-- 2. 백업 검증
SELECT
    (SELECT COUNT(*) FROM `te_common`.`rl_rule_action`) AS original_count,
    (SELECT COUNT(*) FROM `te_common`.`rl_rule_action_backup_20260720_01`) AS backup_count;

-- 3. ALTER TABLE 문 실행
ALTER TABLE `te_common`.`rl_rule_action`
    MODIFY COLUMN `rule_action_id` VARCHAR(99) NOT NULL COMMENT '규칙 실행 ID',
    MODIFY COLUMN `rule_id` VARCHAR(99) NOT NULL COMMENT '규칙 ID',
    MODIFY COLUMN `action_type_code` VARCHAR(99) NOT NULL COMMENT '실행 유형 코드',
    MODIFY COLUMN `action_value` VARCHAR(2000) NULL DEFAULT NULL COMMENT '실행 값',
    MODIFY COLUMN `remark` VARCHAR(2000) NULL DEFAULT NULL COMMENT '비고';

-- 4. 변경 결과 확인
SELECT column_name, column_type
FROM information_schema.columns
WHERE table_schema = 'te_common'
  AND table_name = 'rl_rule_action'
  AND column_name IN (
      'rule_action_id',
      'rule_id',
      'action_type_code',
      'action_value',
      'remark'
  )
ORDER BY ordinal_position;

SELECT COUNT(*) AS row_count FROM `te_common`.`rl_rule_action`;

/* PATCH 061 END */

/* =============================================================
PATCH 062 START
Database : te_common
Table    : rl_rule_condition
Columns  : 7
Rows     : 1
Backup   : rl_rule_condition_backup_20260720_01
============================================================= */

-- 1. 변경 전 백업
CREATE TABLE `te_common`.`rl_rule_condition_backup_20260720_01`
LIKE `te_common`.`rl_rule_condition`;

START TRANSACTION;

INSERT INTO `te_common`.`rl_rule_condition_backup_20260720_01`
SELECT *
FROM `te_common`.`rl_rule_condition`;

COMMIT;

-- 2. 백업 검증
SELECT
    (SELECT COUNT(*) FROM `te_common`.`rl_rule_condition`) AS original_count,
    (SELECT COUNT(*) FROM `te_common`.`rl_rule_condition_backup_20260720_01`) AS backup_count;

-- 3. ALTER TABLE 문 실행
ALTER TABLE `te_common`.`rl_rule_condition`
    MODIFY COLUMN `condition_id` VARCHAR(99) NOT NULL COMMENT '규칙 조건 ID',
    MODIFY COLUMN `rule_id` VARCHAR(99) NOT NULL COMMENT '규칙 ID',
    MODIFY COLUMN `field_code` VARCHAR(99) NOT NULL COMMENT '대상 필드 코드',
    MODIFY COLUMN `operator_code` VARCHAR(99) NOT NULL COMMENT '연산자 코드',
    MODIFY COLUMN `condition_value` VARCHAR(2000) NOT NULL COMMENT '조건 값',
    MODIFY COLUMN `logical_operator_code` VARCHAR(99) NULL DEFAULT NULL COMMENT '논리 연산자 코드',
    MODIFY COLUMN `remark` VARCHAR(2000) NULL DEFAULT NULL COMMENT '비고';

-- 4. 변경 결과 확인
SELECT column_name, column_type
FROM information_schema.columns
WHERE table_schema = 'te_common'
  AND table_name = 'rl_rule_condition'
  AND column_name IN (
      'condition_id',
      'rule_id',
      'field_code',
      'operator_code',
      'condition_value',
      'logical_operator_code',
      'remark'
  )
ORDER BY ordinal_position;

SELECT COUNT(*) AS row_count FROM `te_common`.`rl_rule_condition`;

/* PATCH 062 END */

/* =============================================================
PATCH 063 START
Database : te_common
Table    : rl_rule_evidence
Columns  : 4
Rows     : 1
Backup   : rl_rule_evidence_backup_20260720_01
============================================================= */

-- 1. 변경 전 백업
CREATE TABLE `te_common`.`rl_rule_evidence_backup_20260720_01`
LIKE `te_common`.`rl_rule_evidence`;

START TRANSACTION;

INSERT INTO `te_common`.`rl_rule_evidence_backup_20260720_01`
SELECT *
FROM `te_common`.`rl_rule_evidence`;

COMMIT;

-- 2. 백업 검증
SELECT
    (SELECT COUNT(*) FROM `te_common`.`rl_rule_evidence`) AS original_count,
    (SELECT COUNT(*) FROM `te_common`.`rl_rule_evidence_backup_20260720_01`) AS backup_count;

-- 3. ALTER TABLE 문 실행
ALTER TABLE `te_common`.`rl_rule_evidence`
    MODIFY COLUMN `rule_evidence_id` VARCHAR(99) NOT NULL COMMENT '규칙 근거 연결 ID',
    MODIFY COLUMN `rule_id` VARCHAR(99) NOT NULL COMMENT '규칙 ID',
    MODIFY COLUMN `evidence_id` VARCHAR(99) NOT NULL COMMENT '근거 ID',
    MODIFY COLUMN `remark` VARCHAR(2000) NULL DEFAULT NULL COMMENT '비고';

-- 4. 변경 결과 확인
SELECT column_name, column_type
FROM information_schema.columns
WHERE table_schema = 'te_common'
  AND table_name = 'rl_rule_evidence'
  AND column_name IN (
      'rule_evidence_id',
      'rule_id',
      'evidence_id',
      'remark'
  )
ORDER BY ordinal_position;

SELECT COUNT(*) AS row_count FROM `te_common`.`rl_rule_evidence`;

/* PATCH 063 END */

/* =============================================================
PATCH 064 START
Database : te_common
Table    : sp_policy_rule_candidate
Columns  : 6
Rows     : 9
Backup   : sp_policy_rule_candidate_backup_20260720_01
============================================================= */

-- 1. 변경 전 백업
CREATE TABLE `te_common`.`sp_policy_rule_candidate_backup_20260720_01`
LIKE `te_common`.`sp_policy_rule_candidate`;

START TRANSACTION;

INSERT INTO `te_common`.`sp_policy_rule_candidate_backup_20260720_01`
SELECT *
FROM `te_common`.`sp_policy_rule_candidate`;

COMMIT;

-- 2. 백업 검증
SELECT
    (SELECT COUNT(*) FROM `te_common`.`sp_policy_rule_candidate`) AS original_count,
    (SELECT COUNT(*) FROM `te_common`.`sp_policy_rule_candidate_backup_20260720_01`) AS backup_count;

-- 3. ALTER TABLE 문 실행
ALTER TABLE `te_common`.`sp_policy_rule_candidate`
    MODIFY COLUMN `policy_id` VARCHAR(99) NULL DEFAULT NULL,
    MODIFY COLUMN `source_document_name` VARCHAR(150) NULL DEFAULT NULL,
    MODIFY COLUMN `matched_keyword_text` TEXT NULL DEFAULT NULL,
    MODIFY COLUMN `rule_candidate_category_code` VARCHAR(99) NULL DEFAULT NULL,
    MODIFY COLUMN `confidence_score` DECIMAL(10,4) NULL DEFAULT 0.00,
    MODIFY COLUMN `change_reason` VARCHAR(2000) NULL DEFAULT NULL;

-- 4. 변경 결과 확인
SELECT column_name, column_type
FROM information_schema.columns
WHERE table_schema = 'te_common'
  AND table_name = 'sp_policy_rule_candidate'
  AND column_name IN (
      'policy_id',
      'source_document_name',
      'matched_keyword_text',
      'rule_candidate_category_code',
      'confidence_score',
      'change_reason'
  )
ORDER BY ordinal_position;

SELECT COUNT(*) AS row_count FROM `te_common`.`sp_policy_rule_candidate`;

/* PATCH 064 END */

/* =============================================================
PATCH 065 START
Database : te_common
Table    : sp_policy_rule_keyword
Columns  : 4
Rows     : 24
Backup   : sp_policy_rule_keyword_backup_20260720_01
============================================================= */

-- 1. 변경 전 백업
CREATE TABLE `te_common`.`sp_policy_rule_keyword_backup_20260720_01`
LIKE `te_common`.`sp_policy_rule_keyword`;

START TRANSACTION;

INSERT INTO `te_common`.`sp_policy_rule_keyword_backup_20260720_01`
SELECT *
FROM `te_common`.`sp_policy_rule_keyword`;

COMMIT;

-- 2. 백업 검증
SELECT
    (SELECT COUNT(*) FROM `te_common`.`sp_policy_rule_keyword`) AS original_count,
    (SELECT COUNT(*) FROM `te_common`.`sp_policy_rule_keyword_backup_20260720_01`) AS backup_count;

-- 3. ALTER TABLE 문 실행
ALTER TABLE `te_common`.`sp_policy_rule_keyword`
    MODIFY COLUMN `rule_keyword_text` TEXT NOT NULL,
    MODIFY COLUMN `rule_keyword_category_code` VARCHAR(99) NOT NULL,
    MODIFY COLUMN `rule_keyword_description` VARCHAR(2000) NULL DEFAULT NULL,
    MODIFY COLUMN `change_reason` VARCHAR(2000) NULL DEFAULT NULL;

-- 4. 변경 결과 확인
SELECT column_name, column_type
FROM information_schema.columns
WHERE table_schema = 'te_common'
  AND table_name = 'sp_policy_rule_keyword'
  AND column_name IN (
      'rule_keyword_text',
      'rule_keyword_category_code',
      'rule_keyword_description',
      'change_reason'
  )
ORDER BY ordinal_position;

SELECT COUNT(*) AS row_count FROM `te_common`.`sp_policy_rule_keyword`;

/* PATCH 065 END */

/* =============================================================
PATCH 066 START
Database : te_common
Table    : sql_guard_execution_log
Columns  : 3
Rows     : 0
Backup   : sql_guard_execution_log_backup_20260720_01
============================================================= */

-- 1. 변경 전 백업
CREATE TABLE `te_common`.`sql_guard_execution_log_backup_20260720_01`
LIKE `te_common`.`sql_guard_execution_log`;

START TRANSACTION;

INSERT INTO `te_common`.`sql_guard_execution_log_backup_20260720_01`
SELECT *
FROM `te_common`.`sql_guard_execution_log`;

COMMIT;

-- 2. 백업 검증
SELECT
    (SELECT COUNT(*) FROM `te_common`.`sql_guard_execution_log`) AS original_count,
    (SELECT COUNT(*) FROM `te_common`.`sql_guard_execution_log_backup_20260720_01`) AS backup_count;

-- 3. ALTER TABLE 문 실행
ALTER TABLE `te_common`.`sql_guard_execution_log`
    MODIFY COLUMN `user_id` VARCHAR(99) NOT NULL,
    MODIFY COLUMN `query_id` VARCHAR(99) NOT NULL,
    MODIFY COLUMN `crud_type` VARCHAR(99) NOT NULL;

-- 4. 변경 결과 확인
SELECT column_name, column_type
FROM information_schema.columns
WHERE table_schema = 'te_common'
  AND table_name = 'sql_guard_execution_log'
  AND column_name IN (
      'user_id',
      'query_id',
      'crud_type'
  )
ORDER BY ordinal_position;

SELECT COUNT(*) AS row_count FROM `te_common`.`sql_guard_execution_log`;

/* PATCH 066 END */

/* =============================================================
PATCH 067 START
Database : te_common
Table    : sql_guard_verification_log
Columns  : 2
Rows     : 0
Backup   : sql_guard_verification_log_backup_20260720_01
============================================================= */

-- 1. 변경 전 백업
CREATE TABLE `te_common`.`sql_guard_verification_log_backup_20260720_01`
LIKE `te_common`.`sql_guard_verification_log`;

START TRANSACTION;

INSERT INTO `te_common`.`sql_guard_verification_log_backup_20260720_01`
SELECT *
FROM `te_common`.`sql_guard_verification_log`;

COMMIT;

-- 2. 백업 검증
SELECT
    (SELECT COUNT(*) FROM `te_common`.`sql_guard_verification_log`) AS original_count,
    (SELECT COUNT(*) FROM `te_common`.`sql_guard_verification_log_backup_20260720_01`) AS backup_count;

-- 3. ALTER TABLE 문 실행
ALTER TABLE `te_common`.`sql_guard_verification_log`
    MODIFY COLUMN `query_id` VARCHAR(99) NULL DEFAULT NULL,
    MODIFY COLUMN `check_step` VARCHAR(99) NOT NULL;

-- 4. 변경 결과 확인
SELECT column_name, column_type
FROM information_schema.columns
WHERE table_schema = 'te_common'
  AND table_name = 'sql_guard_verification_log'
  AND column_name IN (
      'query_id',
      'check_step'
  )
ORDER BY ordinal_position;

SELECT COUNT(*) AS row_count FROM `te_common`.`sql_guard_verification_log`;

/* PATCH 067 END */

/* =============================================================
PATCH 068 START
Database : te_common
Table    : system_menu
Columns  : 2
Rows     : 1
Backup   : system_menu_backup_20260720_01
============================================================= */

-- 1. 변경 전 백업
CREATE TABLE `te_common`.`system_menu_backup_20260720_01`
LIKE `te_common`.`system_menu`;

START TRANSACTION;

INSERT INTO `te_common`.`system_menu_backup_20260720_01`
SELECT *
FROM `te_common`.`system_menu`;

COMMIT;

-- 2. 백업 검증
SELECT
    (SELECT COUNT(*) FROM `te_common`.`system_menu`) AS original_count,
    (SELECT COUNT(*) FROM `te_common`.`system_menu_backup_20260720_01`) AS backup_count;

-- 3. ALTER TABLE 문 실행
ALTER TABLE `te_common`.`system_menu`
    MODIFY COLUMN `menu_name` VARCHAR(150) NOT NULL,
    MODIFY COLUMN `menu_url` VARCHAR(2000) NULL DEFAULT NULL;

-- 4. 변경 결과 확인
SELECT column_name, column_type
FROM information_schema.columns
WHERE table_schema = 'te_common'
  AND table_name = 'system_menu'
  AND column_name IN (
      'menu_name',
      'menu_url'
  )
ORDER BY ordinal_position;

SELECT COUNT(*) AS row_count FROM `te_common`.`system_menu`;

/* PATCH 068 END */

/* =============================================================
PATCH 069 START
Database : te_common
Table    : system_menu_button
Columns  : 3
Rows     : 4
Backup   : system_menu_button_backup_20260720_01
============================================================= */

-- 1. 변경 전 백업
CREATE TABLE `te_common`.`system_menu_button_backup_20260720_01`
LIKE `te_common`.`system_menu_button`;

START TRANSACTION;

INSERT INTO `te_common`.`system_menu_button_backup_20260720_01`
SELECT *
FROM `te_common`.`system_menu_button`;

COMMIT;

-- 2. 백업 검증
SELECT
    (SELECT COUNT(*) FROM `te_common`.`system_menu_button`) AS original_count,
    (SELECT COUNT(*) FROM `te_common`.`system_menu_button_backup_20260720_01`) AS backup_count;

-- 3. ALTER TABLE 문 실행
ALTER TABLE `te_common`.`system_menu_button`
    MODIFY COLUMN `button_name` VARCHAR(150) NOT NULL,
    MODIFY COLUMN `crud_type` VARCHAR(99) NOT NULL,
    MODIFY COLUMN `query_id` VARCHAR(99) NOT NULL;

-- 4. 변경 결과 확인
SELECT column_name, column_type
FROM information_schema.columns
WHERE table_schema = 'te_common'
  AND table_name = 'system_menu_button'
  AND column_name IN (
      'button_name',
      'crud_type',
      'query_id'
  )
ORDER BY ordinal_position;

SELECT COUNT(*) AS row_count FROM `te_common`.`system_menu_button`;

/* PATCH 069 END */

SET FOREIGN_KEY_CHECKS = 1;

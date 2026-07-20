/*
File Name : story_platform_direct_type_maintenance_20260720.sql
Purpose   : One-time, explicitly hardcoded STORY_PLATFORM direct type maintenance.
Scope     : 21 approved widening conversions only.
Excluded  : _by, _id, _code, _ip, _name; semantic/high-risk conversions.
Safety    : No dynamic SQL. Original NULL, DEFAULT, COMMENT and other attributes are preserved.
*/

SET NAMES utf8mb4;

SELECT 'BEFORE' AS verification_step, table_name, column_name, column_type
FROM information_schema.columns
WHERE table_schema = 'te_story_platform'
  AND (table_name, column_name) IN
(
    ('sp_attribute', 'data_type'),
    ('sp_attribute', 'default_value'),
    ('sp_attribute', 'attribute_comment'),
    ('sp_business', 'business_description'),
    ('sp_domain', 'domain_description'),
    ('sp_entity', 'entity_comment'),
    ('sp_erd', 'erd_description'),
    ('sp_execution_history', 'generated_identifier'),
    ('sp_execution_history', 'repository_status'),
    ('sp_execution_history', 'mongodb_status'),
    ('sp_execution_history', 'execution_status'),
    ('sp_execution_history', 'history_status'),
    ('sp_identifier_blueprint', 'remark'),
    ('sp_impact_analysis_result', 'change_target_text'),
    ('sp_impact_analysis_result', 'affected_file_path'),
    ('sp_knowledge_hold', 'change_reason'),
    ('sp_knowledge_relationship_hold', 'change_reason'),
    ('sp_knowledge_type_hold', 'change_reason'),
    ('sp_metadata', 'metadata_value'),
    ('sp_object', 'target_identifier_field'),
    ('sp_object_lifecycle', 'lifecycle_reason')
)
ORDER BY table_name, ordinal_position;

ALTER TABLE `te_story_platform`.`sp_attribute`
    MODIFY COLUMN `data_type` VARCHAR(99) NOT NULL COMMENT 'Data Type. Attribute의 데이터 형식을 정의하여 Database, API, UI, Generator의 생성 기준으로 사용한다.',
    MODIFY COLUMN `default_value` VARCHAR(2000) DEFAULT NULL COMMENT 'Default Value. Attribute의 기본값을 정의하여 Database Default와 Generator 초기값 생성 기준으로 사용한다.',
    MODIFY COLUMN `attribute_comment` VARCHAR(2000) DEFAULT NULL COMMENT 'Attribute Comment. Attribute의 목적, 의미, 관리 범위를 설명하고 Data Dictionary와 문서 생성의 원천으로 사용한다.';

ALTER TABLE `te_story_platform`.`sp_business`
    MODIFY COLUMN `business_description` VARCHAR(2000) DEFAULT NULL COMMENT 'Business Description';

ALTER TABLE `te_story_platform`.`sp_domain`
    MODIFY COLUMN `domain_description` VARCHAR(2000) DEFAULT NULL COMMENT 'Domain Description';

ALTER TABLE `te_story_platform`.`sp_entity`
    MODIFY COLUMN `entity_comment` VARCHAR(2000) DEFAULT NULL COMMENT 'Entity Comment. Entity의 목적, 의미, 관리 범위를 설명하고 Data Dictionary와 문서 생성의 원천으로 사용한다.';

ALTER TABLE `te_story_platform`.`sp_erd`
    MODIFY COLUMN `erd_description` VARCHAR(2000) DEFAULT NULL COMMENT 'ERD Description';

ALTER TABLE `te_story_platform`.`sp_execution_history`
    MODIFY COLUMN `generated_identifier` VARCHAR(99) DEFAULT NULL,
    MODIFY COLUMN `repository_status` VARCHAR(99) DEFAULT NULL,
    MODIFY COLUMN `mongodb_status` VARCHAR(99) DEFAULT NULL,
    MODIFY COLUMN `execution_status` VARCHAR(99) NOT NULL,
    MODIFY COLUMN `history_status` VARCHAR(99) NOT NULL;

ALTER TABLE `te_story_platform`.`sp_identifier_blueprint`
    MODIFY COLUMN `remark` VARCHAR(2000) DEFAULT NULL COMMENT 'Remark';

ALTER TABLE `te_story_platform`.`sp_impact_analysis_result`
    MODIFY COLUMN `change_target_text` TEXT NOT NULL,
    MODIFY COLUMN `affected_file_path` VARCHAR(2000) DEFAULT NULL;

ALTER TABLE `te_story_platform`.`sp_knowledge_hold`
    MODIFY COLUMN `change_reason` VARCHAR(2000) DEFAULT NULL;

ALTER TABLE `te_story_platform`.`sp_knowledge_relationship_hold`
    MODIFY COLUMN `change_reason` VARCHAR(2000) DEFAULT NULL;

ALTER TABLE `te_story_platform`.`sp_knowledge_type_hold`
    MODIFY COLUMN `change_reason` VARCHAR(2000) DEFAULT NULL;

ALTER TABLE `te_story_platform`.`sp_metadata`
    MODIFY COLUMN `metadata_value` VARCHAR(2000) DEFAULT NULL COMMENT 'Metadata Value. 권장 용어, 대체값, 정규식 또는 규제 실행값.';

ALTER TABLE `te_story_platform`.`sp_object`
    MODIFY COLUMN `target_identifier_field` VARCHAR(99) DEFAULT NULL COMMENT '생성 대상 Identifier 필드명. 예: member_id, database_id, api_id';

ALTER TABLE `te_story_platform`.`sp_object_lifecycle`
    MODIFY COLUMN `lifecycle_reason` VARCHAR(2000) DEFAULT NULL;

SELECT 'AFTER' AS verification_step, table_name, column_name, column_type
FROM information_schema.columns
WHERE table_schema = 'te_story_platform'
  AND (table_name, column_name) IN
(
    ('sp_attribute', 'data_type'),
    ('sp_attribute', 'default_value'),
    ('sp_attribute', 'attribute_comment'),
    ('sp_business', 'business_description'),
    ('sp_domain', 'domain_description'),
    ('sp_entity', 'entity_comment'),
    ('sp_erd', 'erd_description'),
    ('sp_execution_history', 'generated_identifier'),
    ('sp_execution_history', 'repository_status'),
    ('sp_execution_history', 'mongodb_status'),
    ('sp_execution_history', 'execution_status'),
    ('sp_execution_history', 'history_status'),
    ('sp_identifier_blueprint', 'remark'),
    ('sp_impact_analysis_result', 'change_target_text'),
    ('sp_impact_analysis_result', 'affected_file_path'),
    ('sp_knowledge_hold', 'change_reason'),
    ('sp_knowledge_relationship_hold', 'change_reason'),
    ('sp_knowledge_type_hold', 'change_reason'),
    ('sp_metadata', 'metadata_value'),
    ('sp_object', 'target_identifier_field'),
    ('sp_object_lifecycle', 'lifecycle_reason')
)
ORDER BY table_name, ordinal_position;

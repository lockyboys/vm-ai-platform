/*
File Name   : repository_knowledge_batch_20260719.sql
Purpose     : Repository Table disposition Knowledge batch registration
Safety      : Knowledge registration only. No DROP, ALTER, RENAME or data migration.
Principles  : Repository First / Metadata Driven / Single Source of Truth
*/

SET NAMES utf8mb4;
USE te_story_platform;
SET @actor_id := 'SYSTEM';
SET @client_ip := '127.0.0.1';
SET @program_id := 'SPS_REPOSITORY_KNOWLEDGE_BATCH_20260719';

START TRANSACTION;

/* 1. Resolve Knowledge Type metadata. */
SET @entity_type_id := (
    SELECT knowledge_type_id
    FROM te_story_platform.sp_knowledge_type_hold
    WHERE knowledge_type_code = 'ENTITY'
      AND active_yn = 'Y'
      AND deleted_yn = 'N'
    LIMIT 1
);

SET @object_type_id := (
    SELECT knowledge_type_id
    FROM te_story_platform.sp_knowledge_type_hold
    WHERE knowledge_type_code = 'OBJECT'
      AND active_yn = 'Y'
      AND deleted_yn = 'N'
    LIMIT 1
);

SELECT
    CASE
        WHEN @entity_type_id IS NOT NULL
         AND @object_type_id IS NOT NULL
        THEN 'SUCCESS'
        ELSE 'ERROR'
    END AS verification_result,
    @entity_type_id AS entity_type_id,
    @object_type_id AS object_type_id;

/* 2. Build live Repository inventory and initial disposition. */
DROP TEMPORARY TABLE IF EXISTS tmp_repository_table_decision;

CREATE TEMPORARY TABLE tmp_repository_table_decision
(
    table_schema VARCHAR(99) NOT NULL,
    table_name VARCHAR(150) NOT NULL,
    table_type VARCHAR(30) NOT NULL,
    table_comment TEXT NULL,
    estimated_row_count BIGINT NULL,
    decision_code VARCHAR(30) NOT NULL,
    decision_reason VARCHAR(2000) NOT NULL,
    data_preserve_yn CHAR(1) NOT NULL DEFAULT 'Y',
    drop_allowed_yn CHAR(1) NOT NULL DEFAULT 'N',
    migration_required_yn CHAR(1) NOT NULL DEFAULT 'N',
    next_action VARCHAR(2000) NOT NULL,
    PRIMARY KEY (table_schema, table_name)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

INSERT INTO tmp_repository_table_decision
(
    table_schema,
    table_name,
    table_type,
    table_comment,
    estimated_row_count,
    decision_code,
    decision_reason,
    data_preserve_yn,
    drop_allowed_yn,
    migration_required_yn,
    next_action
)
SELECT
    table_schema,
    table_name,
    table_type,
    NULLIF(table_comment, ''),
    table_rows,
    CASE
        WHEN table_name IN
        (
            'health_report_backup_20260624',
            'sql_guard_verification_log_backup_20260624'
        ) THEN 'DISPOSE'
        WHEN table_name IN
        (
            'cm_sequence_definition',
            'cm_sequence_format_definition',
            'cm_sequence_policy_definition'
        ) THEN 'DISPOSE'
        WHEN table_name = 'health_report' THEN 'DISPOSE'
        WHEN table_name = 'cm_data_type' THEN 'MERGE'
        WHEN table_name IN
        (
            'cm_audit_policy',
            'cm_business_domain',
            'cm_storage_repository',
            'md_object',
            'md_relation',
            'system_user',
            'sp_policy_rule_candidate'
        ) THEN 'INTEGRATE'
        WHEN table_schema = 'te_health_companion' THEN 'REDESIGN'
        WHEN RIGHT(table_name, 5) = '_hold' THEN 'HOLD'
        ELSE 'HOLD'
    END AS decision_code,
    CASE
        WHEN table_name LIKE '%backup%' THEN
            'Backup Table이며 실사용·FK·Source 사용 여부 검증 후 폐기한다.'
        WHEN table_name IN
        (
            'cm_sequence_definition',
            'cm_sequence_format_definition',
            'cm_sequence_policy_definition'
        ) THEN
            '현재 운영 Sequence 계열과 중복되는 구형 Definition 계열이다.'
        WHEN table_name = 'health_report' THEN
            'COMMON Database 소속이 부적절한 초기 Health Prototype Table이다.'
        WHEN table_name = 'cm_data_type' THEN
            'cm_common_code의 CM_DATA_TYPE 그룹과 중복되므로 공통코드로 Merge한다.'
        WHEN table_schema = 'te_health_companion' THEN
            'Health Companion 초기 Prototype 구조이며 데이터 보존 후 재설계한다.'
        WHEN RIGHT(table_name, 5) = '_hold' THEN
            '기존 결정에 따라 Hold 상태를 유지하며 변경을 금지한다.'
        WHEN table_name IN
        (
            'cm_audit_policy',
            'cm_business_domain',
            'cm_storage_repository',
            'md_object',
            'md_relation',
            'system_user',
            'sp_policy_rule_candidate'
        ) THEN
            '다른 Repository Object와 역할 또는 식별 체계가 중복되어 통합 검토가 필요하다.'
        ELSE
            '전체 상관 분석의 최초 등록 대상으로 현재 구조와 데이터를 보존한다.'
    END AS decision_reason,
    'Y' AS data_preserve_yn,
    'N' AS drop_allowed_yn,
    CASE
        WHEN table_name IN
        (
            'cm_data_type',
            'cm_audit_policy',
            'cm_business_domain',
            'cm_storage_repository',
            'md_object',
            'md_relation',
            'system_user',
            'sp_policy_rule_candidate'
        ) OR table_schema = 'te_health_companion'
        THEN 'Y'
        ELSE 'N'
    END AS migration_required_yn,
    CASE
        WHEN table_name LIKE '%backup%' THEN
            '정확한 COUNT, Source 사용처, FK 부재를 재검증한 후 별도 폐기 SQL을 승인한다.'
        WHEN table_name = 'cm_data_type' THEN
            'CM_DATA_TYPE 공통코드와 데이터 대조 후 참조 경로를 전환한다.'
        WHEN table_schema = 'te_health_companion' THEN
            '신규 업무 모델을 확정하고 기존 데이터를 Migration한다.'
        WHEN RIGHT(table_name, 5) = '_hold' THEN
            'HOLD 해제 결정 전까지 DROP, RENAME, MIGRATION을 금지한다.'
        ELSE
            '전체 판정표 확정 후 KEEP, MODIFY, MERGE, INTEGRATE, DISPOSE를 승인한다.'
    END AS next_action
FROM information_schema.tables
WHERE table_schema IN
(
    'te_common',
    'te_story_platform',
    'te_health_companion'
)
AND table_type IN ('BASE TABLE', 'VIEW');

/* 3. Register every live Table/View as an idempotent Knowledge Object. */
INSERT INTO te_story_platform.sp_knowledge_hold
(
    knowledge_identifier,
    knowledge_type_id,
    knowledge_name,
    knowledge_description,
    source_story_text,
    active_yn,
    created_by,
    created_dt,
    updated_by,
    updated_dt,
    deleted_yn,
    change_reason,
    client_ip,
    program_id
)
SELECT
    UPPER(CONCAT('KWH_TABLE_', table_schema, '_', table_name)),
    CASE
        WHEN table_type = 'VIEW' THEN @object_type_id
        ELSE @entity_type_id
    END,
    CONCAT(table_schema, '.', table_name),
    COALESCE(
        table_comment,
        CONCAT(table_schema, '.', table_name, ' Repository Object')
    ),
    CONCAT(
        'DATABASE_NAME: ', table_schema, CHAR(10),
        'TABLE_NAME: ', table_name, CHAR(10),
        'OBJECT_TYPE: ', table_type, CHAR(10),
        'DECISION: ', decision_code, CHAR(10),
        'DECISION_REASON: ', decision_reason, CHAR(10),
        'DATA_PRESERVE_YN: ', data_preserve_yn, CHAR(10),
        'DROP_ALLOWED_YN: ', drop_allowed_yn, CHAR(10),
        'MIGRATION_REQUIRED_YN: ', migration_required_yn, CHAR(10),
        'ROW_COUNT_POLICY: information_schema.table_rows는 추정값이므로 폐기 판정에 사용하지 않는다.', CHAR(10),
        'NEXT_ACTION: ', next_action
    ),
    'Y',
    @actor_id,
    CURRENT_TIMESTAMP(),
    @actor_id,
    CURRENT_TIMESTAMP(),
    'N',
    '전체 Repository Table 상관 분석 최초 Batch 등록',
    @client_ip,
    @program_id
FROM tmp_repository_table_decision
ON DUPLICATE KEY UPDATE
    knowledge_type_id = VALUES(knowledge_type_id),
    knowledge_name = VALUES(knowledge_name),
    knowledge_description = VALUES(knowledge_description),
    source_story_text = VALUES(source_story_text),
    active_yn = 'Y',
    updated_by = VALUES(updated_by),
    updated_dt = VALUES(updated_dt),
    deleted_yn = 'N',
    deleted_by = NULL,
    deleted_dt = NULL,
    change_reason = VALUES(change_reason),
    client_ip = VALUES(client_ip),
    program_id = VALUES(program_id);

/* 4. Register physical Foreign Keys as REFERENCES relationships. */
INSERT INTO te_story_platform.sp_knowledge_relationship_hold
(
    source_knowledge_id,
    target_knowledge_id,
    relationship_type_code,
    relationship_description,
    active_yn,
    created_by,
    created_dt,
    updated_by,
    updated_dt,
    deleted_yn,
    change_reason,
    client_ip,
    program_id
)
SELECT DISTINCT
    source_knowledge.knowledge_id,
    target_knowledge.knowledge_id,
    'REFERENCES',
    CONCAT(
        key_usage.constraint_schema, '.',
        key_usage.table_name, '.',
        key_usage.column_name,
        ' -> ',
        key_usage.referenced_table_schema, '.',
        key_usage.referenced_table_name, '.',
        key_usage.referenced_column_name,
        ' / CONSTRAINT: ',
        key_usage.constraint_name
    ),
    'Y',
    @actor_id,
    CURRENT_TIMESTAMP(),
    @actor_id,
    CURRENT_TIMESTAMP(),
    'N',
    '실 DB Foreign Key를 Knowledge Relationship으로 자동 등록',
    @client_ip,
    @program_id
FROM information_schema.key_column_usage key_usage
JOIN te_story_platform.sp_knowledge_hold source_knowledge
  ON source_knowledge.knowledge_identifier = UPPER(
      CONCAT(
          'KWH_TABLE_',
          key_usage.constraint_schema,
          '_',
          key_usage.table_name
      )
  )
JOIN te_story_platform.sp_knowledge_hold target_knowledge
  ON target_knowledge.knowledge_identifier = UPPER(
      CONCAT(
          'KWH_TABLE_',
          key_usage.referenced_table_schema,
          '_',
          key_usage.referenced_table_name
      )
  )
WHERE key_usage.constraint_schema IN
(
    'te_common',
    'te_story_platform',
    'te_health_companion'
)
AND key_usage.referenced_table_name IS NOT NULL
AND NOT EXISTS
(
    SELECT 1
    FROM te_story_platform.sp_knowledge_relationship_hold existing_relation
    WHERE existing_relation.source_knowledge_id = source_knowledge.knowledge_id
      AND existing_relation.target_knowledge_id = target_knowledge.knowledge_id
      AND existing_relation.relationship_type_code = 'REFERENCES'
      AND existing_relation.relationship_description = CONCAT(
          key_usage.constraint_schema, '.',
          key_usage.table_name, '.',
          key_usage.column_name,
          ' -> ',
          key_usage.referenced_table_schema, '.',
          key_usage.referenced_table_name, '.',
          key_usage.referenced_column_name,
          ' / CONSTRAINT: ',
          key_usage.constraint_name
      )
      AND existing_relation.deleted_yn = 'N'
);

/* 5. Build explicit disposition relationships. */
DROP TEMPORARY TABLE IF EXISTS tmp_repository_disposition_relation;

CREATE TEMPORARY TABLE tmp_repository_disposition_relation
(
    source_schema VARCHAR(99) NOT NULL,
    source_table VARCHAR(150) NOT NULL,
    target_schema VARCHAR(99) NOT NULL,
    target_table VARCHAR(150) NOT NULL,
    relationship_type_code VARCHAR(50) NOT NULL,
    relationship_description VARCHAR(2000) NOT NULL,
    PRIMARY KEY
    (
        source_schema,
        source_table,
        target_schema,
        target_table,
        relationship_type_code
    )
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

INSERT INTO tmp_repository_disposition_relation VALUES
('te_common', 'cm_data_type', 'te_common', 'cm_common_code', 'MERGE_INTO', 'CM_DATA_TYPE 공통코드로 Merge한다.'),
('te_common', 'cm_audit_policy', 'te_common', 'cm_common_code', 'INTEGRATE_CANDIDATE', '감사 정책 선택값의 공통코드 통합 여부를 검토한다.'),
('te_common', 'cm_sequence_definition', 'te_common', 'cm_sequence_rule', 'REPLACE_BY', '구형 Sequence Definition을 현행 Sequence Rule로 대체한다.'),
('te_common', 'cm_sequence_format_definition', 'te_common', 'cm_sequence_format', 'REPLACE_BY', '구형 Format Definition을 현행 Sequence Format으로 대체한다.'),
('te_common', 'cm_sequence_policy_definition', 'te_common', 'cm_sequence_policy', 'REPLACE_BY', '구형 Policy Definition을 현행 Sequence Policy로 대체한다.'),
('te_common', 'health_report_backup_20260624', 'te_common', 'health_report', 'DISPOSE_AFTER', '원본 상태 검증 후 Backup Table을 폐기한다.'),
('te_common', 'sql_guard_verification_log_backup_20260624', 'te_common', 'sql_guard_verification_log', 'DISPOSE_AFTER', '원본 상태 검증 후 Backup Table을 폐기한다.'),
('te_common', 'system_user', 'te_common', 'cm_member', 'INTEGRATE_CANDIDATE', 'User Identity를 Member Identity와 통합 검토한다.'),
('te_common', 'cm_storage_repository', 'te_common', 'cm_repository', 'INTEGRATE_CANDIDATE', 'Storage Repository와 Core Repository 역할 통합 여부를 검토한다.'),
('te_common', 'md_object', 'te_story_platform', 'sp_object', 'INTEGRATE_CANDIDATE', 'Metadata Object와 SPS Object 역할 통합 여부를 검토한다.'),
('te_common', 'md_relation', 'te_story_platform', 'sp_relationship', 'INTEGRATE_CANDIDATE', 'Metadata Relation과 SPS Relationship 역할 통합 여부를 검토한다.'),
('te_common', 'cm_business_domain', 'te_story_platform', 'sp_domain', 'INTEGRATE_CANDIDATE', '공통 업무 도메인과 Story Domain의 역할을 통합 검토한다.'),
('te_common', 'sp_policy_rule_candidate', 'te_common', 'rl_rule', 'INTEGRATE_CANDIDATE', 'Policy Rule Candidate를 범용 Rule Repository와 통합 검토한다.');

INSERT INTO te_story_platform.sp_knowledge_relationship_hold
(
    source_knowledge_id,
    target_knowledge_id,
    relationship_type_code,
    relationship_description,
    active_yn,
    created_by,
    created_dt,
    updated_by,
    updated_dt,
    deleted_yn,
    change_reason,
    client_ip,
    program_id
)
SELECT
    source_knowledge.knowledge_id,
    target_knowledge.knowledge_id,
    disposition.relationship_type_code,
    disposition.relationship_description,
    'Y',
    @actor_id,
    CURRENT_TIMESTAMP(),
    @actor_id,
    CURRENT_TIMESTAMP(),
    'N',
    'Table 정비 판정 관계 최초 Batch 등록',
    @client_ip,
    @program_id
FROM tmp_repository_disposition_relation disposition
JOIN te_story_platform.sp_knowledge_hold source_knowledge
  ON source_knowledge.knowledge_identifier = UPPER(
      CONCAT(
          'KWH_TABLE_',
          disposition.source_schema,
          '_',
          disposition.source_table
      )
  )
JOIN te_story_platform.sp_knowledge_hold target_knowledge
  ON target_knowledge.knowledge_identifier = UPPER(
      CONCAT(
          'KWH_TABLE_',
          disposition.target_schema,
          '_',
          disposition.target_table
      )
  )
WHERE NOT EXISTS
(
    SELECT 1
    FROM te_story_platform.sp_knowledge_relationship_hold existing_relation
    WHERE existing_relation.source_knowledge_id = source_knowledge.knowledge_id
      AND existing_relation.target_knowledge_id = target_knowledge.knowledge_id
      AND existing_relation.relationship_type_code = disposition.relationship_type_code
      AND existing_relation.deleted_yn = 'N'
);

/* 6. Verification. */
SELECT
    'INVENTORY_DECISION_COUNT' AS verification_step,
    decision_code,
    COUNT(*) AS object_count
FROM tmp_repository_table_decision
GROUP BY decision_code
ORDER BY decision_code;

SELECT
    'KNOWLEDGE_BATCH_COUNT' AS verification_step,
    COUNT(*) AS registered_count
FROM te_story_platform.sp_knowledge_hold
WHERE BINARY program_id = BINARY @program_id
  AND deleted_yn = 'N';

SELECT
    'RELATIONSHIP_BATCH_COUNT' AS verification_step,
    relationship_type_code,
    COUNT(*) AS registered_count
FROM te_story_platform.sp_knowledge_relationship_hold
WHERE BINARY program_id = BINARY @program_id
  AND deleted_yn = 'N'
GROUP BY relationship_type_code
ORDER BY relationship_type_code;

SELECT
    'KNOWLEDGE_WITHOUT_IDENTIFIER' AS verification_step,
    COUNT(*) AS error_count
FROM te_story_platform.sp_knowledge_hold
WHERE BINARY program_id = BINARY @program_id
  AND (
      knowledge_identifier IS NULL
      OR knowledge_identifier = ''
  );

SELECT
    'ORPHAN_RELATIONSHIP' AS verification_step,
    COUNT(*) AS error_count
FROM te_story_platform.sp_knowledge_relationship_hold relation_object
LEFT JOIN te_story_platform.sp_knowledge_hold source_knowledge
  ON source_knowledge.knowledge_id = relation_object.source_knowledge_id
LEFT JOIN te_story_platform.sp_knowledge_hold target_knowledge
  ON target_knowledge.knowledge_id = relation_object.target_knowledge_id
WHERE BINARY relation_object.program_id = BINARY @program_id
  AND (
      source_knowledge.knowledge_id IS NULL
      OR target_knowledge.knowledge_id IS NULL
  );

/* Registration only. No structural changes are executed. */
COMMIT;
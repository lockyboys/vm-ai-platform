-- Common Code empty-group batch History and Evidence supplement
-- Target: 9 groups and 42 codes applied at 2026-07-22 09:37:59
-- Idempotent: fixed identifiers and fixed created_dt are used.

USE te_common;

SET @actor = 'SYSTEM';
SET @client_ip = '127.0.0.1';
SET @program_id = 'CM_COMMON_CODE_BATCH_20260722';
SET @batch_dt = TIMESTAMP('2026-07-22 09:37:59');
SET @evidence_id = 'CM_EV_EVIDENCE_20260722_093759_00001';

START TRANSACTION;

-- History 1: nine group metadata updates.
INSERT IGNORE INTO cm_change_history
(
    change_history_id, target_database_name, target_table_name,
    target_record_id, action_type, change_story,
    created_by, created_dt, client_ip, program_id, status_code
)
SELECT
    CONCAT('CM_CO_CHANGE_HISTORY_20260722_093759_G', LPAD(ROW_NUMBER() OVER (ORDER BY group_code), 2, '0')),
    'te_common',
    'cm_common_code_group',
    group_code,
    'BATCH',
    CONCAT(group_code, ' Group의 설명·시스템 여부·상태·감사정보를 보완한다.'),
    @actor, @batch_dt, @client_ip, @program_id, 'ACTIVE'
FROM cm_common_code_group
WHERE group_code IN
(
    'AI_ANALYSIS_STATUS','AI_PROVIDER','HP_RISK_LEVEL','HS_HOSPITAL_TYPE',
    'OC_DOCUMENT_TYPE','SPS_FUNCTION','SPS_SEQUENCE_FORMAT',
    'SPS_SEQUENCE_POLICY','WF_WELFARE_TYPE'
);

-- History 2: forty-two common-code upserts.
INSERT IGNORE INTO cm_change_history
(
    change_history_id, target_database_name, target_table_name,
    target_record_id, action_type, change_story,
    created_by, created_dt, client_ip, program_id, status_code
)
SELECT
    CONCAT('CM_CO_CHANGE_HISTORY_20260722_093759_C', LPAD(ROW_NUMBER() OVER (ORDER BY group_code, sort_no, code), 2, '0')),
    'te_common',
    'cm_common_code',
    CONCAT(group_code, ':', code),
    'BATCH',
    CONCAT(group_code, '.', code, ' 공통코드를 등록 또는 최신 정의로 갱신한다.'),
    @actor, @batch_dt, @client_ip, @program_id, 'ACTIVE'
FROM cm_common_code
WHERE program_id = @program_id
  AND group_code IN
(
    'AI_ANALYSIS_STATUS','AI_PROVIDER','HP_RISK_LEVEL','HS_HOSPITAL_TYPE',
    'OC_DOCUMENT_TYPE','SPS_FUNCTION','SPS_SEQUENCE_FORMAT',
    'SPS_SEQUENCE_POLICY','WF_WELFARE_TYPE'
);

-- Official Evidence definition. Source SQL, source rows, execution log, and
-- verification report paths are preserved in summary/remark until a valid
-- INTERNAL_DOCUMENT code is registered in REFERENCE_TYPE.
INSERT INTO ev_evidence
(
    evidence_id, evidence_code, evidence_name,
    evidence_level_code, evidence_category_code,
    organization_name, source_title, published_dt,
    effective_from_dt, version_num, status_code,
    summary, remark, sort_no,
    created_dt, created_by, updated_dt, updated_by,
    program_id, client_ip
)
VALUES
(
    @evidence_id,
    'EV_CM_COMMON_CODE_EMPTY_GROUP_BATCH_2026_000001',
    '공통코드 빈 Group 9건 및 Code 42건 정비 근거',
    'A',
    'REPOSITORY_MAINTENANCE',
    'Story Programming Framework',
    '공통코드 빈 Group 정비 배치 실행 및 검증',
    @batch_dt,
    @batch_dt,
    '1.0',
    'ACTIVE',
    '62개 Group·373개 Code 감사 결과에서 코드가 비어 있던 9개 Group을 조사하고, Source·Repository·Master 값 및 SPS 확장 설계를 근거로 42개 Code를 등록했다.',
    'SOURCE_SQL=sql/runtime/common_code_empty_groups_batch_20260722.sql; SOURCE_ROWS=outputs/reports/common_code_full_audit_20260721.json; EXECUTION_LOG=outputs/logs/common_code_empty_groups_batch_20260722_093759.log; REAUDIT=outputs/reports/common_code_full_audit_20260722_after_empty_group_batch.json; REFERENCE_TYPE Repository에 INTERNAL_DOCUMENT가 없어 ev_evidence_reference 등록은 보류한다.',
    10,
    @batch_dt, @actor, @batch_dt, @actor,
    @program_id, @client_ip
)
ON DUPLICATE KEY UPDATE
    evidence_name = VALUES(evidence_name),
    evidence_level_code = VALUES(evidence_level_code),
    evidence_category_code = VALUES(evidence_category_code),
    organization_name = VALUES(organization_name),
    source_title = VALUES(source_title),
    published_dt = VALUES(published_dt),
    effective_from_dt = VALUES(effective_from_dt),
    version_num = VALUES(version_num),
    status_code = VALUES(status_code),
    summary = VALUES(summary),
    remark = VALUES(remark),
    updated_dt = VALUES(updated_dt),
    updated_by = VALUES(updated_by),
    program_id = VALUES(program_id),
    client_ip = VALUES(client_ip);

INSERT INTO ev_evidence_version
(
    evidence_version_id, evidence_id, version_num,
    effective_from_dt, change_summary, remark,
    created_dt, created_by, updated_dt, updated_by,
    program_id, client_ip, status_code
)
VALUES
(
    'CM_EV_EVIDENCE_VERSION_20260722_093759_00001',
    @evidence_id,
    '1.0',
    @batch_dt,
    '공통코드 빈 Group 9건에 Code 42건을 등록하고 Group Metadata를 보완한 최초 근거 Version.',
    '등록 SQL·원본 감사 행·실행 로그·재감사 결과를 Evidence 경로로 보존한다.',
    @batch_dt, @actor, @batch_dt, @actor,
    @program_id, @client_ip, 'ACTIVE'
)
ON DUPLICATE KEY UPDATE
    change_summary = VALUES(change_summary),
    remark = VALUES(remark),
    updated_dt = VALUES(updated_dt),
    updated_by = VALUES(updated_by),
    program_id = VALUES(program_id),
    client_ip = VALUES(client_ip),
    status_code = VALUES(status_code);

-- Hard validation. Force rollback through SIGNAL if counts do not match.
SET @history_count = (
    SELECT COUNT(*)
    FROM cm_change_history
    WHERE created_dt = @batch_dt
      AND program_id = @program_id
      AND change_history_id LIKE 'CM_CO_CHANGE_HISTORY_20260722_093759_%'
);
SET @group_count = (
    SELECT COUNT(*)
    FROM cm_common_code_group
    WHERE group_code IN
    (
        'AI_ANALYSIS_STATUS','AI_PROVIDER','HP_RISK_LEVEL','HS_HOSPITAL_TYPE',
        'OC_DOCUMENT_TYPE','SPS_FUNCTION','SPS_SEQUENCE_FORMAT',
        'SPS_SEQUENCE_POLICY','WF_WELFARE_TYPE'
    )
);
SET @code_count = (
    SELECT COUNT(*)
    FROM cm_common_code
    WHERE program_id = @program_id
      AND group_code IN
    (
        'AI_ANALYSIS_STATUS','AI_PROVIDER','HP_RISK_LEVEL','HS_HOSPITAL_TYPE',
        'OC_DOCUMENT_TYPE','SPS_FUNCTION','SPS_SEQUENCE_FORMAT',
        'SPS_SEQUENCE_POLICY','WF_WELFARE_TYPE'
    )
);
SET @evidence_count = (
    SELECT COUNT(*) FROM ev_evidence WHERE evidence_id = @evidence_id
);
SET @version_count = (
    SELECT COUNT(*) FROM ev_evidence_version
    WHERE evidence_version_id = 'CM_EV_EVIDENCE_VERSION_20260722_093759_00001'
);

CREATE TEMPORARY TABLE tmp_common_code_batch_assert
(
    validation_result TINYINT NOT NULL,
    CONSTRAINT chk_common_code_batch_assert CHECK (validation_result = 1)
);

INSERT INTO tmp_common_code_batch_assert (validation_result)
VALUES
(
    IF(
        @history_count = 51
        AND @group_count = 9
        AND @code_count = 42
        AND @evidence_count = 1
        AND @version_count = 1,
        1,
        0
    )
);

DROP TEMPORARY TABLE tmp_common_code_batch_assert;

COMMIT;

SELECT @history_count AS history_count,
       @group_count AS group_count,
       @code_count AS code_count,
       @evidence_count AS evidence_count,
       @version_count AS evidence_version_count;

SELECT change_history_id, target_table_name, target_record_id,
       action_type, change_story, created_dt, program_id
FROM cm_change_history
WHERE created_dt = @batch_dt
  AND program_id = @program_id
ORDER BY change_history_id;

SELECT evidence_id, evidence_code, evidence_name, evidence_level_code,
       evidence_category_code, version_num, status_code, summary, remark
FROM ev_evidence
WHERE evidence_id = @evidence_id;

SELECT evidence_version_id, evidence_id, version_num, effective_from_dt,
       change_summary, status_code
FROM ev_evidence_version
WHERE evidence_id = @evidence_id;

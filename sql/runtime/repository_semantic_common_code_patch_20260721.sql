-- SPS Repository semantic common-code registration
-- Date: 2026-07-21
-- Scope: 5 groups, 9 codes, 6 column COMMENT corrections

SET NAMES utf8mb4;

START TRANSACTION;

INSERT INTO te_common.cm_common_code_group
    (group_code, group_name, group_description, sort_no, status_code,
     reserved_yn, system_yn, created_by, updated_by, program_id)
VALUES
    ('EVIDENCE_LEVEL', '근거 수준', 'Evidence의 신뢰도와 근거 강도를 A/B/C/D 등급으로 관리한다.', 210, 'ACTIVE', 'N', 'Y', 'SYSTEM', 'SYSTEM', 'CM_CO_COMMON_CODE_20260721_00001'),
    ('REFERENCE_TYPE', '참조 유형', 'Evidence가 참조하는 정부문서, 논문, URL 등 출처 유형을 관리한다.', 220, 'ACTIVE', 'N', 'Y', 'SYSTEM', 'SYSTEM', 'CM_CO_COMMON_CODE_20260721_00001'),
    ('RULE_TYPE', '규칙 유형', 'Rule의 처리 목적과 평가 방식을 구분하는 유형을 관리한다.', 230, 'ACTIVE', 'N', 'Y', 'SYSTEM', 'SYSTEM', 'CM_CO_COMMON_CODE_20260721_00001'),
    ('AUDIT_TYPE', '감사 유형', 'Audit Record가 추적하는 판단, 실행 및 변경 유형을 관리한다.', 240, 'ACTIVE', 'N', 'Y', 'SYSTEM', 'SYSTEM', 'CM_CO_COMMON_CODE_20260721_00001'),
    ('OBJECT_LIFECYCLE_EVENT', 'Object Lifecycle Event', 'Object Lifecycle에서 발생하는 등록, 변경, 폐기 등의 Event를 관리한다.', 250, 'ACTIVE', 'N', 'Y', 'SYSTEM', 'SYSTEM', 'CM_CO_COMMON_CODE_20260721_00001')
ON DUPLICATE KEY UPDATE
    group_name = VALUES(group_name),
    group_description = VALUES(group_description),
    status_code = 'ACTIVE',
    system_yn = 'Y',
    updated_by = 'SYSTEM',
    program_id = VALUES(program_id),
    deleted_by = NULL,
    deleted_dt = NULL;

INSERT INTO te_common.cm_common_code
    (group_code, code, code_name, common_code_description, sort_no,
     status_code, created_by, updated_by, program_id, common_code_json)
VALUES
    ('EVIDENCE_LEVEL', 'A', 'A 등급', '가장 높은 수준의 Evidence 등급.', 10, 'ACTIVE', 'SYSTEM', 'SYSTEM', 'CM_CO_COMMON_CODE_20260721_00001', JSON_OBJECT('level', 1, 'grade', 'A')),
    ('EVIDENCE_LEVEL', 'B', 'B 등급', '높은 수준의 Evidence 등급.', 20, 'ACTIVE', 'SYSTEM', 'SYSTEM', 'CM_CO_COMMON_CODE_20260721_00001', JSON_OBJECT('level', 2, 'grade', 'B')),
    ('EVIDENCE_LEVEL', 'C', 'C 등급', '보통 수준의 Evidence 등급.', 30, 'ACTIVE', 'SYSTEM', 'SYSTEM', 'CM_CO_COMMON_CODE_20260721_00001', JSON_OBJECT('level', 3, 'grade', 'C')),
    ('EVIDENCE_LEVEL', 'D', 'D 등급', '제한적 수준의 Evidence 등급.', 40, 'ACTIVE', 'SYSTEM', 'SYSTEM', 'CM_CO_COMMON_CODE_20260721_00001', JSON_OBJECT('level', 4, 'grade', 'D')),
    ('REFERENCE_TYPE', 'GOV_DOCUMENT', '정부 문서', '정부 또는 공공기관이 발행한 공식 문서.', 10, 'ACTIVE', 'SYSTEM', 'SYSTEM', 'CM_CO_COMMON_CODE_20260721_00001', JSON_OBJECT('source_type', 'GOVERNMENT_DOCUMENT')),
    ('RULE_TYPE', 'LIFECYCLE', 'Lifecycle 규칙', 'Object Lifecycle 상태와 Event 전이를 통제하는 Rule 유형.', 10, 'ACTIVE', 'SYSTEM', 'SYSTEM', 'CM_CO_COMMON_CODE_20260721_00001', JSON_OBJECT('rule_scope', 'LIFECYCLE')),
    ('RULE_TYPE', 'THRESHOLD', '임계값 규칙', '입력값과 임계값을 비교하여 판단하는 Rule 유형.', 20, 'ACTIVE', 'SYSTEM', 'SYSTEM', 'CM_CO_COMMON_CODE_20260721_00001', JSON_OBJECT('rule_scope', 'THRESHOLD')),
    ('AUDIT_TYPE', 'DECISION', '판단 감사', 'Decision Engine의 판단 과정과 결과를 추적하는 Audit 유형.', 10, 'ACTIVE', 'SYSTEM', 'SYSTEM', 'CM_CO_COMMON_CODE_20260721_00001', JSON_OBJECT('audit_scope', 'DECISION')),
    ('OBJECT_LIFECYCLE_EVENT', 'REGISTER', '등록', 'Object가 Repository에 최초 등록된 Lifecycle Event.', 10, 'ACTIVE', 'SYSTEM', 'SYSTEM', 'CM_CO_COMMON_CODE_20260721_00001', JSON_OBJECT('event', 'REGISTER'))
ON DUPLICATE KEY UPDATE
    code_name = VALUES(code_name),
    common_code_description = VALUES(common_code_description),
    sort_no = VALUES(sort_no),
    status_code = 'ACTIVE',
    updated_by = 'SYSTEM',
    program_id = VALUES(program_id),
    common_code_json = VALUES(common_code_json),
    deleted_by = NULL,
    deleted_dt = NULL;

COMMIT;

ALTER TABLE te_common.cm_verified_sql_query
    MODIFY COLUMN certified_level_code VARCHAR(99) DEFAULT NULL
    COMMENT '검증 인증 수준 코드. SSOT: te_common.cm_common_code의 group_code=EVIDENCE_LEVEL. A, B, C, D 중 등록된 Code를 사용한다.';

ALTER TABLE te_common.ev_evidence
    MODIFY COLUMN evidence_level_code VARCHAR(99) NOT NULL
    COMMENT '근거 수준 코드. SSOT: te_common.cm_common_code의 group_code=EVIDENCE_LEVEL. A, B, C, D 중 등록된 Code를 사용한다.';

ALTER TABLE te_common.ev_evidence_reference
    MODIFY COLUMN reference_type_code VARCHAR(99) NOT NULL
    COMMENT '근거 참조 유형 코드. SSOT: te_common.cm_common_code의 group_code=REFERENCE_TYPE. GOV_DOCUMENT 등 등록된 Code를 사용한다.';

ALTER TABLE te_common.rl_rule
    MODIFY COLUMN rule_type_code VARCHAR(99) NOT NULL
    COMMENT 'Rule 유형 코드. SSOT: te_common.cm_common_code의 group_code=RULE_TYPE. LIFECYCLE, THRESHOLD 등 등록된 Code를 사용한다.';

ALTER TABLE te_health_companion.at_audit
    MODIFY COLUMN audit_type_code VARCHAR(99) NOT NULL
    COMMENT '감사 유형 코드. SSOT: te_common.cm_common_code의 group_code=AUDIT_TYPE. DECISION 등 등록된 Code를 사용한다.';

ALTER TABLE te_story_platform.sp_object_lifecycle
    MODIFY COLUMN lifecycle_event_code VARCHAR(99) NOT NULL
    COMMENT 'Object Lifecycle Event 코드. SSOT: te_common.cm_common_code의 group_code=OBJECT_LIFECYCLE_EVENT. REGISTER 등 등록된 Code를 사용한다.';

SELECT group_code, group_name, status_code
FROM te_common.cm_common_code_group
WHERE group_code IN
    ('EVIDENCE_LEVEL', 'REFERENCE_TYPE', 'RULE_TYPE', 'AUDIT_TYPE', 'OBJECT_LIFECYCLE_EVENT')
ORDER BY group_code;

SELECT group_code, code, code_name, status_code
FROM te_common.cm_common_code
WHERE group_code IN
    ('EVIDENCE_LEVEL', 'REFERENCE_TYPE', 'RULE_TYPE', 'AUDIT_TYPE', 'OBJECT_LIFECYCLE_EVENT')
ORDER BY group_code, sort_no, code;

SELECT
    (SELECT COUNT(*)
       FROM te_common.cm_verified_sql_query q
       LEFT JOIN te_common.cm_common_code c
         ON c.group_code = 'EVIDENCE_LEVEL'
        AND CONVERT(q.certified_level_code USING utf8mb4) COLLATE utf8mb4_unicode_ci
            = c.code COLLATE utf8mb4_unicode_ci
      WHERE q.certified_level_code IS NOT NULL AND c.code IS NULL) AS invalid_certified_level_count,
    (SELECT COUNT(*)
       FROM te_common.ev_evidence e
       LEFT JOIN te_common.cm_common_code c
         ON c.group_code = 'EVIDENCE_LEVEL'
        AND CONVERT(e.evidence_level_code USING utf8mb4) COLLATE utf8mb4_unicode_ci
            = c.code COLLATE utf8mb4_unicode_ci
      WHERE c.code IS NULL) AS invalid_evidence_level_count,
    (SELECT COUNT(*)
       FROM te_common.ev_evidence_reference r
       LEFT JOIN te_common.cm_common_code c
         ON c.group_code = 'REFERENCE_TYPE'
        AND CONVERT(r.reference_type_code USING utf8mb4) COLLATE utf8mb4_unicode_ci
            = c.code COLLATE utf8mb4_unicode_ci
      WHERE c.code IS NULL) AS invalid_reference_type_count,
    (SELECT COUNT(*)
       FROM te_common.rl_rule r
       LEFT JOIN te_common.cm_common_code c
         ON c.group_code = 'RULE_TYPE'
        AND CONVERT(r.rule_type_code USING utf8mb4) COLLATE utf8mb4_unicode_ci
            = c.code COLLATE utf8mb4_unicode_ci
      WHERE c.code IS NULL) AS invalid_rule_type_count,
    (SELECT COUNT(*)
       FROM te_health_companion.at_audit a
       LEFT JOIN te_common.cm_common_code c
         ON c.group_code = 'AUDIT_TYPE'
        AND CONVERT(a.audit_type_code USING utf8mb4) COLLATE utf8mb4_unicode_ci
            = c.code COLLATE utf8mb4_unicode_ci
      WHERE c.code IS NULL) AS invalid_audit_type_count,
    (SELECT COUNT(*)
       FROM te_story_platform.sp_object_lifecycle l
       LEFT JOIN te_common.cm_common_code c
         ON c.group_code = 'OBJECT_LIFECYCLE_EVENT'
        AND CONVERT(l.lifecycle_event_code USING utf8mb4) COLLATE utf8mb4_unicode_ci
            = c.code COLLATE utf8mb4_unicode_ci
      WHERE c.code IS NULL) AS invalid_lifecycle_event_count;

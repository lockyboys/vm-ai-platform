-- Health Companion Common Code Registration and Comment Patch 20260721

CREATE TABLE IF NOT EXISTS te_common.cm_common_code_group_bkp_hc_code_20260721
LIKE te_common.cm_common_code_group;
INSERT INTO te_common.cm_common_code_group_bkp_hc_code_20260721
SELECT * FROM te_common.cm_common_code_group
WHERE NOT EXISTS (SELECT 1 FROM te_common.cm_common_code_group_bkp_hc_code_20260721 LIMIT 1);

CREATE TABLE IF NOT EXISTS te_common.cm_common_code_bkp_hc_code_20260721
LIKE te_common.cm_common_code;
INSERT INTO te_common.cm_common_code_bkp_hc_code_20260721
SELECT * FROM te_common.cm_common_code
WHERE NOT EXISTS (SELECT 1 FROM te_common.cm_common_code_bkp_hc_code_20260721 LIMIT 1);

CREATE TABLE IF NOT EXISTS te_health_companion.ac_action_bkp_hc_code_comment_20260721
LIKE te_health_companion.ac_action;
INSERT INTO te_health_companion.ac_action_bkp_hc_code_comment_20260721
SELECT * FROM te_health_companion.ac_action
WHERE NOT EXISTS (SELECT 1 FROM te_health_companion.ac_action_bkp_hc_code_comment_20260721 LIMIT 1);

CREATE TABLE IF NOT EXISTS te_health_companion.at_audit_bkp_hc_code_comment_20260721
LIKE te_health_companion.at_audit;
INSERT INTO te_health_companion.at_audit_bkp_hc_code_comment_20260721
SELECT * FROM te_health_companion.at_audit
WHERE NOT EXISTS (SELECT 1 FROM te_health_companion.at_audit_bkp_hc_code_comment_20260721 LIMIT 1);

CREATE TABLE IF NOT EXISTS te_health_companion.dc_decision_bkp_hc_code_comment_20260721
LIKE te_health_companion.dc_decision;
INSERT INTO te_health_companion.dc_decision_bkp_hc_code_comment_20260721
SELECT * FROM te_health_companion.dc_decision
WHERE NOT EXISTS (SELECT 1 FROM te_health_companion.dc_decision_bkp_hc_code_comment_20260721 LIMIT 1);

CREATE TABLE IF NOT EXISTS te_common.rl_rule_action_bkp_hc_code_comment_20260721
LIKE te_common.rl_rule_action;
INSERT INTO te_common.rl_rule_action_bkp_hc_code_comment_20260721
SELECT * FROM te_common.rl_rule_action
WHERE NOT EXISTS (SELECT 1 FROM te_common.rl_rule_action_bkp_hc_code_comment_20260721 LIMIT 1);

START TRANSACTION;

INSERT INTO te_common.cm_common_code_group (
    group_code, group_name, group_description, sort_no, status_code,
    reserved_yn, system_yn, created_by, updated_by, program_id
) VALUES
('ACTION_TYPE', 'Action 유형', 'Health Companion 및 Rule Engine Action의 수행 유형을 관리한다.', 300, 'ACTIVE', 'N', 'N', 'SYSTEM', 'SYSTEM', 'CM_CO_PROGRAM_20260721_000000_00001'),
('AI_PROVIDER', 'AI 제공자', '실제 외부 AI 호출을 수행한 공식 Provider Code를 관리한다. API Key 존재 또는 연동 예정만으로 Code를 기록하지 않는다.', 310, 'ACTIVE', 'N', 'N', 'SYSTEM', 'SYSTEM', 'CM_CO_PROGRAM_20260721_000000_00001'),
('DECISION_TYPE', 'Decision 유형', 'Health Companion Decision의 판단 유형을 관리한다.', 320, 'ACTIVE', 'N', 'N', 'SYSTEM', 'SYSTEM', 'CM_CO_PROGRAM_20260721_000000_00001')
ON DUPLICATE KEY UPDATE
    group_name=VALUES(group_name),
    group_description=VALUES(group_description),
    status_code='ACTIVE',
    updated_by='SYSTEM',
    program_id='CM_CO_PROGRAM_20260721_000000_00001';

INSERT INTO te_common.cm_common_code (
    group_code, code, code_name, common_code_description, sort_no,
    status_code, created_by, updated_by, program_id
) VALUES
('ACTION_TYPE', 'SAFE_MODE_ON', '안심모드 활성화', 'Health Companion 안심모드를 활성화하는 Action 유형.', 10, 'ACTIVE', 'SYSTEM', 'SYSTEM', 'CM_CO_PROGRAM_20260721_000000_00001'),
('ACTION_TYPE', 'HOSPITAL_RECOMMEND', '의료기관 추천', '건강 위험도에 따라 의료기관 안내를 수행하는 Action 유형.', 20, 'ACTIVE', 'SYSTEM', 'SYSTEM', 'CM_CO_PROGRAM_20260721_000000_00001'),
('ACTION_TYPE', 'HUMAN_REVIEW', '사람 검토', 'Rule Engine이 자동 처리 대신 담당자 검토를 요청하는 Action 유형.', 30, 'ACTIVE', 'SYSTEM', 'SYSTEM', 'CM_CO_PROGRAM_20260721_000000_00001'),
('DECISION_TYPE', 'HEALTH_RISK', '건강 위험 판단', '건강 상태와 Evidence를 기반으로 위험도를 판단하는 Decision 유형.', 10, 'ACTIVE', 'SYSTEM', 'SYSTEM', 'CM_CO_PROGRAM_20260721_000000_00001')
ON DUPLICATE KEY UPDATE
    code_name=VALUES(code_name),
    common_code_description=VALUES(common_code_description),
    status_code='ACTIVE',
    updated_by='SYSTEM',
    program_id='CM_CO_PROGRAM_20260721_000000_00001';

COMMIT;

ALTER TABLE te_common.rl_rule_action
MODIFY COLUMN action_type_code varchar(99) NOT NULL
COMMENT 'Rule Action 수행 유형 코드. SSOT: te_common.cm_common_code의 group_code=ACTION_TYPE. SAFE_MODE_ON, HOSPITAL_RECOMMEND, HUMAN_REVIEW 등 등록된 Code만 사용하며 Hardcoding하지 않는다.';

ALTER TABLE te_health_companion.ac_action
MODIFY COLUMN action_type_code varchar(99) NOT NULL
COMMENT 'Action 수행 유형 코드. SSOT: te_common.cm_common_code의 group_code=ACTION_TYPE. SAFE_MODE_ON, HOSPITAL_RECOMMEND, HUMAN_REVIEW 등 등록된 Code만 사용하며 Hardcoding하지 않는다.',
MODIFY COLUMN result_code varchar(99) DEFAULT NULL
COMMENT 'Action 처리 결과 코드. SSOT: te_common.cm_common_code의 group_code=CM_JOB_STATUS. READY, RUNNING, SUCCESS, FAIL, CANCEL 중 등록된 Code를 사용한다.';

ALTER TABLE te_health_companion.at_audit
MODIFY COLUMN audit_result_code varchar(99) NOT NULL DEFAULT 'SUCCESS'
COMMENT '감사 처리 결과 코드. SSOT: te_common.cm_common_code의 group_code=CM_JOB_STATUS. READY, RUNNING, SUCCESS, FAIL, CANCEL 중 등록된 Code를 사용한다.',
MODIFY COLUMN ai_provider_code varchar(99) DEFAULT NULL
COMMENT '실제 외부 AI 호출 Provider 코드. SSOT: te_common.cm_common_code의 group_code=AI_PROVIDER. API Key 존재 또는 연동 예정만으로 기록하지 않으며 실제 호출 Provider만 저장한다.';

ALTER TABLE te_health_companion.dc_decision
MODIFY COLUMN decision_type_code varchar(99) NOT NULL
COMMENT 'Decision 판단 유형 코드. SSOT: te_common.cm_common_code의 group_code=DECISION_TYPE. HEALTH_RISK 등 등록된 Code만 사용하며 Hardcoding하지 않는다.';

SELECT group_code, group_name, group_description, status_code
FROM te_common.cm_common_code_group
WHERE group_code IN ('ACTION_TYPE', 'AI_PROVIDER', 'DECISION_TYPE')
ORDER BY group_code;

SELECT group_code, code, code_name, common_code_description, status_code
FROM te_common.cm_common_code
WHERE group_code IN ('ACTION_TYPE', 'AI_PROVIDER', 'DECISION_TYPE')
ORDER BY group_code, sort_no, code;

SELECT table_schema, table_name, column_name, column_comment
FROM information_schema.columns
WHERE (table_schema, table_name, column_name) IN (
 ('te_common','rl_rule_action','action_type_code'),
 ('te_health_companion','ac_action','action_type_code'),
 ('te_health_companion','ac_action','result_code'),
 ('te_health_companion','at_audit','audit_result_code'),
 ('te_health_companion','at_audit','ai_provider_code'),
 ('te_health_companion','dc_decision','decision_type_code')
)
ORDER BY table_schema, table_name, ordinal_position;

SELECT
 (SELECT COUNT(*) FROM te_common.rl_rule_action r
  LEFT JOIN te_common.cm_common_code c
    ON c.group_code='ACTION_TYPE' AND c.code=r.action_type_code COLLATE utf8mb4_unicode_ci
  WHERE c.code IS NULL) AS invalid_rule_action_type_count,
 (SELECT COUNT(*) FROM te_health_companion.ac_action a
  LEFT JOIN te_common.cm_common_code c
    ON c.group_code='ACTION_TYPE' AND c.code=a.action_type_code COLLATE utf8mb4_unicode_ci
  WHERE c.code IS NULL) AS invalid_action_type_count,
 (SELECT COUNT(*) FROM te_health_companion.ac_action a
  LEFT JOIN te_common.cm_common_code c
    ON c.group_code='CM_JOB_STATUS' AND c.code=a.result_code COLLATE utf8mb4_unicode_ci
  WHERE a.result_code IS NOT NULL AND c.code IS NULL) AS invalid_result_count,
 (SELECT COUNT(*) FROM te_health_companion.at_audit a
  LEFT JOIN te_common.cm_common_code c
    ON c.group_code='CM_JOB_STATUS' AND c.code=a.audit_result_code COLLATE utf8mb4_unicode_ci
  WHERE c.code IS NULL) AS invalid_audit_result_count,
 (SELECT COUNT(*) FROM te_health_companion.at_audit a
  LEFT JOIN te_common.cm_common_code c
    ON c.group_code='AI_PROVIDER' AND c.code=a.ai_provider_code COLLATE utf8mb4_unicode_ci
  WHERE a.ai_provider_code IS NOT NULL AND c.code IS NULL) AS invalid_ai_provider_count,
 (SELECT COUNT(*) FROM te_health_companion.dc_decision d
  LEFT JOIN te_common.cm_common_code c
    ON c.group_code='DECISION_TYPE' AND c.code=d.decision_type_code COLLATE utf8mb4_unicode_ci
  WHERE c.code IS NULL) AS invalid_decision_type_count;

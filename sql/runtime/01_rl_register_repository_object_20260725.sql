/*
 * Repository Object registration Rule.
 * Rule Action resolves execution only through Action Metadata.
 */
USE te_common;

START TRANSACTION;

SET @program_id = 'RL_REGISTER_REPOSITORY_OBJECT_BATCH';
SET @client_ip = '127.0.0.1';
SET @rule_code = 'RL_REGISTER_REPOSITORY_OBJECT';
SET @rule_id = 'CM_CO_RULE_20260725_000001';
SET @action_code = 'REGISTER_REPOSITORY_OBJECT';

INSERT INTO rl_rule
(
    rule_id, rule_code, rule_name, rule_type_code, rule_group_code,
    rule_description, priority_no, status_code, version_num, remark, sort_no,
    created_by, updated_by, program_id, client_ip
)
VALUES
(
    @rule_id, @rule_code, 'Repository Object 등록 규칙',
    'LIFECYCLE', 'REPOSITORY_OBJECT',
    'Repository에 존재하고 공식 Object가 없는 경우 Action Metadata를 해석하여 등록한다.',
    100, 'ACTIVE', '1.0',
    '대상 및 실행 계약은 Repository Metadata에서 해석한다.',
    10, 'SYSTEM', 'SYSTEM', @program_id, @client_ip
)
ON DUPLICATE KEY UPDATE
    rule_name = VALUES(rule_name),
    rule_type_code = VALUES(rule_type_code),
    rule_group_code = VALUES(rule_group_code),
    rule_description = VALUES(rule_description),
    priority_no = VALUES(priority_no),
    status_code = VALUES(status_code),
    version_num = VALUES(version_num),
    remark = VALUES(remark),
    sort_no = VALUES(sort_no),
    updated_dt = CURRENT_TIMESTAMP,
    updated_by = VALUES(updated_by),
    program_id = VALUES(program_id),
    client_ip = VALUES(client_ip);

DELETE FROM rl_rule_condition WHERE rule_id = @rule_id;
DELETE FROM rl_rule_action WHERE rule_id = @rule_id;

INSERT INTO rl_rule_condition
(
    condition_id, rule_id, sort_no, field_code, operator_code,
    condition_value, logical_operator_code, remark,
    created_by, updated_by, program_id, client_ip, status_code
)
VALUES
(
    'CM_RL_CONDITION_20260725_000001', @rule_id, 10,
    'REPOSITORY_OBJECT_EXISTS', 'EQ', 'N', NULL,
    '대상 Repository Object의 등록 여부는 Repository Runtime이 제공한다.',
    'SYSTEM', 'SYSTEM', @program_id, @client_ip, 'ACTIVE'
);

INSERT INTO rl_rule_action
(
    rule_action_id, rule_id, action_type_code, action_value, sort_no, remark,
    created_by, updated_by, program_id, client_ip, status_code
)
SELECT
    'CM_RL_ACTION_20260725_000001',
    @rule_id,
    c.code,
    JSON_OBJECT(
        'action_code', c.code,
        'verified_query_id',
        JSON_UNQUOTE(JSON_EXTRACT(c.common_code_json, '$.verified_query_id'))
    ),
    10,
    'Action Metadata가 지정한 Verified Query와 Stored Procedure를 호출한다.',
    'SYSTEM', 'SYSTEM', @program_id, @client_ip, 'ACTIVE'
FROM cm_common_code c
WHERE c.group_code = 'ACTION_TYPE'
  AND c.code = @action_code
  AND c.status_code = 'ACTIVE'
  AND c.deleted_dt IS NULL
  AND JSON_UNQUOTE(JSON_EXTRACT(c.common_code_json, '$.active_yn')) = 'Y';

SELECT
    a.rule_action_id,
    a.action_type_code,
    JSON_UNQUOTE(JSON_EXTRACT(a.action_value, '$.verified_query_id')) AS verified_query_id
FROM rl_rule_action a
WHERE a.rule_id = @rule_id
ORDER BY a.sort_no, a.rule_action_id;

COMMIT;

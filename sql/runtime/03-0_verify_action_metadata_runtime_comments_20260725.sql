/*
 * Read-only review for Action Metadata Runtime COMMENT changes.
 *
 * Review current_comment and proposed_comment together.
 * This query does not change the database and does not grant execution approval.
 */

WITH column_proposals AS (
    SELECT 'cm_common_code' AS table_name,
           'common_code_json' AS column_name,
           '공통코드 Object의 구조화된 공식 JSON입니다. ACTION_TYPE 항목은 Verified Query 식별자와 실행 계약 정보를 저장할 수 있습니다.' AS proposed_comment,
           'Action Metadata 실행 계약 설명 추가' AS change_reason
    UNION ALL
    SELECT 'cm_verified_sql_query', 'query_description',
           'Verified SQL Query Object의 목적, 사용 범위 및 업무 설명입니다. Stored Procedure 실행 계약은 호출 Procedure, 입력값, 결과값, 트랜잭션 정책을 JSON으로 저장합니다.',
           'Stored Procedure 실행 계약 설명 추가'
    UNION ALL
    SELECT 'cm_verified_sql_query', 'sql_text',
           '검증 또는 실행이 승인된 SQL 또는 CALL 원문입니다. Repository에 보관하며 Stored Procedure Runtime은 이 문자열을 직접 실행하지 않고 실행 계약을 해석하여 Procedure를 호출합니다.',
           'Runtime 직접 SQL 실행 금지 설명 추가'
    UNION ALL
    SELECT 'rl_rule_action', 'action_value',
           'Rule Action의 실행 값입니다. Stored Procedure Runtime Action은 조회할 Verified Query 식별자를 JSON으로 저장합니다.',
           'Verified Query 연결 설명 추가'
)
SELECT
    'COLUMN' AS comment_type,
    c.table_schema,
    c.table_name,
    c.column_name AS target_name,
    c.column_comment AS current_comment,
    p.proposed_comment,
    p.change_reason,
    CASE WHEN c.column_comment <=> p.proposed_comment THEN 'UNCHANGED' ELSE 'REVIEW_REQUIRED' END AS review_status
FROM information_schema.columns c
JOIN column_proposals p
  ON p.table_name = c.table_name
 AND p.column_name = c.column_name
WHERE c.table_schema = 'te_common'
ORDER BY c.table_name, c.ordinal_position;

WITH table_proposals AS (
    SELECT
        table_name,
        CASE table_name
            WHEN 'cm_common_code' THEN
                'ACTION_TYPE 공통코드는 common_code_json에 Verified Query 식별자와 실행 계약을 저장할 수 있습니다.'
            WHEN 'cm_verified_sql_query' THEN
                'Stored Procedure Runtime은 이 Repository의 실행 계약을 해석하며 SQL 문자열을 직접 실행하지 않습니다.'
            WHEN 'rl_rule_action' THEN
                'Stored Procedure Runtime Action은 action_value의 verified_query_id로 Verified Query를 조회한 뒤 Procedure를 호출합니다.'
        END AS runtime_addendum
    FROM information_schema.tables
    WHERE table_schema = 'te_common'
      AND table_name IN ('cm_common_code', 'cm_verified_sql_query', 'rl_rule_action')
)
SELECT
    'TABLE' AS comment_type,
    t.table_schema,
    t.table_name,
    t.table_name AS target_name,
    t.table_comment AS current_comment,
    CONCAT(t.table_comment, '\n\n[Action Metadata Runtime]\n', p.runtime_addendum) AS proposed_comment,
    '기존 테이블 COMMENT 보존 후 Runtime 설명 추가' AS change_reason,
    'REVIEW_REQUIRED' AS review_status
FROM information_schema.tables t
JOIN table_proposals p
  ON p.table_name = t.table_name
WHERE t.table_schema = 'te_common'
ORDER BY t.table_name;

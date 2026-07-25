/*
 * Action Metadata Runtime COMMENT maintenance
 *
 * Scope:
 * - Existing `_code` comments and their cm_common_code references are preserved.
 * - Only Runtime execution-contract column comments are clarified.
 * - Before execution, review current_comment and proposed_comment from
 *   03-0_verify_action_metadata_runtime_comments_20260725.sql and approve the text.
 * - Table comments are intentionally excluded until their current text and
 *   proposed appended text are separately approved.
 * - No data type, nullability, default, index, key, or data change.
 */

ALTER TABLE te_common.cm_common_code
    MODIFY COLUMN common_code_json longtext DEFAULT NULL
    COMMENT '공통코드 Object의 구조화된 공식 JSON입니다. ACTION_TYPE 항목은 Verified Query 식별자와 실행 계약 정보를 저장할 수 있습니다.';

ALTER TABLE te_common.cm_verified_sql_query
    MODIFY COLUMN query_description varchar(2000) DEFAULT NULL
    COMMENT 'Verified SQL Query Object의 목적, 사용 범위 및 업무 설명입니다. Stored Procedure 실행 계약은 호출 Procedure, 입력값, 결과값, 트랜잭션 정책을 JSON으로 저장합니다.',
    MODIFY COLUMN sql_text longtext NOT NULL
    COMMENT '검증 또는 실행이 승인된 SQL 또는 CALL 원문입니다. Repository에 보관하며 Stored Procedure Runtime은 이 문자열을 직접 실행하지 않고 실행 계약을 해석하여 Procedure를 호출합니다.';

ALTER TABLE te_common.rl_rule_action
    MODIFY COLUMN action_value varchar(2000) DEFAULT NULL
    COMMENT 'Rule Action의 실행 값입니다. Stored Procedure Runtime Action은 조회할 Verified Query 식별자를 JSON으로 저장합니다.';

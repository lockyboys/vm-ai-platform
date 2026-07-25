/*
 * Action Metadata Runtime COMMENT maintenance
 *
 * Scope:
 * - Existing `_code` comments and their cm_common_code references are preserved.
 * - Only Runtime execution-contract column comments are clarified.
 * - Table comments are intentionally excluded until the current comments are
 *   read and approved through 03-0_verify_action_metadata_runtime_comments_20260725.sql.
 * - No data type, nullability, default, index, key, or data change.
 */

ALTER TABLE te_common.cm_common_code
    MODIFY COLUMN common_code_json longtext DEFAULT NULL
    COMMENT '공통코드의 구조화된 공식 JSON입니다. ACTION_TYPE 항목은 Verified Query 식별자와 실행 계약 정보를 저장할 수 있습니다.';

ALTER TABLE te_common.cm_verified_sql_query
    MODIFY COLUMN query_description varchar(2000) DEFAULT NULL
    COMMENT 'Verified Query의 목적과 Stored Procedure 실행 계약을 설명하는 JSON입니다. 호출 Procedure, 입력값, 결과값, 트랜잭션 정책을 저장합니다.',
    MODIFY COLUMN sql_text longtext NOT NULL
    COMMENT '검증·승인된 SQL 또는 CALL 원문입니다. Stored Procedure Runtime은 이 문자열을 직접 실행하지 않고 실행 계약을 해석하여 Procedure를 호출합니다.';

ALTER TABLE te_common.rl_rule_action
    MODIFY COLUMN action_value varchar(2000) DEFAULT NULL
    COMMENT 'Rule Action의 실행 정보입니다. Stored Procedure Runtime Action은 조회할 Verified Query 식별자를 JSON으로 저장합니다.';

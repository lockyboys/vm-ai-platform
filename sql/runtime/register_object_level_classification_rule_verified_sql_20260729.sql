/*
 * SPS Verified SQL registration for the Object Level Classification Rule.
 *
 * 20260729 | SYSTEM | cm_verified_sql_query에 Object Level Classification Rule
 * 등록 Batch 원문과 SHA-256 검증 근거를 등록한다.
 *
 * Preconditions
 * - @verified_sql_query_id: Identifier Engine output for the SQL Query target.
 * - Do not manually construct the identifier.
 * - No DB structure change.
 */

USE te_common;

START TRANSACTION;

-- @verified_sql_query_id must be set by Identifier Engine before this batch runs.
SET @program_id = 'OBJECT_LEVEL_CLASSIFICATION_RULE_VERIFIED_SQL_REGISTRAR';
SET @client_ip = '127.0.0.1';

SELECT CASE
    WHEN @verified_sql_query_id IS NULL OR @verified_sql_query_id = ''
        THEN 'IDENTIFIER_ENGINE_VERIFIED_SQL_QUERY_ID_REQUIRED'
    ELSE 'READY'
END AS registration_status;

SET @verified_sql_text = CONCAT(
    'START TRANSACTION;', CHAR(10),
    'SET @rule_id = :rule_id; -- Identifier Engine output required.', CHAR(10),
    'SET @program_id = ''OBJECT_LEVEL_CLASSIFICATION_RULE_REGISTRAR'';', CHAR(10),
    'SET @client_ip = ''127.0.0.1'';', CHAR(10), CHAR(10),
    'INSERT INTO rl_rule (', CHAR(10),
    '    rule_id, rule_code, rule_name, rule_type_code, rule_group_code,', CHAR(10),
    '    rule_description, priority_no, status_code, version_num, remark, sort_no,', CHAR(10),
    '    created_by, updated_by, program_id, client_ip', CHAR(10),
    ') VALUES (', CHAR(10),
    '    @rule_id, ''RL_OBJECT_LEVEL_CLASSIFICATION'', ''SPS Object Level 분류 규칙'',', CHAR(10),
    '    ''LIFECYCLE'', ''OBJECT_LEVEL'',', CHAR(10),
    '    ''cm_data_classification.classification_id는 데이터 성격별 그룹이므로 Level 2이고, sp_erd.erd_id는 ERD 구조·범위이므로 Level 2이다. sp_object.object_id는 SPS 관리 Object의 공식 식별자이며 대상 정체에 따라 Level 0~5이다. 물리 저장 테이블을 Table Object로 등록한 object_id는 Level 3이고, 별도 Object로 등록한 Attribute·Relationship Attribute는 Level 4이다. 테이블 PK 한 건은 무조건 Level 4가 아니며 그 ID가 표현하는 대상 정체로 결정한다. 테이블명, _log/_history/_result 접미사, 저장 위치, SELECT 행위는 Level 결정 기준이 아니다.'',', CHAR(10),
    '    100, ''ACTIVE'', ''1.0'',', CHAR(10),
    '    ''Repository First, Metadata Driven, Single Source of Truth, Hardcoding Prohibited.'',', CHAR(10),
    '    10, ''SYSTEM'', ''SYSTEM'', @program_id, @client_ip', CHAR(10),
    ') ON DUPLICATE KEY UPDATE', CHAR(10),
    '    rule_name = VALUES(rule_name),', CHAR(10),
    '    rule_type_code = VALUES(rule_type_code),', CHAR(10),
    '    rule_group_code = VALUES(rule_group_code),', CHAR(10),
    '    rule_description = VALUES(rule_description),', CHAR(10),
    '    priority_no = VALUES(priority_no),', CHAR(10),
    '    status_code = VALUES(status_code),', CHAR(10),
    '    version_num = VALUES(version_num),', CHAR(10),
    '    remark = VALUES(remark),', CHAR(10),
    '    sort_no = VALUES(sort_no),', CHAR(10),
    '    updated_dt = CURRENT_TIMESTAMP,', CHAR(10),
    '    updated_by = VALUES(updated_by),', CHAR(10),
    '    program_id = VALUES(program_id),', CHAR(10),
    '    client_ip = VALUES(client_ip);', CHAR(10),
    'COMMIT;'
);

INSERT INTO cm_verified_sql_query
(
    query_id,
    query_name,
    query_description,
    crud_type,
    sql_text,
    verified_yn,
    certified_level_code,
    verification_description,
    created_by,
    verified_by,
    verified_dt,
    updated_dt,
    updated_by,
    story_programming_rule_pass_yn,
    snake_case_pass_yn,
    table_exists_pass_yn,
    column_exists_pass_yn,
    crud_match_pass_yn,
    where_clause_pass_yn,
    status_code,
    program_id,
    client_ip
)
SELECT
    @verified_sql_query_id,
    'SPS Object Level 분류 Rule 등록 Batch',
    'SOURCE_FILE: sql/runtime/register_object_level_classification_rule_20260729.sql. SPS Object Level Classification Rule을 rl_rule Repository에 등록·갱신하는 공식 SQL 원문이다.',
    'BATCH',
    @verified_sql_text,
    'Y',
    'A',
    CONCAT(
        'cm_verified_sql_query와 rl_rule 실제 Schema 및 Object Level 확정 기준 검증 완료. SHA256=',
        SHA2(@verified_sql_text, 256),
        '; Identifier Engine 발급 ID 사용.'
    ),
    'SYSTEM',
    'SYSTEM',
    CURRENT_TIMESTAMP,
    CURRENT_TIMESTAMP,
    'SYSTEM',
    'Y',
    'Y',
    'Y',
    'Y',
    'Y',
    'Y',
    'ACTIVE',
    @program_id,
    @client_ip
WHERE @verified_sql_query_id IS NOT NULL
  AND @verified_sql_query_id <> ''
ON DUPLICATE KEY UPDATE
    query_name = VALUES(query_name),
    query_description = VALUES(query_description),
    crud_type = VALUES(crud_type),
    sql_text = VALUES(sql_text),
    verified_yn = VALUES(verified_yn),
    certified_level_code = VALUES(certified_level_code),
    verification_description = VALUES(verification_description),
    verified_by = VALUES(verified_by),
    verified_dt = VALUES(verified_dt),
    updated_dt = CURRENT_TIMESTAMP,
    updated_by = VALUES(updated_by),
    story_programming_rule_pass_yn = VALUES(story_programming_rule_pass_yn),
    snake_case_pass_yn = VALUES(snake_case_pass_yn),
    table_exists_pass_yn = VALUES(table_exists_pass_yn),
    column_exists_pass_yn = VALUES(column_exists_pass_yn),
    crud_match_pass_yn = VALUES(crud_match_pass_yn),
    where_clause_pass_yn = VALUES(where_clause_pass_yn),
    status_code = VALUES(status_code),
    deleted_dt = NULL,
    deleted_by = NULL,
    program_id = VALUES(program_id),
    client_ip = VALUES(client_ip);

SELECT
    query_id,
    query_name,
    crud_type,
    verified_yn,
    certified_level_code,
    verification_description,
    status_code
FROM cm_verified_sql_query
WHERE query_id = @verified_sql_query_id
  AND deleted_dt IS NULL;

COMMIT;

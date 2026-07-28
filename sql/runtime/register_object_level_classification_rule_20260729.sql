/*
 * SPS Object Level Classification Rule registration.
 *
 * Purpose
 * - Register the official Level classification rule without changing DB structure.
 *
 * Source of truth
 * - cm_data_classification.classification_id represents a data-character group:
 *   Level 2.
 * - sp_erd.erd_id represents an ERD structure and scope: Level 2.
 * - sp_object.object_id is the official SPS-managed Object identifier. Its
 *   object_level is Level 0 through Level 5, determined only by the Object's
 *   identity and Repository metadata.
 *
 * Base identity rules
 * - A physical storage table, when registered as a Table Object with object_id,
 *   is Level 3.
 * - An Attribute or Relationship-Attribute, when separately registered as an
 *   Object with object_id, is Level 4.
 * - A table primary-key row is not universally Level 4. Its Level is determined
 *   by the identity represented by that ID.
 * - A table name, suffix (_log, _history, _result), or SELECT operation must not
 *   determine Object Level.
 *
 * Negative rules
 * - Reject an Object Level outside 0 through 5.
 * - Reject a Level derived solely from a table name, suffix, primary-key shape,
 *   stored-table location, or SQL operation.
 * - Do not create a new object_id merely because a repository row is stored in a table.
 *
 * Identifier requirement
 * - Before execution, assign @rule_id with Identifier Engine output for the Rule target.
 * - Do not replace @rule_id with a manually constructed identifier.
 */

USE te_common;

START TRANSACTION;

-- Input from Identifier Engine. This script must not overwrite this identifier.
-- @rule_id must be set before this batch runs.
SET @program_id = 'OBJECT_LEVEL_CLASSIFICATION_RULE_REGISTRAR';
SET @client_ip = '127.0.0.1';

-- Stop safely until Identifier Engine supplies the official Rule ID.
SELECT CASE
    WHEN @rule_id IS NULL OR @rule_id = ''
        THEN 'IDENTIFIER_ENGINE_RULE_ID_REQUIRED'
    ELSE 'READY'
END AS registration_status;

INSERT INTO rl_rule
(
    rule_id,
    rule_code,
    rule_name,
    rule_type_code,
    rule_group_code,
    rule_description,
    priority_no,
    status_code,
    version_num,
    remark,
    sort_no,
    created_by,
    updated_by,
    program_id,
    client_ip
)
SELECT
    @rule_id,
    'RL_OBJECT_LEVEL_CLASSIFICATION',
    'SPS Object Level 분류 규칙',
    'LIFECYCLE',
    'OBJECT_LEVEL',
    'cm_data_classification.classification_id는 데이터 성격별 그룹이므로 Level 2이고, sp_erd.erd_id는 ERD 구조·범위이므로 Level 2이다. sp_object.object_id는 SPS 관리 Object의 공식 식별자이며 대상 정체에 따라 Level 0~5이다. 물리 저장 테이블을 Table Object로 등록한 object_id는 Level 3이고, 별도 Object로 등록한 Attribute·Relationship Attribute는 Level 4이다. 테이블 PK 한 건은 무조건 Level 4가 아니며 그 ID가 표현하는 대상 정체로 결정한다. 테이블명, _log/_history/_result 접미사, 저장 위치, SELECT 행위는 Level 결정 기준이 아니다.',
    100,
    'ACTIVE',
    '1.0',
    'Repository First, Metadata Driven, Single Source of Truth, Hardcoding Prohibited.',
    10,
    'SYSTEM',
    'SYSTEM',
    @program_id,
    @client_ip
WHERE @rule_id IS NOT NULL
  AND @rule_id <> ''
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

SELECT
    rule_id,
    rule_code,
    rule_name,
    rule_type_code,
    rule_group_code,
    rule_description,
    status_code,
    version_num
FROM rl_rule
WHERE rule_code = 'RL_OBJECT_LEVEL_CLASSIFICATION'
  AND deleted_dt IS NULL;

COMMIT;

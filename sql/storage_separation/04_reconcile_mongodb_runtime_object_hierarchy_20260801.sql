/*
 * File Story
 * Common Repository의 MongoDB Runtime Object Definition과 이미 등록된 SPS Object를 동기화한다.
 *
 * Change History
 * 20260801 | Codex | SPS Platform Level 0 및 MCO/MCM 계층 정정 값을 기존 Object ID를 보존하며 반영한다.
 *
 * DB 구조는 변경하지 않는다.
 */
USE te_story_platform;

START TRANSACTION;

SET @program_id = 'RECONCILE_MONGODB_RUNTIME_OBJECT_HIERARCHY_20260801';
SET @actor_id = 'SYSTEM';
SET @client_ip = '127.0.0.1';

UPDATE sp_object
SET
    object_name = 'SPS Platform',
    object_description = 'Story Programming System의 최상위 Platform Object. MongoDB Runtime Object 계층의 Level 0 기준점이다.',
    object_level = 0,
    updated_dt = CURRENT_TIMESTAMP,
    updated_by = @actor_id,
    client_ip = @client_ip,
    program_id = @program_id
WHERE object_code = 'STORY_PROGRAMMING_PLATFORM'
  AND object_type_code = 'PLATFORM'
  AND status_code = 'ACTIVE'
  AND active_yn = 'Y'
  AND deleted_dt IS NULL;

UPDATE sp_object AS object_repository
JOIN te_common.cm_common_code AS definition_code
  ON BINARY definition_code.group_code = BINARY 'MONGODB_RUNTIME_OBJECT_DEFINITION'
 AND BINARY definition_code.code = BINARY object_repository.object_code
 AND BINARY definition_code.status_code = BINARY 'ACTIVE'
 AND definition_code.deleted_dt IS NULL
SET
    object_repository.object_name = JSON_UNQUOTE(JSON_EXTRACT(definition_code.common_code_json, '$.object_name')),
    object_repository.object_description = JSON_UNQUOTE(JSON_EXTRACT(definition_code.common_code_json, '$.object_description')),
    object_repository.business_code = JSON_UNQUOTE(JSON_EXTRACT(definition_code.common_code_json, '$.business_code')),
    object_repository.domain_code = JSON_UNQUOTE(JSON_EXTRACT(definition_code.common_code_json, '$.domain_code')),
    object_repository.object_type_code = JSON_UNQUOTE(JSON_EXTRACT(definition_code.common_code_json, '$.object_type_code')),
    object_repository.object_level = CAST(JSON_UNQUOTE(JSON_EXTRACT(definition_code.common_code_json, '$.object_level')) AS UNSIGNED),
    object_repository.target_identifier_field = JSON_UNQUOTE(JSON_EXTRACT(definition_code.common_code_json, '$.target_identifier_field')),
    object_repository.identifier_target_code = JSON_UNQUOTE(JSON_EXTRACT(definition_code.common_code_json, '$.identifier_target_code')),
    object_repository.sequence_scope_code = JSON_UNQUOTE(JSON_EXTRACT(definition_code.common_code_json, '$.sequence_scope_code')),
    object_repository.sequence_length = CAST(JSON_UNQUOTE(JSON_EXTRACT(definition_code.common_code_json, '$.sequence_length')) AS UNSIGNED),
    object_repository.updated_dt = CURRENT_TIMESTAMP,
    object_repository.updated_by = @actor_id,
    object_repository.client_ip = @client_ip,
    object_repository.program_id = @program_id
WHERE object_repository.status_code = 'ACTIVE'
  AND object_repository.active_yn = 'Y'
  AND object_repository.deleted_dt IS NULL;

SELECT
    object_id,
    object_code,
    object_name,
    object_type_code,
    object_level,
    target_identifier_field,
    identifier_target_code
FROM sp_object
WHERE object_code IN ('STORY_PROGRAMMING_PLATFORM', 'MDB', 'MCO', 'MCM', 'MDD')
  AND status_code = 'ACTIVE'
  AND active_yn = 'Y'
  AND deleted_dt IS NULL
ORDER BY object_level, object_code;

COMMIT;

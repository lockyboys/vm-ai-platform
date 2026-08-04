/*
 * Identifier Blueprint SSOT를 sp_identifier_blueprint에서
 * te_common.cm_common_code(SPS_IDENTIFIER_BLUEPRINT)로 이관한다.
 * 테이블·컬럼 구조는 변경하지 않는다.
 */
START TRANSACTION;

INSERT INTO te_common.cm_common_code
(
    group_code, code, code_name, common_code_description, sort_no,
    status_code, created_by, updated_by, client_ip, program_id,
    common_code_json, lifecycle_status_code
)
SELECT
    'SPS_IDENTIFIER_BLUEPRINT',
    blueprint_code,
    blueprint_name,
    remark,
    sort_no,
    'ACTIVE',
    'SYSTEM',
    'SYSTEM',
    client_ip,
    'MIGRATE_IDENTIFIER_BLUEPRINT_COMMON_CODE_20260731',
    JSON_OBJECT(
        'object_level', object_level,
        'identifier_pattern', identifier_pattern,
        'date_format', date_format,
        'time_format', time_format,
        'random_length', random_length,
        'sequence_length', sequence_length,
        'sequence_scope_code', sequence_scope_code
    ),
    'CREATE_MAINTAIN'
FROM te_story_platform.sp_identifier_blueprint
WHERE enabled_yn = 'Y'
  AND status_code = 'ACTIVE'
  AND deleted_dt IS NULL
ON DUPLICATE KEY UPDATE
    code_name = VALUES(code_name),
    common_code_description = VALUES(common_code_description),
    sort_no = VALUES(sort_no),
    status_code = VALUES(status_code),
    updated_dt = CURRENT_TIMESTAMP,
    updated_by = VALUES(updated_by),
    deleted_by = NULL,
    deleted_dt = NULL,
    client_ip = VALUES(client_ip),
    program_id = VALUES(program_id),
    common_code_json = VALUES(common_code_json),
    lifecycle_status_code = VALUES(lifecycle_status_code);

SELECT
    code AS blueprint_code,
    JSON_UNQUOTE(JSON_EXTRACT(common_code_json, '$.object_level')) AS object_level,
    JSON_UNQUOTE(JSON_EXTRACT(common_code_json, '$.identifier_pattern')) AS identifier_pattern,
    JSON_UNQUOTE(JSON_EXTRACT(common_code_json, '$.sequence_scope_code')) AS sequence_scope_code,
    JSON_UNQUOTE(JSON_EXTRACT(common_code_json, '$.sequence_length')) AS sequence_length
FROM te_common.cm_common_code
WHERE group_code = 'SPS_IDENTIFIER_BLUEPRINT'
  AND JSON_EXTRACT(common_code_json, '$.object_level') IS NOT NULL
  AND status_code = 'ACTIVE'
  AND deleted_dt IS NULL
ORDER BY sort_no, code;

COMMIT;

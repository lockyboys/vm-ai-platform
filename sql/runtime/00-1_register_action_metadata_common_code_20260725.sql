/*
 * Action Metadata common-code registration.
 * DB schema is unchanged: execution contracts are Repository metadata.
 */
USE te_common;

START TRANSACTION;

SET @program_id = 'ACTION_METADATA_COMMON_CODE_20260725';
SET @action_code = 'REGISTER_REPOSITORY_OBJECT';
SET @verified_query_id = 'SP_RP_SQL_QUERY_20260725_REGISTER_REPOSITORY_OBJECT_00001';
SET @procedure_name = 'sp_register_repository_object';

INSERT INTO cm_common_code
(
    group_code, code, code_name, common_code_description, sort_no,
    status_code, created_by, updated_by, client_ip, program_id,
    common_code_json, lifecycle_status_code
)
SELECT
    'ACTION_TYPE',
    @action_code,
    'Repository Object 등록',
    'Rule Action이 Verified Query 계약을 통해 Repository Object 등록 Stored Procedure를 호출하도록 정의한다.',
    120,
    'ACTIVE',
    'SYSTEM',
    'SYSTEM',
    @client_ip,
    @program_id,
    JSON_OBJECT(
        'action_code', @action_code,
        'action_name', 'Repository Object 등록',
        'verified_query_id', @verified_query_id,
        'procedure_name', @procedure_name,
        'parameter_schema', JSON_OBJECT(
            'type', 'object',
            'required', JSON_ARRAY(
                'object_id', 'object_code', 'object_name', 'business_code',
                'domain_code', 'object_type_code', 'object_level',
                'status_code', 'active_yn', 'created_by', 'program_id'
            )
        ),
        'result_schema', JSON_OBJECT(
            'type', 'object',
            'required', JSON_ARRAY('object_id', 'registered_yn')
        ),
        'transaction_required_yn', 'Y',
        'rollback_policy', 'ROLLBACK_ON_ERROR',
        'timeout_seconds', 30,
        'active_yn', 'Y',
        'repository_first', TRUE,
        'generator_first', TRUE,
        'hardcoding_allowed', FALSE
    ),
    'CREATE_MAINTAIN'
WHERE EXISTS
(
    SELECT 1
    FROM cm_common_code_group
    WHERE group_code = 'ACTION_TYPE'
      AND status_code = 'ACTIVE'
)
ON DUPLICATE KEY UPDATE
    code_name = VALUES(code_name),
    common_code_description = VALUES(common_code_description),
    sort_no = VALUES(sort_no),
    status_code = VALUES(status_code),
    updated_dt = CURRENT_TIMESTAMP,
    updated_by = VALUES(updated_by),
    client_ip = VALUES(client_ip),
    program_id = VALUES(program_id),
    common_code_json = VALUES(common_code_json),
    lifecycle_status_code = VALUES(lifecycle_status_code);

SELECT
    code AS action_code,
    JSON_UNQUOTE(JSON_EXTRACT(common_code_json, '$.verified_query_id')) AS verified_query_id,
    JSON_UNQUOTE(JSON_EXTRACT(common_code_json, '$.procedure_name')) AS procedure_name
FROM cm_common_code
WHERE group_code = 'ACTION_TYPE'
  AND code = @action_code
  AND status_code = 'ACTIVE'
  AND deleted_dt IS NULL;

COMMIT;

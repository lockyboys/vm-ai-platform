-- File Story: CM Verified SQL Query repository contract registration.
-- Change History: 20260729 | Codex | Register CM prefix/domain and cm_verified_sql_query Identifier metadata.
-- Scope: DML only. Database structure is not changed.
-- Contract: table_prefix_domain_code_map CM -> CO;
--           table_identifier_metadata cm_verified_sql_query.query_id -> SQ.

SET @program_id = 'REGISTER_CM_VERIFIED_SQL_QUERY_CONTRACT_20260729';

UPDATE cm_common_code
SET common_code_json = JSON_SET(
        COALESCE(common_code_json, JSON_OBJECT()),
        '$.table_prefix_domain_code_map.CM',
        'CO',
        '$.table_identifier_metadata.cm_verified_sql_query',
        JSON_OBJECT(
            'target_identifier_field', 'query_id',
            'identifier_target_code', 'SQ'
        )
    ),
    updated_by = 'SYSTEM',
    client_ip = '127.0.0.1',
    program_id = @program_id
WHERE group_code = 'ACTION_TYPE'
  AND code = 'REGISTER_REPOSITORY_OBJECT'
  AND status_code = 'ACTIVE'
  AND deleted_dt IS NULL;

SELECT
    group_code,
    code,
    JSON_UNQUOTE(JSON_EXTRACT(common_code_json, '$.table_prefix_domain_code_map.CM'))
        AS cm_domain_code,
    JSON_UNQUOTE(
        JSON_EXTRACT(
            common_code_json,
            '$.table_identifier_metadata.cm_verified_sql_query.target_identifier_field'
        )
    ) AS cm_verified_sql_query_target_identifier_field,
    JSON_UNQUOTE(
        JSON_EXTRACT(
            common_code_json,
            '$.table_identifier_metadata.cm_verified_sql_query.identifier_target_code'
        )
    ) AS cm_verified_sql_query_identifier_target_code
FROM cm_common_code
WHERE group_code = 'ACTION_TYPE'
  AND code = 'REGISTER_REPOSITORY_OBJECT'
  AND status_code = 'ACTIVE'
  AND deleted_dt IS NULL;

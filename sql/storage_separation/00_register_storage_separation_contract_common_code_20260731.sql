-- =============================================================================
-- File Story
-- =============================================================================
-- Storage Separation Target 공통코드 계약을 등록한다.
-- Runtime은 이 계약을 읽어 MariaDB Index와 MongoDB payload를 분리한다.
-- MongoDB 연결은 sp_object_execution_link만 사용한다.
--
-- Change History
-- 20260731 | SYSTEM | Storage Separation Target 계약을 등록하여 대상별 SSOT와 payload 분리 기준을 Metadata로 관리한다.
-- 20260829 | CODEX | MongoDB Payload Field를 계약으로 분리하여 MariaDB 원본 컬럼명과 MongoDB 문서 필드를 독립 관리한다.
-- =============================================================================

SET NAMES utf8mb4;
SET @program_id := 'REGISTER_STORAGE_SEPARATION_CONTRACT_20260731';
SET @actor_id := 'SYSTEM';
SET @client_ip := '127.0.0.1';

INSERT INTO cm_common_code_group
(
    group_code,
    group_name,
    group_description,
    sort_no,
    status_code,
    reserved_yn,
    system_yn,
    created_by,
    updated_by,
    client_ip,
    program_id,
    lifecycle_status_code
)
VALUES
(
    'STORAGE_SEPARATION_TARGET',
    'Storage Separation Target',
    'MariaDB Index와 MongoDB Document의 SSOT 경계, payload field 및 Execution Link 계약을 관리한다.',
    350,
    'ACTIVE',
    'Y',
    'Y',
    @actor_id,
    @actor_id,
    @client_ip,
    @program_id,
    'CREATE_MAINTAIN'
)
ON DUPLICATE KEY UPDATE
    group_name = VALUES(group_name),
    group_description = VALUES(group_description),
    sort_no = VALUES(sort_no),
    status_code = VALUES(status_code),
    reserved_yn = VALUES(reserved_yn),
    system_yn = VALUES(system_yn),
    updated_by = VALUES(updated_by),
    updated_dt = CURRENT_TIMESTAMP,
    client_ip = VALUES(client_ip),
    program_id = VALUES(program_id),
    lifecycle_status_code = VALUES(lifecycle_status_code);


INSERT INTO cm_common_code
(
    group_code,
    code,
    code_name,
    common_code_description,
    sort_no,
    status_code,
    created_by,
    updated_by,
    client_ip,
    program_id,
    common_code_json,
    lifecycle_status_code
)
VALUES
(
    'STORAGE_SEPARATION_TARGET',
    'RUNTIME_EXECUTION_PAYLOAD',
    'Runtime Execution Payload',
    'sp_execution_history의 상태·추적 Index와 MongoDB 실행 상세 payload를 분리한다.',
    10,
    'ACTIVE',
    @actor_id,
    @actor_id,
    @client_ip,
    @program_id,
    JSON_OBJECT(
        'source_database_role', 'STORY',
        'mongodb_database_role', 'STORY',
        'source_table_name', 'sp_execution_history',
        'source_object_code', 'EXECUTION_HISTORY',
        'source_identifier_column_name', 'execution_history_id',
        'mariadb_ssot', 'INDEX_ONLY',
        'mongodb_collection_name', 'runtime_execution_payload',
        'mongodb_ssot', 'EXECUTION_PAYLOAD',
        'payload_column_names', JSON_ARRAY(),
        'execution_link_required_yn', 'Y',
        'execution_link_type_code', 'MONGODB',
        'migration_mode_code', 'FUTURE_PAYLOAD'
    ),
    'CREATE_MAINTAIN'
),
(
    'STORAGE_SEPARATION_TARGET',
    'HEALTH_REPORT_CONTENT',
    'Health Report Content',
    'health_report의 patient·title·status Index는 MariaDB에 유지하고 report_content 원문은 MongoDB로 분리한다.',
    20,
    'ACTIVE',
    @actor_id,
    @actor_id,
    @client_ip,
    @program_id,
    JSON_OBJECT(
        'source_database_role', 'COMMON',
        'source_table_name', 'health_report',
        'source_object_code', 'TE_COMMON_HEALTH_REPORT',
        'source_identifier_column_name', 'health_report_id',
        'mariadb_ssot', 'REPORT_INDEX',
        'mongodb_collection_name', 'health_report_content',
        'mongodb_ssot', 'REPORT_CONTENT',
        'payload_column_names', JSON_ARRAY('report_content'),
        'execution_link_required_yn', 'Y',
        'execution_link_type_code', 'MONGODB',
        'migration_mode_code', 'MOVE_PAYLOAD'
    ),
    'CREATE_MAINTAIN'
),
(
    'STORAGE_SEPARATION_TARGET',
    'SQL_GUARD_EXECUTION_DETAIL',
    'SQL Guard Execution Detail',
    'sql_guard_execution_log의 조건 조회용 실행 Index는 MariaDB에 유지하고 error_message 상세는 MongoDB로 분리한다.',
    30,
    'ACTIVE',
    @actor_id,
    @actor_id,
    @client_ip,
    @program_id,
    JSON_OBJECT(
        'source_database_role', 'COMMON',
        'source_table_name', 'sql_guard_execution_log',
        'source_object_code', 'TE_COMMON_SQL_GUARD_EXECUTION_LOG',
        'source_identifier_column_name', 'execution_id',
        'mariadb_ssot', 'EXECUTION_INDEX',
        'mongodb_collection_name', 'sql_guard_executionr_message',
        'mongodb_ssot', 'EXECUTION_ERROR_DETAIL',
        'payload_column_names', JSON_ARRAY('error_message'),
        'execution_link_required_yn', 'Y',
        'execution_link_type_code', 'MONGODB',
        'migration_mode_code', 'MOVE_PAYLOAD'
    ),
    'CREATE_MAINTAIN'
),
(
    'STORAGE_SEPARATION_TARGET',
    'SQL_GUARD_VERIFICATION_DETAIL',
    'SQL Guard Verification Detail',
    'sql_guard_verification_log의 단계·판정 Index는 MariaDB에 유지하고 message 상세는 MongoDB로 분리한다.',
    40,
    'ACTIVE',
    @actor_id,
    @actor_id,
    @client_ip,
    @program_id,
    JSON_OBJECT(
        'source_database_role', 'COMMON',
        'source_table_name', 'sql_guard_verification_log',
        'source_object_code', 'TE_COMMON_SQL_GUARD_VERIFICATION_LOG',
        'source_identifier_column_name', 'log_id',
        'mariadb_ssot', 'VERIFICATION_INDEX',
        'mongodb_collection_name', 'sql_guard_verification_log',
        'mongodb_ssot', 'VERIFICATION_MESSAGE_DETAIL',
        'payload_column_names', JSON_ARRAY('message'),
        'mongodb_payload_field_name', 'sql_guard_verification_message',
        'execution_link_required_yn', 'Y',
        'execution_link_type_code', 'MONGODB',
        'migration_mode_code', 'MOVE_PAYLOAD'
    ),
    'CREATE_MAINTAIN'
)
ON DUPLICATE KEY UPDATE
    code_name = VALUES(code_name),
    common_code_description = VALUES(common_code_description),
    sort_no = VALUES(sort_no),
    status_code = VALUES(status_code),
    updated_by = VALUES(updated_by),
    updated_dt = CURRENT_TIMESTAMP,
    client_ip = VALUES(client_ip),
    program_id = VALUES(program_id),
    common_code_json = VALUES(common_code_json),
    lifecycle_status_code = VALUES(lifecycle_status_code);

-- MOVE_PAYLOAD 계약은 source_clear 실행에 사용할 감사 파라미터를 반드시 선언한다.
UPDATE cm_common_code
SET common_code_json = JSON_SET(common_code_json, '$.source_clear_parameter_codes', JSON_ARRAY('actor_id', 'program_id', 'client_ip', 'source_identifier')),
    updated_by = @actor_id, updated_dt = CURRENT_TIMESTAMP, program_id = @program_id, client_ip = @client_ip
WHERE group_code = 'STORAGE_SEPARATION_TARGET'
  AND status_code = 'ACTIVE'
  AND JSON_UNQUOTE(JSON_EXTRACT(common_code_json, '$.migration_mode_code')) = 'MOVE_PAYLOAD'
  AND (JSON_EXTRACT(common_code_json, '$.source_clear_parameter_codes') IS NULL OR JSON_LENGTH(JSON_EXTRACT(common_code_json, '$.source_clear_parameter_codes')) = 0);

SELECT
    group_code,
    code,
    code_name,
    JSON_UNQUOTE(JSON_EXTRACT(common_code_json, '$.source_table_name')) AS source_table_name,
    JSON_UNQUOTE(JSON_EXTRACT(common_code_json, '$.mongodb_collection_name')) AS mongodb_collection_name,
    JSON_UNQUOTE(JSON_EXTRACT(common_code_json, '$.mariadb_ssot')) AS mariadb_ssot,
    JSON_UNQUOTE(JSON_EXTRACT(common_code_json, '$.mongodb_ssot')) AS mongodb_ssot,
    JSON_UNQUOTE(JSON_EXTRACT(common_code_json, '$.migration_mode_code')) AS migration_mode_code
FROM cm_common_code
WHERE group_code = 'STORAGE_SEPARATION_TARGET'
ORDER BY sort_no, code;

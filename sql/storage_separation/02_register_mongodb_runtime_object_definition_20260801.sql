/*
 * File Story
 * SPS Platform을 최상위로 하는 MongoDB Runtime Object Definition을 Common Repository metadata로 등록한다.
 *
 * Change History
 * 20260801 | Codex | MongoDB 계층 Object 정의를 Identifier Engine 입력 계약으로 멱등 등록한다.
 * 20260801 | Codex | SPS Platform Level 0, MongoDB Collection Master Level 3 계층으로 정정한다.
 *
 * DB 구조는 변경하지 않는다.
 */
USE te_common;

START TRANSACTION;

SET @program_id = 'MONGODB_RUNTIME_OBJECT_DEFINITION_20260801';
SET @actor_id = 'SYSTEM';
SET @client_ip = '127.0.0.1';

INSERT INTO cm_common_code_group
(
    group_code, group_name, group_description, sort_no,
    status_code, reserved_yn, system_yn,
    created_by, updated_by, client_ip, program_id, lifecycle_status_code
)
VALUES
(
    'MONGODB_RUNTIME_OBJECT_DEFINITION',
    'MongoDB Runtime Object Definition',
    'SPS Platform Level 0 아래 MongoDB Database, Collection Object, Collection Master, Document Details Object의 Identifier 발급과 Repository 등록에 사용하는 선언형 Engine 입력 계약을 관리한다.',
    360,
    'ACTIVE', 'Y', 'Y',
    @actor_id, @actor_id, @client_ip, @program_id, 'CREATE_MAINTAIN'
)
ON DUPLICATE KEY UPDATE
    group_name = VALUES(group_name),
    group_description = VALUES(group_description),
    sort_no = VALUES(sort_no),
    status_code = VALUES(status_code),
    reserved_yn = VALUES(reserved_yn),
    system_yn = VALUES(system_yn),
    updated_dt = CURRENT_TIMESTAMP,
    updated_by = VALUES(updated_by),
    client_ip = VALUES(client_ip),
    program_id = VALUES(program_id),
    lifecycle_status_code = VALUES(lifecycle_status_code);

INSERT INTO cm_common_code
(
    group_code, code, code_name, common_code_description, sort_no,
    status_code, created_by, updated_by, client_ip, program_id,
    common_code_json, lifecycle_status_code
)
VALUES
(
    'MONGODB_RUNTIME_OBJECT_DEFINITION', 'MDB', 'MongoDB Database',
    'SPS Platform 하위 MongoDB Database Object 정의. MongoDB 저장소 계층의 Level 1이다.',
    10, 'ACTIVE', @actor_id, @actor_id, @client_ip, @program_id,
    JSON_OBJECT(
        'object_code', 'MDB',
        'object_name', 'MongoDB Database',
        'object_description', 'SPS Platform 하위 MongoDB 저장소 계층의 Level 1 Database Object. Storage Separation Contract의 MongoDB Database를 식별한다.',
        'business_code', 'SP', 'domain_code', 'RP', 'object_type_code', 'DATABASE',
        'object_level', 1, 'sort_no', 10,
        'target_identifier_field', 'mongodb_database_id',
        'identifier_target_code', 'MDB',
        'sequence_scope_code', 'YEARLY', 'sequence_length', 5,
        'mongodb_internal_yn', 'N'
    ),
    'CREATE_MAINTAIN'
),
(
    'MONGODB_RUNTIME_OBJECT_DEFINITION', 'MCO', 'MongoDB Collection Object',
    'MongoDB Collection Object 정의. MongoDB 저장소 계층의 Level 2이다.',
    20, 'ACTIVE', @actor_id, @actor_id, @client_ip, @program_id,
    JSON_OBJECT(
        'object_code', 'MCO',
        'object_name', 'MongoDB Collection Object',
        'object_description', 'SPS Platform 하위 MongoDB 저장소 계층의 Level 2 Collection Object. Database 하위 Collection의 논리 Object를 식별한다.',
        'business_code', 'SP', 'domain_code', 'RP', 'object_type_code', 'REPOSITORY',
        'object_level', 2, 'sort_no', 20,
        'target_identifier_field', 'mongodb_collection_id',
        'identifier_target_code', 'MCO',
        'sequence_scope_code', 'MONTHLY', 'sequence_length', 5,
        'mongodb_internal_yn', 'N'
    ),
    'CREATE_MAINTAIN'
),
(
    'MONGODB_RUNTIME_OBJECT_DEFINITION', 'MCM', 'MongoDB Collection Master',
    'MongoDB Collection Master Object 정의. Execution Link가 참조하는 Level 3 Collection Master이다.',
    30, 'ACTIVE', @actor_id, @actor_id, @client_ip, @program_id,
    JSON_OBJECT(
        'object_code', 'MCM',
        'object_name', 'MongoDB Collection Master',
        'object_description', 'SPS Platform 하위 MongoDB 저장소 계층의 Level 3 Collection Master Object. sp_object_execution_link.target_object_id와 mongodb_document_master_id가 동일한 MCM Object ID를 참조한다.',
        'business_code', 'SP', 'domain_code', 'RP', 'object_type_code', 'REPOSITORY',
        'object_level', 3, 'sort_no', 30,
        'target_identifier_field', 'mongodb_document_master_id',
        'identifier_target_code', 'MCM',
        'sequence_scope_code', 'DAILY', 'sequence_length', 5,
        'mongodb_internal_yn', 'N'
    ),
    'CREATE_MAINTAIN'
),
(
    'MONGODB_RUNTIME_OBJECT_DEFINITION', 'MDD', 'MongoDB Document Detail',
    'MongoDB Document Detail Object 정의. MongoDB 내부 전용 Level 4이다.',
    40, 'ACTIVE', @actor_id, @actor_id, @client_ip, @program_id,
    JSON_OBJECT(
        'object_code', 'MDD',
        'object_name', 'MongoDB Document Detail',
        'object_description', 'MongoDB 내부 전용 Level 4 Document Detail Object. MariaDB Business Table에 직접 저장하지 않는다.',
        'business_code', 'SP', 'domain_code', 'RP', 'object_type_code', 'DOCUMENT',
        'object_level', 4, 'sort_no', 40,
        'target_identifier_field', 'mongodb_document_details_id',
        'identifier_target_code', 'MDD',
        'sequence_scope_code', 'DAILY', 'sequence_length', 5,
        'mongodb_internal_yn', 'Y'
    ),
    'CREATE_MAINTAIN'
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
    code AS object_code,
    JSON_UNQUOTE(JSON_EXTRACT(common_code_json, '$.object_name')) AS object_name,
    JSON_UNQUOTE(JSON_EXTRACT(common_code_json, '$.object_type_code')) AS object_type_code,
    JSON_UNQUOTE(JSON_EXTRACT(common_code_json, '$.object_level')) AS object_level,
    JSON_UNQUOTE(JSON_EXTRACT(common_code_json, '$.identifier_target_code')) AS identifier_target_code,
    JSON_UNQUOTE(JSON_EXTRACT(common_code_json, '$.target_identifier_field')) AS target_identifier_field
FROM cm_common_code
WHERE group_code = 'MONGODB_RUNTIME_OBJECT_DEFINITION'
  AND status_code = 'ACTIVE'
  AND deleted_dt IS NULL
ORDER BY sort_no, code;

COMMIT;

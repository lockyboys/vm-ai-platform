/*
 * File Story
 * MongoDB 식별자 Target(MDB/MCO/MCM/MDD)을 Common Repository에 멱등 등록한다.
 *
 * Change History
 * 20260801 | Codex | MongoDB Database, Collection, Document Master, Document Details 식별자 Target을 등록한다.
 *
 * DB 구조는 변경하지 않는다.
 */
USE te_common;

START TRANSACTION;

SET @program_id = 'REGISTER_MONGODB_IDENTIFIER_TARGET_20260801';
SET @actor_id = 'SYSTEM';
SET @client_ip = '127.0.0.1';

INSERT INTO cm_common_code
(
    group_code, code, code_name, common_code_description, sort_no,
    status_code, created_by, updated_by, client_ip, program_id,
    common_code_json, lifecycle_status_code
)
VALUES
(
    'SPS_IDENTIFIER_TARGET', 'MDB', 'MongoDB Database',
    'MongoDB 물리 Database 식별자 Target. MongoDB 저장소 계층의 최상위 Database를 식별한다.',
    210, 'ACTIVE', @actor_id, @actor_id, @client_ip, @program_id,
    JSON_OBJECT(
        'identifier_token', 'MDB',
        'identifier_level', 1,
        'target_identifier_field', 'mongodb_database_id',
        'mariadb_repository_yn', 'Y',
        'mongodb_internal_yn', 'N'
    ),
    'CREATE_MAINTAIN'
),
(
    'SPS_IDENTIFIER_TARGET', 'MCO', 'MongoDB Collection',
    'MongoDB Collection 식별자 Target. Database 하위 Collection을 식별한다.',
    220, 'ACTIVE', @actor_id, @actor_id, @client_ip, @program_id,
    JSON_OBJECT(
        'identifier_token', 'MCO',
        'identifier_level', 2,
        'target_identifier_field', 'mongodb_collection_id',
        'mariadb_repository_yn', 'Y',
        'mongodb_internal_yn', 'N'
    ),
    'CREATE_MAINTAIN'
),
(
    'SPS_IDENTIFIER_TARGET', 'MCM', 'MongoDB Document Master',
    'MongoDB Document Master 식별자 Target. Execution Link가 참조하는 MongoDB Document Master를 식별한다.',
    230, 'ACTIVE', @actor_id, @actor_id, @client_ip, @program_id,
    JSON_OBJECT(
        'identifier_token', 'MCM',
        'identifier_level', 3,
        'target_identifier_field', 'mongodb_document_master_id',
        'mariadb_repository_yn', 'Y',
        'mongodb_internal_yn', 'N'
    ),
    'CREATE_MAINTAIN'
),
(
    'SPS_IDENTIFIER_TARGET', 'MDD', 'MongoDB Document Details',
    'MongoDB 내부 Document Details 식별자 Target. MariaDB Business Table에는 저장하지 않는다.',
    240, 'ACTIVE', @actor_id, @actor_id, @client_ip, @program_id,
    JSON_OBJECT(
        'identifier_token', 'MDD',
        'identifier_level', 4,
        'target_identifier_field', 'mongodb_document_details_id',
        'mariadb_repository_yn', 'N',
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
    code,
    code_name,
    JSON_UNQUOTE(JSON_EXTRACT(common_code_json, '$.identifier_level')) AS identifier_level,
    JSON_UNQUOTE(JSON_EXTRACT(common_code_json, '$.target_identifier_field')) AS target_identifier_field,
    JSON_UNQUOTE(JSON_EXTRACT(common_code_json, '$.mongodb_internal_yn')) AS mongodb_internal_yn
FROM cm_common_code
WHERE group_code = 'SPS_IDENTIFIER_TARGET'
  AND code IN ('MDB', 'MCO', 'MCM', 'MDD')
ORDER BY sort_no, code;

COMMIT;

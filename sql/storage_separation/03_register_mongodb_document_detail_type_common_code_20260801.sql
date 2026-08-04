/*
 * File Story
 * MongoDB 내부 언어 데이터 상세(Corpus, Document, Sentence, Token, Vocab) 구분 공통코드를 멱등 등록한다.
 *
 * Change History
 * 20260801 | Codex | MDD MongoDB 내부 상세를 Corpus → Document → Sentence → Token 계층과 Corpus 단위 Vocab 참조를 선언한다.
 *
 * DB 구조는 변경하지 않는다.
 */
USE te_common;

START TRANSACTION;

SET @program_id = 'REGISTER_MONGODB_DOCUMENT_DETAIL_TYPE_20260801';
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
    'MONGODB_DOCUMENT_DETAIL_TYPE',
    'MongoDB Document Detail Type',
    'MongoDB 내부 MDD의 언어 데이터 계층(Corpus, Document, Sentence, Token)과 Corpus 단위 Vocab 참조 관계를 관리한다. MariaDB Business Table에는 이 상세 행을 복제하지 않는다.',
    370,
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
    'MONGODB_DOCUMENT_DETAIL_TYPE', 'CORPUS', 'Corpus',
    '문서 집합과 수집·정제 단위를 나타내는 MongoDB 내부 언어 데이터 최상위 상세.',
    10, 'ACTIVE', @actor_id, @actor_id, @client_ip, @program_id,
    JSON_OBJECT(
        'document_detail_type_code', 'CORPUS',
        'parent_document_detail_type_code', NULL,
        'child_document_detail_type_codes', JSON_ARRAY('DOCUMENT', 'VOCAB'),
        'content_storage_yn', 'Y',
        'mariadb_business_table_store_yn', 'N'
    ),
    'CREATE_MAINTAIN'
),
(
    'MONGODB_DOCUMENT_DETAIL_TYPE', 'DOCUMENT', 'Document',
    'Corpus에 속하는 원문 또는 정규화 문서 상세.',
    20, 'ACTIVE', @actor_id, @actor_id, @client_ip, @program_id,
    JSON_OBJECT(
        'document_detail_type_code', 'DOCUMENT',
        'parent_document_detail_type_code', 'CORPUS',
        'child_document_detail_type_codes', JSON_ARRAY('SENTENCE'),
        'content_storage_yn', 'Y',
        'mariadb_business_table_store_yn', 'N'
    ),
    'CREATE_MAINTAIN'
),
(
    'MONGODB_DOCUMENT_DETAIL_TYPE', 'SENTENCE', 'Sentence',
    'Document에서 분리한 문장 단위 상세.',
    30, 'ACTIVE', @actor_id, @actor_id, @client_ip, @program_id,
    JSON_OBJECT(
        'document_detail_type_code', 'SENTENCE',
        'parent_document_detail_type_code', 'DOCUMENT',
        'child_document_detail_type_codes', JSON_ARRAY('TOKEN'),
        'content_storage_yn', 'Y',
        'mariadb_business_table_store_yn', 'N'
    ),
    'CREATE_MAINTAIN'
),
(
    'MONGODB_DOCUMENT_DETAIL_TYPE', 'TOKEN', 'Token',
    'Sentence에서 분석한 Token 단위 상세.',
    40, 'ACTIVE', @actor_id, @actor_id, @client_ip, @program_id,
    JSON_OBJECT(
        'document_detail_type_code', 'TOKEN',
        'parent_document_detail_type_code', 'SENTENCE',
        'child_document_detail_type_codes', JSON_ARRAY(),
        'reference_document_detail_type_codes', JSON_ARRAY('VOCAB'),
        'content_storage_yn', 'Y',
        'mariadb_business_table_store_yn', 'N'
    ),
    'CREATE_MAINTAIN'
),
(
    'MONGODB_DOCUMENT_DETAIL_TYPE', 'VOCAB', 'Vocab',
    'Corpus 단위로 공유하는 어휘 집합. Token은 Vocab을 참조하며 Vocab은 Token의 하위 행이 아니다.',
    50, 'ACTIVE', @actor_id, @actor_id, @client_ip, @program_id,
    JSON_OBJECT(
        'document_detail_type_code', 'VOCAB',
        'parent_document_detail_type_code', 'CORPUS',
        'child_document_detail_type_codes', JSON_ARRAY(),
        'referenced_by_document_detail_type_codes', JSON_ARRAY('TOKEN'),
        'content_storage_yn', 'Y',
        'mariadb_business_table_store_yn', 'N'
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
    JSON_UNQUOTE(JSON_EXTRACT(common_code_json, '$.parent_document_detail_type_code')) AS parent_type_code,
    JSON_UNQUOTE(JSON_EXTRACT(common_code_json, '$.content_storage_yn')) AS content_storage_yn
FROM cm_common_code
WHERE group_code = 'MONGODB_DOCUMENT_DETAIL_TYPE'
  AND status_code = 'ACTIVE'
  AND deleted_dt IS NULL
ORDER BY sort_no, code;

COMMIT;
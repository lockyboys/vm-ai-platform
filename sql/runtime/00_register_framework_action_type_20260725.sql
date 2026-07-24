/*
===============================================================================
Story Programming Framework
Framework ACTION_TYPE Common Code Registration Batch
===============================================================================

PURPOSE
- Rule Engine이 사용하는 Framework 공통 Action Type을 COMMON Repository에
  등록한다.

PRINCIPLE
- Repository First
- Generator First
- Hardcoding 금지
- 기존 업무 Action Type 보존
- Framework Action과 Domain Action을 동일 ACTION_TYPE Group에서 관리하되
  common_code_json.scope로 의미 범위를 구분

SCOPE
- te_common.cm_common_code
- group_code = ACTION_TYPE

NOTE
- 본 Batch는 공통코드만 등록한다.
- 실제 Rule 등록은 후속 Batch에서 수행한다.
===============================================================================
*/

USE te_common;

START TRANSACTION;

SET @program_id = 'ACTION_TYPE_FRAMEWORK_BATCH_20260725';
SET @client_ip  = '127.0.0.1';

INSERT INTO cm_common_code
(
    group_code,
    code,
    code_name,
    common_code_description,
    sort_no,
    status_code,
    created_dt,
    created_by,
    updated_dt,
    updated_by,
    client_ip,
    deleted_by,
    deleted_dt,
    program_id,
    common_code_json,
    lifecycle_status_code
)
VALUES
(
    'ACTION_TYPE',
    'RESOLVE_OBJECT_METADATA',
    'Object Metadata 해석',
    'Repository에 등록된 Metadata를 해석하여 대상 Object 등록 또는 실행에 필요한 속성 집합을 구성하는 Framework 공통 Action 유형.',
    100,
    'ACTIVE',
    NOW(),
    'SYSTEM',
    NOW(),
    'SYSTEM',
    @client_ip,
    NULL,
    NULL,
    @program_id,
    JSON_OBJECT(
        'scope', 'FRAMEWORK',
        'category', 'RESOLUTION',
        'repository_first', TRUE,
        'generator_first', TRUE,
        'hardcoding_allowed', FALSE,
        'input_source', 'REPOSITORY_METADATA'
    ),
    'CREATE_MAINTAIN'
),
(
    'ACTION_TYPE',
    'GENERATE_IDENTIFIER',
    'Identifier 생성',
    'Identifier Engine이 Blueprint와 Repository Metadata를 해석하여 대상 Object 또는 Runtime 식별자를 생성하는 Framework 공통 Action 유형.',
    110,
    'ACTIVE',
    NOW(),
    'SYSTEM',
    NOW(),
    'SYSTEM',
    @client_ip,
    NULL,
    NULL,
    @program_id,
    JSON_OBJECT(
        'scope', 'FRAMEWORK',
        'category', 'GENERATION',
        'engine', 'IDENTIFIER_ENGINE',
        'repository_first', TRUE,
        'generator_first', TRUE,
        'hardcoding_allowed', FALSE
    ),
    'CREATE_MAINTAIN'
),
(
    'ACTION_TYPE',
    'REGISTER_OBJECT',
    'Repository Object 등록',
    'Repository Metadata와 발급된 Identifier를 사용하여 sp_object에 Object를 등록하는 Framework 공통 Action 유형.',
    120,
    'ACTIVE',
    NOW(),
    'SYSTEM',
    NOW(),
    'SYSTEM',
    @client_ip,
    NULL,
    NULL,
    @program_id,
    JSON_OBJECT(
        'scope', 'FRAMEWORK',
        'category', 'REGISTRATION',
        'target_repository', 'STORY.sp_object',
        'repository_first', TRUE,
        'generator_first', TRUE,
        'hardcoding_allowed', FALSE,
        'duplicate_policy', 'REUSE_EXISTING_OBJECT'
    ),
    'CREATE_MAINTAIN'
),
(
    'ACTION_TYPE',
    'REGISTER_LIFECYCLE',
    'Lifecycle 등록',
    'Object, Rule, Document 또는 Repository 자산의 생명주기 상태와 전이를 기록하는 Framework 공통 Action 유형.',
    130,
    'ACTIVE',
    NOW(),
    'SYSTEM',
    NOW(),
    'SYSTEM',
    @client_ip,
    NULL,
    NULL,
    @program_id,
    JSON_OBJECT(
        'scope', 'FRAMEWORK',
        'category', 'LIFECYCLE',
        'repository_first', TRUE,
        'hardcoding_allowed', FALSE,
        'initial_event', 'REGISTER'
    ),
    'CREATE_MAINTAIN'
),
(
    'ACTION_TYPE',
    'REGISTER_METADATA',
    'Metadata 등록',
    'Object 또는 실행 대상을 설명하는 구조화 Metadata를 공식 Repository에 등록하는 Framework 공통 Action 유형.',
    140,
    'ACTIVE',
    NOW(),
    'SYSTEM',
    NOW(),
    'SYSTEM',
    @client_ip,
    NULL,
    NULL,
    @program_id,
    JSON_OBJECT(
        'scope', 'FRAMEWORK',
        'category', 'REGISTRATION',
        'target_repository', 'STORY.sp_metadata',
        'repository_first', TRUE,
        'hardcoding_allowed', FALSE
    ),
    'CREATE_MAINTAIN'
),
(
    'ACTION_TYPE',
    'REGISTER_RELATIONSHIP',
    'Relationship 등록',
    'Repository Object 간 공식 관계를 Relationship Repository에 등록하는 Framework 공통 Action 유형.',
    150,
    'ACTIVE',
    NOW(),
    'SYSTEM',
    NOW(),
    'SYSTEM',
    @client_ip,
    NULL,
    NULL,
    @program_id,
    JSON_OBJECT(
        'scope', 'FRAMEWORK',
        'category', 'RELATIONSHIP',
        'target_repository', 'STORY.sp_relationship',
        'repository_first', TRUE,
        'hardcoding_allowed', FALSE
    ),
    'CREATE_MAINTAIN'
),
(
    'ACTION_TYPE',
    'REGISTER_DOCUMENT',
    'Document Object 등록',
    '보고서, 명세서 또는 실행 산출물을 Document Object로 등록하는 Framework 공통 Action 유형.',
    160,
    'ACTIVE',
    NOW(),
    'SYSTEM',
    NOW(),
    'SYSTEM',
    @client_ip,
    NULL,
    NULL,
    @program_id,
    JSON_OBJECT(
        'scope', 'FRAMEWORK',
        'category', 'DOCUMENT',
        'identifier_target_code', 'DC',
        'repository_first', TRUE,
        'generator_first', TRUE,
        'hardcoding_allowed', FALSE
    ),
    'CREATE_MAINTAIN'
),
(
    'ACTION_TYPE',
    'REGISTER_EVIDENCE',
    'Evidence 등록',
    'Repository 분석 보고서 또는 실행 결과를 근거로 Evidence Repository에 공식 증거를 등록하는 Framework 공통 Action 유형.',
    170,
    'ACTIVE',
    NOW(),
    'SYSTEM',
    NOW(),
    'SYSTEM',
    @client_ip,
    NULL,
    NULL,
    @program_id,
    JSON_OBJECT(
        'scope', 'FRAMEWORK',
        'category', 'EVIDENCE',
        'repository_first', TRUE,
        'hardcoding_allowed', FALSE,
        'evidence_source_policy', 'FINAL_REPORT_FIRST'
    ),
    'CREATE_MAINTAIN'
),
(
    'ACTION_TYPE',
    'REGISTER_WORK_SESSION',
    'Work Session 등록',
    'Framework 개발 및 실행 작업 단위를 Work Session Repository에 등록하는 공통 Action 유형.',
    180,
    'ACTIVE',
    NOW(),
    'SYSTEM',
    NOW(),
    'SYSTEM',
    @client_ip,
    NULL,
    NULL,
    @program_id,
    JSON_OBJECT(
        'scope', 'FRAMEWORK',
        'category', 'WORK_REPOSITORY',
        'target_repository', 'WORK_SESSION',
        'repository_first', TRUE,
        'hardcoding_allowed', FALSE
    ),
    'CREATE_MAINTAIN'
),
(
    'ACTION_TYPE',
    'REGISTER_WORK_ITEM',
    'Work Item 등록',
    'Work Session에 포함되는 개별 작업 단위를 Work Item Repository에 등록하는 공통 Action 유형.',
    190,
    'ACTIVE',
    NOW(),
    'SYSTEM',
    NOW(),
    'SYSTEM',
    @client_ip,
    NULL,
    NULL,
    @program_id,
    JSON_OBJECT(
        'scope', 'FRAMEWORK',
        'category', 'WORK_REPOSITORY',
        'target_repository', 'WORK_ITEM',
        'repository_first', TRUE,
        'hardcoding_allowed', FALSE
    ),
    'CREATE_MAINTAIN'
),
(
    'ACTION_TYPE',
    'REGISTER_WORK_ASSET',
    'Work Asset 등록',
    'SQL, Report, DOCX, Markdown 또는 기타 산출물을 Work Asset Repository에 등록하는 공통 Action 유형.',
    200,
    'ACTIVE',
    NOW(),
    'SYSTEM',
    NOW(),
    'SYSTEM',
    @client_ip,
    NULL,
    NULL,
    @program_id,
    JSON_OBJECT(
        'scope', 'FRAMEWORK',
        'category', 'WORK_REPOSITORY',
        'target_repository', 'WORK_ASSET',
        'repository_first', TRUE,
        'hardcoding_allowed', FALSE
    ),
    'CREATE_MAINTAIN'
),
(
    'ACTION_TYPE',
    'GENERATE_REPORT',
    'Report 생성',
    'Repository Audit, Impact Analysis 또는 실행 결과를 공식 Report 산출물로 생성하는 Framework 공통 Action 유형.',
    210,
    'ACTIVE',
    NOW(),
    'SYSTEM',
    NOW(),
    'SYSTEM',
    @client_ip,
    NULL,
    NULL,
    @program_id,
    JSON_OBJECT(
        'scope', 'FRAMEWORK',
        'category', 'GENERATION',
        'generator', 'REPORT_GENERATOR',
        'repository_first', TRUE,
        'generator_first', TRUE,
        'hardcoding_allowed', FALSE
    ),
    'CREATE_MAINTAIN'
),
(
    'ACTION_TYPE',
    'RETURN_IDENTIFIER',
    'Identifier 반환',
    'Rule 또는 Generator 실행 후 생성되거나 재사용된 공식 Identifier를 후속 처리 단계에 반환하는 Framework 공통 Action 유형.',
    220,
    'ACTIVE',
    NOW(),
    'SYSTEM',
    NOW(),
    'SYSTEM',
    @client_ip,
    NULL,
    NULL,
    @program_id,
    JSON_OBJECT(
        'scope', 'FRAMEWORK',
        'category', 'RETURN',
        'repository_first', TRUE,
        'hardcoding_allowed', FALSE,
        'required_output', 'identifier'
    ),
    'CREATE_MAINTAIN'
)
ON DUPLICATE KEY UPDATE
    code_name               = VALUES(code_name),
    common_code_description = VALUES(common_code_description),
    sort_no                 = VALUES(sort_no),
    status_code             = VALUES(status_code),
    updated_dt              = NOW(),
    updated_by              = VALUES(updated_by),
    client_ip               = VALUES(client_ip),
    deleted_by              = NULL,
    deleted_dt              = NULL,
    program_id              = VALUES(program_id),
    common_code_json        = VALUES(common_code_json),
    lifecycle_status_code   = VALUES(lifecycle_status_code);

/* ============================================================================
   Verification
============================================================================ */

SELECT
    group_code,
    code,
    code_name,
    sort_no,
    status_code,
    lifecycle_status_code,
    program_id,
    common_code_json
FROM cm_common_code
WHERE group_code = 'ACTION_TYPE'
  AND code IN
  (
      'RESOLVE_OBJECT_METADATA',
      'GENERATE_IDENTIFIER',
      'REGISTER_OBJECT',
      'REGISTER_LIFECYCLE',
      'REGISTER_METADATA',
      'REGISTER_RELATIONSHIP',
      'REGISTER_DOCUMENT',
      'REGISTER_EVIDENCE',
      'REGISTER_WORK_SESSION',
      'REGISTER_WORK_ITEM',
      'REGISTER_WORK_ASSET',
      'GENERATE_REPORT',
      'RETURN_IDENTIFIER'
  )
ORDER BY sort_no, code;

SELECT
    COUNT(*) AS framework_action_type_count
FROM cm_common_code
WHERE group_code = 'ACTION_TYPE'
  AND status_code = 'ACTIVE'
  AND deleted_dt IS NULL
  AND JSON_UNQUOTE(JSON_EXTRACT(common_code_json, '$.scope')) = 'FRAMEWORK';

COMMIT;

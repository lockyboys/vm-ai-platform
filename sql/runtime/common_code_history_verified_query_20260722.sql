-- Common Code empty-group batch History and Verified SQL supplement
-- Target: 9 groups and 42 codes applied at 2026-07-22 09:37:59
-- Idempotent: fixed identifiers and fixed created_dt are used.

USE te_common;

SET @actor = 'SYSTEM';
SET @client_ip = '127.0.0.1';
SET @program_id = 'CM_COMMON_CODE_BATCH_20260722';
SET @batch_dt = TIMESTAMP('2026-07-22 09:37:59');
SET @query_id = 'SP_RP_SQL_QUERY_20260722_093759_00001';

START TRANSACTION;

-- History 1: nine group metadata updates.
INSERT IGNORE INTO cm_change_history
(
    change_history_id, target_database_name, target_table_name,
    target_record_id, action_type, change_story,
    created_by, created_dt, client_ip, program_id, status_code
)
SELECT
    CONCAT('CM_CO_CHANGE_HISTORY_20260722_093759_G', LPAD(ROW_NUMBER() OVER (ORDER BY group_code), 2, '0')),
    'te_common',
    'cm_common_code_group',
    group_code,
    'BATCH',
    CONCAT(group_code, ' Group의 설명·시스템 여부·상태·감사정보를 보완한다.'),
    @actor, @batch_dt, @client_ip, @program_id, 'ACTIVE'
FROM cm_common_code_group
WHERE group_code IN
(
    'AI_ANALYSIS_STATUS','AI_PROVIDER','HP_RISK_LEVEL','HS_HOSPITAL_TYPE',
    'OC_DOCUMENT_TYPE','SPS_FUNCTION','SPS_SEQUENCE_FORMAT',
    'SPS_SEQUENCE_POLICY','WF_WELFARE_TYPE'
);

-- History 2: forty-two common-code upserts.
INSERT IGNORE INTO cm_change_history
(
    change_history_id, target_database_name, target_table_name,
    target_record_id, action_type, change_story,
    created_by, created_dt, client_ip, program_id, status_code
)
SELECT
    CONCAT('CM_CO_CHANGE_HISTORY_20260722_093759_C', LPAD(ROW_NUMBER() OVER (ORDER BY group_code, sort_no, code), 2, '0')),
    'te_common',
    'cm_common_code',
    CONCAT(group_code, ':', code),
    'BATCH',
    CONCAT(group_code, '.', code, ' 공통코드를 등록 또는 최신 정의로 갱신한다.'),
    @actor, @batch_dt, @client_ip, @program_id, 'ACTIVE'
FROM cm_common_code
WHERE program_id = @program_id
  AND group_code IN
(
    'AI_ANALYSIS_STATUS','AI_PROVIDER','HP_RISK_LEVEL','HS_HOSPITAL_TYPE',
    'OC_DOCUMENT_TYPE','SPS_FUNCTION','SPS_SEQUENCE_FORMAT',
    'SPS_SEQUENCE_POLICY','WF_WELFARE_TYPE'
);

-- Official Repository record for the verified and executed SQL batch.
INSERT INTO cm_verified_sql_query
(
    query_id, query_name, query_description, crud_type, sql_text,
    verified_yn, certified_level_code, verification_description,
    created_by, created_dt, verified_by, verified_dt, updated_dt, updated_by,
    story_programming_rule_pass_yn, snake_case_pass_yn,
    table_exists_pass_yn, column_exists_pass_yn, crud_match_pass_yn,
    where_clause_pass_yn, status_code, program_id, client_ip
)
VALUES
(
    @query_id,
    '공통코드 빈 Group 9건 Code 등록 Batch',
    '빈 공통코드 Group 9건의 Metadata를 보완하고 Source·Repository·Master 값 및 SPS 확장 설계를 근거로 Code 42건을 등록한 검증·실행 SQL Batch.',
    'BATCH',
    '-- 9개 빈 공통코드 Group 통합 정비 배치
-- 대상: AI_ANALYSIS_STATUS, AI_PROVIDER, HP_RISK_LEVEL, HS_HOSPITAL_TYPE,
--       OC_DOCUMENT_TYPE, SPS_FUNCTION, SPS_SEQUENCE_FORMAT,
--       SPS_SEQUENCE_POLICY, WF_WELFARE_TYPE
-- 원칙: 재실행 가능, 물리 삭제 없음, 기존 Master Repository 값 동기화 +
--       SPS 식별자 계층과 Runtime 운용에 필요한 신규 Format/Policy 설계값 등록

START TRANSACTION;

SET @program_id = ''CM_COMMON_CODE_BATCH_20260722'';
SET @actor = ''SYSTEM'';
SET @client_ip = ''127.0.0.1'';

DROP TEMPORARY TABLE IF EXISTS tmp_common_code_batch;
CREATE TEMPORARY TABLE tmp_common_code_batch
(
    group_code VARCHAR(99) NOT NULL,
    code VARCHAR(99) NOT NULL,
    code_name VARCHAR(200) NOT NULL,
    common_code_description VARCHAR(2000) NOT NULL,
    sort_no INT NOT NULL,
    common_code_json JSON NULL,
    PRIMARY KEY (group_code, code)
);

INSERT INTO tmp_common_code_batch VALUES
(''AI_ANALYSIS_STATUS'',''READY'',''분석 대기'',''AI 분석 요청이 등록되어 실행을 기다리는 상태.'',10,JSON_OBJECT(''lifecycle_order'',10,''terminal_yn'',''N'',''allowed_next_codes'',JSON_ARRAY(''RUNNING'',''FAILED''),''evidence'',''OBJECT_ATTEMPT_STATUS 및 Runtime 상태 체계'')),
(''AI_ANALYSIS_STATUS'',''RUNNING'',''분석 중'',''AI Engine이 분석 작업을 실행하고 있는 상태.'',20,JSON_OBJECT(''lifecycle_order'',20,''terminal_yn'',''N'',''allowed_next_codes'',JSON_ARRAY(''SUCCESS'',''FAILED''),''evidence'',''Engine 실행 상태'')),
(''AI_ANALYSIS_STATUS'',''SUCCESS'',''분석 성공'',''AI 분석이 정상적으로 완료되어 결과가 생성된 상태.'',30,JSON_OBJECT(''lifecycle_order'',30,''terminal_yn'',''Y'',''allowed_next_codes'',JSON_ARRAY(),''evidence'',''Runtime 완료 상태'')),
(''AI_ANALYSIS_STATUS'',''FAILED'',''분석 실패'',''AI 분석 실행 중 오류가 발생하여 정상 결과를 생성하지 못한 상태.'',40,JSON_OBJECT(''lifecycle_order'',40,''terminal_yn'',''Y'',''allowed_next_codes'',JSON_ARRAY(''READY''),''evidence'',''Generator 및 Runtime 실패 상태'')),

(''AI_PROVIDER'',''OPENAI'',''OpenAI'',''OpenAI API를 통해 AI 모델을 제공하는 공급자.'',10,JSON_OBJECT(''provider_type'',''EXTERNAL_API'',''config_key_family'',''OPENAI'',''registration_basis'',''project configuration'')),
(''AI_PROVIDER'',''GEMINI'',''Google Gemini'',''Google Gemini API를 통해 AI 모델을 제공하는 공급자.'',20,JSON_OBJECT(''provider_type'',''EXTERNAL_API'',''config_key_family'',''GEMINI'',''registration_basis'',''project configuration'')),
(''AI_PROVIDER'',''GENIE'',''KT Genie'',''KT Genie 연계 기능에서 사용하는 AI 또는 음성 서비스 공급자.'',30,JSON_OBJECT(''provider_type'',''EXTERNAL_API'',''config_key_family'',''GENIE'',''registration_basis'',''project configuration'')),

(''HP_RISK_LEVEL'',''LOW'',''낮음'',''관찰 또는 일반 관리가 가능하며 건강 및 변경 위험이 낮은 단계.'',10,JSON_OBJECT(''severity_order'',10,''requires_immediate_action_yn'',''N'')),
(''HP_RISK_LEVEL'',''MEDIUM'',''보통'',''추가 확인과 지속적인 관찰이 필요한 기본 위험 단계.'',20,JSON_OBJECT(''severity_order'',20,''requires_immediate_action_yn'',''N'')),
(''HP_RISK_LEVEL'',''HIGH'',''높음'',''중대한 위험 가능성이 있어 우선 검토와 대응이 필요한 단계.'',30,JSON_OBJECT(''severity_order'',30,''requires_immediate_action_yn'',''Y'')),

(''HS_HOSPITAL_TYPE'',''TERTIARY_HOSPITAL'',''상급종합병원'',''중증질환 중심의 고난도 전문 진료를 제공하는 상급종합병원.'',10,JSON_OBJECT(''care_level'',3,''referral_required_yn'',''Y'')),
(''HS_HOSPITAL_TYPE'',''GENERAL_HOSPITAL'',''종합병원'',''복수 진료과와 입원 기능을 갖춘 종합병원.'',20,JSON_OBJECT(''care_level'',2,''referral_required_yn'',''CONDITIONAL'')),
(''HS_HOSPITAL_TYPE'',''HOSPITAL'',''병원'',''입원 진료 기능을 중심으로 운영되는 병원급 의료기관.'',30,JSON_OBJECT(''care_level'',2,''referral_required_yn'',''N'')),
(''HS_HOSPITAL_TYPE'',''CLINIC'',''의원'',''외래 중심의 일차 진료를 제공하는 의원급 의료기관.'',40,JSON_OBJECT(''care_level'',1,''referral_required_yn'',''N'')),
(''HS_HOSPITAL_TYPE'',''PHARMACY'',''약국'',''처방 조제와 복약 안내를 제공하는 약국.'',50,JSON_OBJECT(''care_level'',0,''referral_required_yn'',''N'')),

(''OC_DOCUMENT_TYPE'',''TEXT'',''텍스트 문서'',''문자열 본문을 직접 처리하는 텍스트 문서.'',10,JSON_OBJECT(''parser_type'',''TEXT'',''evidence'',''dce_sir_builder.py document_type_code'')),
(''OC_DOCUMENT_TYPE'',''PDF'',''PDF 문서'',''PDF 원본에서 텍스트와 구조를 추출하는 문서.'',20,JSON_OBJECT(''parser_type'',''PDF'',''runtime_object'',''DOCUMENT'')),
(''OC_DOCUMENT_TYPE'',''IMAGE'',''이미지 문서'',''JPG 또는 PNG 이미지에 OCR을 적용하는 문서.'',30,JSON_OBJECT(''parser_type'',''OCR_IMAGE'',''runtime_object'',''IMAGE'')),
(''OC_DOCUMENT_TYPE'',''VIDEO'',''영상 문서'',''영상 프레임을 표본 추출하여 OCR과 분석을 수행하는 문서.'',40,JSON_OBJECT(''parser_type'',''VIDEO_FRAME'',''runtime_object'',''VIDEO'')),

(''SPS_FUNCTION'',''IDENTIFIER_GENERATE'',''Identifier 생성'',''Repository Blueprint와 Sequence 정책으로 식별자를 생성하는 기능.'',10,JSON_OBJECT(''engine'',''IdentifierEngine'',''domain'',''IC'')),
(''SPS_FUNCTION'',''DOCUMENT_COMPILE'',''Document 컴파일'',''Story 문서를 SIR 및 실행 가능한 구조로 변환하는 기능.'',20,JSON_OBJECT(''engine'',''DocumentCompiler'',''domain'',''DC'')),
(''SPS_FUNCTION'',''RUNTIME_EXECUTE'',''Runtime 실행'',''Object 실행 계획을 처리하고 Repository와 결과 저장소에 기록하는 기능.'',30,JSON_OBJECT(''engine'',''ObjectRuntimeEngine'',''domain'',''EN'')),
(''SPS_FUNCTION'',''REPOSITORY_AUDIT'',''Repository 감사'',''Repository Schema, Data, 관계와 표준 준수 여부를 검사하는 기능.'',40,JSON_OBJECT(''engine'',''RepositoryAudit'',''domain'',''RP'')),

(''WF_WELFARE_TYPE'',''CASH'',''현금 급여'',''수급자에게 현금 또는 현금성 급여를 제공하는 복지 유형.'',10,JSON_OBJECT(''delivery_type'',''CASH'')),
(''WF_WELFARE_TYPE'',''IN_KIND'',''현물 급여'',''물품이나 장비 등 현물을 제공하는 복지 유형.'',20,JSON_OBJECT(''delivery_type'',''IN_KIND'')),
(''WF_WELFARE_TYPE'',''SERVICE'',''서비스 지원'',''돌봄, 상담, 재활 등 서비스를 제공하는 복지 유형.'',30,JSON_OBJECT(''delivery_type'',''SERVICE'')),
(''WF_WELFARE_TYPE'',''MEDICAL'',''의료 지원'',''진료, 검사, 치료, 약제비 등 의료 관련 지원을 제공하는 복지 유형.'',40,JSON_OBJECT(''delivery_type'',''MEDICAL'')),
(''WF_WELFARE_TYPE'',''HOUSING'',''주거 지원'',''주거비, 시설 개선 또는 거주 서비스를 제공하는 복지 유형.'',50,JSON_OBJECT(''delivery_type'',''HOUSING''));

-- 기존 Sequence Master Repository 값을 공통코드에 동기화한다.
INSERT INTO tmp_common_code_batch
SELECT
    ''SPS_SEQUENCE_FORMAT'',
    format_code,
    format_name,
    COALESCE(description, CONCAT(''Sequence Format: '', format_pattern)),
    ROW_NUMBER() OVER (ORDER BY format_code) * 10,
    JSON_OBJECT(
        ''format_pattern'', format_pattern,
        ''sequence_length'', sequence_length,
        ''master_repository'', ''cm_sequence_format''
    )
FROM cm_sequence_format
WHERE status_code = ''ACTIVE'';

-- SPS가 추가로 요구하는 식별자 Format을 공통코드 Repository에 설계·등록한다.
-- Master에 아직 없는 확장값이므로 registration_basis로 창작 근거를 명시한다.
INSERT INTO tmp_common_code_batch VALUES
(''SPS_SEQUENCE_FORMAT'',''PREFIX_NO_DATE_5'',''Prefix 무기한 5자리 포맷'',''날짜 구간 없이 Prefix별 연속 Sequence를 생성하는 범용 식별자 포맷.'',110,JSON_OBJECT(''format_pattern'',''{PREFIX}_{SEQ:5}'',''sequence_length'',5,''reset_policy_code'',''NO_RESET'',''registration_basis'',''SPS_DESIGNED_EXTENSION'')),
(''SPS_SEQUENCE_FORMAT'',''SPS_MONTH_5'',''SPS 연월 5자리 포맷'',''Business, Domain, Object Token, 연월과 5자리 Sequence로 Level별 식별자를 생성하는 SPS 포맷.'',120,JSON_OBJECT(''format_pattern'',''{BUSINESS}_{DOMAIN}_{OBJECT}_{YYYYMM}_{SEQ:5}'',''sequence_length'',5,''reset_policy_code'',''MONTHLY'',''registration_basis'',''SPS_DESIGNED_EXTENSION'')),
(''SPS_SEQUENCE_FORMAT'',''SPS_DAY_5'',''SPS 연월일 5자리 포맷'',''Business, Domain, Object Token, 연월일과 5자리 Sequence로 Runtime Object 식별자를 생성하는 SPS 포맷.'',130,JSON_OBJECT(''format_pattern'',''{BUSINESS}_{DOMAIN}_{OBJECT}_{YYYYMMDD}_{SEQ:5}'',''sequence_length'',5,''reset_policy_code'',''DAILY'',''registration_basis'',''SPS_DESIGNED_EXTENSION'')),
(''SPS_SEQUENCE_FORMAT'',''SPS_DATETIME_MILLISECOND_5'',''SPS 밀리초 5자리 포맷'',''Business, Domain, Object Token, 밀리초 시각과 5자리 Sequence로 실행 결과 식별자를 생성하는 SPS 포맷.'',140,JSON_OBJECT(''format_pattern'',''{BUSINESS}_{DOMAIN}_{OBJECT}_{YYYYMMDD}_{HHMMSSRRR}_{SEQ:5}'',''sequence_length'',5,''reset_policy_code'',''DAILY'',''time_precision'',''MILLISECOND'',''registration_basis'',''SPS_DESIGNED_EXTENSION''));

INSERT INTO tmp_common_code_batch
SELECT
    ''SPS_SEQUENCE_POLICY'',
    policy_code,
    policy_name,
    COALESCE(description, CONCAT(''Sequence Policy: '', policy_code)),
    sort_no * 10,
    JSON_OBJECT(
        ''date_format'', date_format,
        ''master_repository'', ''cm_sequence_policy''
    )
FROM cm_sequence_policy
WHERE status_code = ''ACTIVE'';

-- 기존 4개 Reset 정책만으로 표현되지 않는 SPS 단기 Runtime 운용 정책을 설계·등록한다.
INSERT INTO tmp_common_code_batch VALUES
(''SPS_SEQUENCE_POLICY'',''WEEKLY'',''주별 초기화'',''ISO 주차가 바뀌면 Sequence를 시작값부터 다시 생성하는 정책.'',110,JSON_OBJECT(''reset_scope'',''ISO_WEEK'',''date_format'',''YYYYWW'',''registration_basis'',''SPS_DESIGNED_EXTENSION'')),
(''SPS_SEQUENCE_POLICY'',''HOURLY'',''시간별 초기화'',''연월일시가 바뀌면 Sequence를 시작값부터 다시 생성하는 고빈도 Runtime 정책.'',120,JSON_OBJECT(''reset_scope'',''HOUR'',''date_format'',''YYYYMMDDHH'',''registration_basis'',''SPS_DESIGNED_EXTENSION''));

UPDATE cm_common_code_group
SET group_description = CASE group_code
    WHEN ''AI_ANALYSIS_STATUS'' THEN ''AI 분석 요청의 대기, 실행, 성공 및 실패 생명주기를 관리한다.''
    WHEN ''AI_PROVIDER'' THEN ''AI 또는 지능형 서비스의 외부 공급자를 관리한다.''
    WHEN ''HP_RISK_LEVEL'' THEN ''건강 및 Repository 영향 분석 결과의 위험 정도를 관리한다.''
    WHEN ''HS_HOSPITAL_TYPE'' THEN ''의료기관의 진료 기능과 기관 유형을 관리한다.''
    WHEN ''OC_DOCUMENT_TYPE'' THEN ''Document Compiler와 OCR Runtime이 처리하는 문서 입력 유형을 관리한다.''
    WHEN ''SPS_FUNCTION'' THEN ''Story Programming Framework의 Engine 및 Generator 기능을 관리한다.''
    WHEN ''SPS_SEQUENCE_FORMAT'' THEN ''식별자 Sequence 출력 패턴을 관리하며 Master 동기화 값과 SPS 확장 설계값을 함께 제공한다.''
    WHEN ''SPS_SEQUENCE_POLICY'' THEN ''Sequence 초기화 주기를 관리하며 Master 동기화 값과 SPS Runtime 확장 정책을 함께 제공한다.''
    WHEN ''WF_WELFARE_TYPE'' THEN ''복지 서비스의 급여 및 제공 방식을 관리한다.''
END,
    system_yn = ''Y'',
    status_code = ''ACTIVE'',
    updated_dt = CURRENT_TIMESTAMP,
    updated_by = @actor,
    client_ip = @client_ip,
    program_id = @program_id
WHERE group_code IN
(
    ''AI_ANALYSIS_STATUS'',''AI_PROVIDER'',''HP_RISK_LEVEL'',''HS_HOSPITAL_TYPE'',
    ''OC_DOCUMENT_TYPE'',''SPS_FUNCTION'',''SPS_SEQUENCE_FORMAT'',
    ''SPS_SEQUENCE_POLICY'',''WF_WELFARE_TYPE''
);

INSERT INTO cm_common_code
(
    group_code, code, code_name, common_code_description, sort_no,
    status_code, created_by, updated_by, client_ip, program_id, common_code_json
)
SELECT
    group_code, code, code_name, common_code_description, sort_no,
    ''ACTIVE'', @actor, @actor, @client_ip, @program_id, common_code_json
FROM tmp_common_code_batch
ON DUPLICATE KEY UPDATE
    code_name = VALUES(code_name),
    common_code_description = VALUES(common_code_description),
    sort_no = VALUES(sort_no),
    status_code = VALUES(status_code),
    updated_dt = CURRENT_TIMESTAMP,
    updated_by = VALUES(updated_by),
    client_ip = VALUES(client_ip),
    program_id = VALUES(program_id),
    common_code_json = VALUES(common_code_json);

-- 검증 1: 9개 Group이 모두 활성 상태이고 설명과 program_id를 가진다.
SELECT
    CASE
        WHEN COUNT(*) = 9
         AND SUM(group_description IS NULL OR group_description = '''') = 0
         AND SUM(program_id IS NULL OR program_id = '''') = 0
        THEN ''PASS'' ELSE ''FAIL''
    END AS group_validation_result,
    COUNT(*) AS group_count
FROM cm_common_code_group
WHERE group_code IN
(
    ''AI_ANALYSIS_STATUS'',''AI_PROVIDER'',''HP_RISK_LEVEL'',''HS_HOSPITAL_TYPE'',
    ''OC_DOCUMENT_TYPE'',''SPS_FUNCTION'',''SPS_SEQUENCE_FORMAT'',
    ''SPS_SEQUENCE_POLICY'',''WF_WELFARE_TYPE''
);

-- 검증 2: Batch 대상과 실제 공통코드의 누락·초과 여부.
SELECT t.group_code, t.code AS missing_code
FROM tmp_common_code_batch t
LEFT JOIN cm_common_code c
  ON c.group_code = t.group_code AND c.code = t.code
WHERE c.code IS NULL;

SELECT
    group_code,
    COUNT(*) AS code_count,
    COUNT(DISTINCT sort_no) AS distinct_sort_no_count,
    SUM(common_code_description IS NULL OR common_code_description = '''') AS missing_description_count,
    SUM(program_id IS NULL OR program_id = '''') AS missing_program_id_count
FROM cm_common_code
WHERE group_code IN
(
    ''AI_ANALYSIS_STATUS'',''AI_PROVIDER'',''HP_RISK_LEVEL'',''HS_HOSPITAL_TYPE'',
    ''OC_DOCUMENT_TYPE'',''SPS_FUNCTION'',''SPS_SEQUENCE_FORMAT'',
    ''SPS_SEQUENCE_POLICY'',''WF_WELFARE_TYPE''
)
GROUP BY group_code
ORDER BY group_code;

SELECT
    group_code, code, code_name, common_code_description, sort_no,
    status_code, program_id, common_code_json
FROM cm_common_code
WHERE group_code IN
(
    ''AI_ANALYSIS_STATUS'',''AI_PROVIDER'',''HP_RISK_LEVEL'',''HS_HOSPITAL_TYPE'',
    ''OC_DOCUMENT_TYPE'',''SPS_FUNCTION'',''SPS_SEQUENCE_FORMAT'',
    ''SPS_SEQUENCE_POLICY'',''WF_WELFARE_TYPE''
)
ORDER BY group_code, sort_no, code;

COMMIT;',
    'Y',
    'A',
    'DEV 실행 SUCCESS, COMMIT 완료, Group 9건 PASS, Code 42건 등록, 누락 0건, 설명·program_id 누락 0건, sort_no 중복 0건을 검증했다.',
    @actor, @batch_dt, @actor, @batch_dt, NOW(), @actor,
    'Y', 'Y', 'Y', 'Y', 'Y', 'Y',
    'ACTIVE', @program_id, @client_ip
)
ON DUPLICATE KEY UPDATE
    query_name = VALUES(query_name),
    query_description = VALUES(query_description),
    crud_type = VALUES(crud_type),
    sql_text = VALUES(sql_text),
    verified_yn = VALUES(verified_yn),
    certified_level_code = VALUES(certified_level_code),
    verification_description = VALUES(verification_description),
    verified_by = VALUES(verified_by),
    verified_dt = VALUES(verified_dt),
    updated_dt = VALUES(updated_dt),
    updated_by = VALUES(updated_by),
    story_programming_rule_pass_yn = VALUES(story_programming_rule_pass_yn),
    snake_case_pass_yn = VALUES(snake_case_pass_yn),
    table_exists_pass_yn = VALUES(table_exists_pass_yn),
    column_exists_pass_yn = VALUES(column_exists_pass_yn),
    crud_match_pass_yn = VALUES(crud_match_pass_yn),
    where_clause_pass_yn = VALUES(where_clause_pass_yn),
    status_code = VALUES(status_code),
    program_id = VALUES(program_id),
    client_ip = VALUES(client_ip);

SET @history_count = (
    SELECT COUNT(*)
    FROM cm_change_history
    WHERE created_dt = @batch_dt
      AND program_id = @program_id
      AND change_history_id LIKE 'CM_CO_CHANGE_HISTORY_20260722_093759_%'
);
SET @group_count = (
    SELECT COUNT(*)
    FROM cm_common_code_group
    WHERE group_code IN
    (
        'AI_ANALYSIS_STATUS','AI_PROVIDER','HP_RISK_LEVEL','HS_HOSPITAL_TYPE',
        'OC_DOCUMENT_TYPE','SPS_FUNCTION','SPS_SEQUENCE_FORMAT',
        'SPS_SEQUENCE_POLICY','WF_WELFARE_TYPE'
    )
);
SET @code_count = (
    SELECT COUNT(*)
    FROM cm_common_code
    WHERE program_id = @program_id
      AND group_code IN
    (
        'AI_ANALYSIS_STATUS','AI_PROVIDER','HP_RISK_LEVEL','HS_HOSPITAL_TYPE',
        'OC_DOCUMENT_TYPE','SPS_FUNCTION','SPS_SEQUENCE_FORMAT',
        'SPS_SEQUENCE_POLICY','WF_WELFARE_TYPE'
    )
);
SET @verified_query_count = (
    SELECT COUNT(*)
    FROM cm_verified_sql_query
    WHERE query_id = @query_id
      AND verified_yn = 'Y'
      AND certified_level_code = 'A'
      AND sql_text IS NOT NULL
      AND CHAR_LENGTH(sql_text) > 0
);

CREATE TEMPORARY TABLE tmp_common_code_batch_assert
(
    validation_result TINYINT NOT NULL,
    CONSTRAINT chk_common_code_batch_assert CHECK (validation_result = 1)
);

INSERT INTO tmp_common_code_batch_assert (validation_result)
VALUES
(
    IF(
        @history_count = 51
        AND @group_count = 9
        AND @code_count = 42
        AND @verified_query_count = 1,
        1,
        0
    )
);

DROP TEMPORARY TABLE tmp_common_code_batch_assert;

COMMIT;

SELECT @history_count AS history_count,
       @group_count AS group_count,
       @code_count AS code_count,
       @verified_query_count AS verified_query_count;

SELECT change_history_id, target_table_name, target_record_id,
       action_type, change_story, created_dt, program_id
FROM cm_change_history
WHERE created_dt = @batch_dt
  AND program_id = @program_id
ORDER BY change_history_id;

SELECT query_id, query_name, crud_type, verified_yn, certified_level_code,
       verification_description, CHAR_LENGTH(sql_text) AS sql_text_length,
       verified_by, verified_dt, status_code, program_id
FROM cm_verified_sql_query
WHERE query_id = @query_id;

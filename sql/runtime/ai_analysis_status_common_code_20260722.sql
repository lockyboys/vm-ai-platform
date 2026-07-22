-- AI_ANALYSIS_STATUS 공통코드 확정·등록 배치
-- 근거:
-- 1) AI_ANALYSIS_STATUS Group은 ACTIVE이나 Code 0건이다.
-- 2) OBJECT_ATTEMPT_STATUS의 공식 실행 생명주기는 READY/RUNNING/SUCCESS/FAILED를 사용한다.
-- 3) Generator Source도 READY/COMPLETED/FAILED 상태를 사용한다.
-- 판정: AI 분석 실행의 최소 공통 생명주기를 READY/RUNNING/SUCCESS/FAILED로 통일한다.

START TRANSACTION;

SET @program_id = 'CM_CO_PROGRAM_20260721_000000_00001';
SET @actor = 'SYSTEM';
SET @client_ip = '127.0.0.1';

UPDATE cm_common_code_group
SET group_description = 'AI 분석 요청의 실행 대기, 실행 중, 성공 및 실패 상태를 관리한다. Engine과 AI는 이 Group을 AI 분석 생명주기의 공식 Repository 원천으로 사용한다.',
    system_yn = 'Y',
    updated_dt = CURRENT_TIMESTAMP,
    updated_by = @actor,
    client_ip = @client_ip,
    program_id = @program_id
WHERE group_code = 'AI_ANALYSIS_STATUS';

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
    common_code_json
)
VALUES
(
    'AI_ANALYSIS_STATUS',
    'READY',
    '분석 대기',
    'AI 분석 요청이 등록되어 실행을 기다리는 상태.',
    10,
    'ACTIVE',
    @actor,
    @actor,
    @client_ip,
    @program_id,
    JSON_OBJECT(
        'lifecycle_order', 10,
        'terminal_yn', 'N',
        'allowed_next_codes', JSON_ARRAY('RUNNING', 'FAILED')
    )
),
(
    'AI_ANALYSIS_STATUS',
    'RUNNING',
    '분석 중',
    'AI Engine이 분석 작업을 실행하고 있는 상태.',
    20,
    'ACTIVE',
    @actor,
    @actor,
    @client_ip,
    @program_id,
    JSON_OBJECT(
        'lifecycle_order', 20,
        'terminal_yn', 'N',
        'allowed_next_codes', JSON_ARRAY('SUCCESS', 'FAILED')
    )
),
(
    'AI_ANALYSIS_STATUS',
    'SUCCESS',
    '분석 성공',
    'AI 분석이 정상적으로 완료되어 결과가 생성된 상태.',
    30,
    'ACTIVE',
    @actor,
    @actor,
    @client_ip,
    @program_id,
    JSON_OBJECT(
        'lifecycle_order', 30,
        'terminal_yn', 'Y',
        'allowed_next_codes', JSON_ARRAY()
    )
),
(
    'AI_ANALYSIS_STATUS',
    'FAILED',
    '분석 실패',
    'AI 분석 실행 중 오류가 발생하여 정상 결과를 생성하지 못한 상태.',
    40,
    'ACTIVE',
    @actor,
    @actor,
    @client_ip,
    @program_id,
    JSON_OBJECT(
        'lifecycle_order', 40,
        'terminal_yn', 'Y',
        'allowed_next_codes', JSON_ARRAY('READY')
    )
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
    common_code_json = VALUES(common_code_json);

-- 실행 전후 검증
SELECT
    group_code,
    group_name,
    group_description,
    status_code,
    system_yn,
    program_id
FROM cm_common_code_group
WHERE group_code = 'AI_ANALYSIS_STATUS';

SELECT
    group_code,
    code,
    code_name,
    common_code_description,
    sort_no,
    status_code,
    program_id,
    common_code_json
FROM cm_common_code
WHERE group_code = 'AI_ANALYSIS_STATUS'
ORDER BY sort_no, code;

SELECT
    CASE
        WHEN COUNT(*) = 4
         AND SUM(code IN ('READY', 'RUNNING', 'SUCCESS', 'FAILED')) = 4
         AND COUNT(DISTINCT sort_no) = 4
         AND SUM(common_code_description IS NULL OR common_code_description = '') = 0
         AND SUM(program_id IS NULL OR program_id = '') = 0
        THEN 'PASS'
        ELSE 'FAIL'
    END AS validation_result,
    COUNT(*) AS code_count
FROM cm_common_code
WHERE group_code = 'AI_ANALYSIS_STATUS';

COMMIT;

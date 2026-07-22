-- HP_RISK_LEVEL 공통코드 확정·등록 배치
-- 근거:
-- 1) sp_impact_analysis_result.risk_level_code의 기본값은 MEDIUM이다.
-- 2) Live Repository 데이터에서 HIGH와 LOW가 실제 사용된다.
-- 3) CRITICAL은 건강위험도 실사용 근거가 없어 제외한다.

START TRANSACTION;

SET @program_id = 'CM_CO_PROGRAM_20260721_000000_00001';
SET @actor = 'SYSTEM';
SET @client_ip = '127.0.0.1';

UPDATE cm_common_code_group
SET group_description = '건강 및 Repository 영향 분석 결과의 위험 정도를 낮음, 보통, 높음으로 관리한다. Generator, Engine 및 AI는 이 Group을 위험도 판정의 공식 Repository 원천으로 사용한다.',
    system_yn = 'Y',
    updated_dt = CURRENT_TIMESTAMP,
    updated_by = @actor,
    client_ip = @client_ip,
    program_id = @program_id
WHERE group_code = 'HP_RISK_LEVEL';

INSERT INTO cm_common_code
(
    group_code, code, code_name, common_code_description, sort_no,
    status_code, created_by, updated_by, client_ip, program_id, common_code_json
)
VALUES
(
    'HP_RISK_LEVEL', 'LOW', '낮음',
    '관찰 또는 일반 관리가 가능하며 변경 영향과 건강 위험이 낮은 단계.',
    10, 'ACTIVE', @actor, @actor, @client_ip, @program_id,
    JSON_OBJECT('severity_order', 10, 'requires_immediate_action_yn', 'N')
),
(
    'HP_RISK_LEVEL', 'MEDIUM', '보통',
    '추가 확인과 지속적인 관찰이 필요하며 기본 위험 단계로 사용하는 상태.',
    20, 'ACTIVE', @actor, @actor, @client_ip, @program_id,
    JSON_OBJECT('severity_order', 20, 'requires_immediate_action_yn', 'N')
),
(
    'HP_RISK_LEVEL', 'HIGH', '높음',
    '중대한 영향 또는 건강 위험 가능성이 있어 우선 검토와 대응이 필요한 단계.',
    30, 'ACTIVE', @actor, @actor, @client_ip, @program_id,
    JSON_OBJECT('severity_order', 30, 'requires_immediate_action_yn', 'Y')
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

SELECT group_code, group_name, group_description, status_code, system_yn, program_id
FROM cm_common_code_group
WHERE group_code = 'HP_RISK_LEVEL';

SELECT group_code, code, code_name, common_code_description, sort_no,
       status_code, program_id, common_code_json
FROM cm_common_code
WHERE group_code = 'HP_RISK_LEVEL'
ORDER BY sort_no, code;

SELECT
    CASE
        WHEN COUNT(*) = 3
         AND SUM(code IN ('LOW', 'MEDIUM', 'HIGH')) = 3
         AND COUNT(DISTINCT sort_no) = 3
         AND SUM(common_code_description IS NULL OR common_code_description = '') = 0
         AND SUM(program_id IS NULL OR program_id = '') = 0
        THEN 'PASS'
        ELSE 'FAIL'
    END AS validation_result,
    COUNT(*) AS code_count
FROM cm_common_code
WHERE group_code = 'HP_RISK_LEVEL';

SELECT DISTINCT r.risk_level_code AS unregistered_risk_level_code
FROM te_story_platform.sp_impact_analysis_result r
LEFT JOIN te_common.cm_common_code c
  ON c.group_code = 'HP_RISK_LEVEL'
 AND c.code = r.risk_level_code COLLATE utf8mb4_unicode_ci
WHERE c.code IS NULL
ORDER BY r.risk_level_code;

COMMIT;

/*
File: business_common_code_migration_20260721.sql
Purpose:
  Business CO(Common)를 CM(Common)으로 변경하여
  Domain CO(Core)와 전역 코드 표기 충돌을 해소한다.

Scope:
  - te_common.cm_common_code: CM_BUSINESS.CO -> CM_BUSINESS.CM
  - te_story_platform.sp_business: CO -> CM

Exclusions:
  - te_story_platform.sp_domain.domain_code = CO(Core)는 변경하지 않는다.
  - 이미 발급된 Object ID, program_id 등 역사 식별자의 CM_CO 문자열은 변경하지 않는다.
*/

SET NAMES utf8mb4;

START TRANSACTION;

-- 사전 충돌 방지: CM이 이미 존재하면 UPDATE로 중복키가 발생하여 전체 Transaction이 실패한다.
SELECT
    group_code,
    code,
    code_name,
    common_code_description,
    status_code
FROM te_common.cm_common_code
WHERE group_code = 'CM_BUSINESS'
  AND code IN ('CO', 'CM')
ORDER BY code;

SELECT
    business_code,
    business_name,
    business_description,
    active_yn
FROM te_story_platform.sp_business
WHERE business_code IN ('CO', 'CM')
ORDER BY business_code;

UPDATE te_common.cm_common_code
SET
    code = 'CM',
    common_code_description = '공통 기반 업무를 관리하는 독립 Business Classification.',
    updated_dt = CURRENT_TIMESTAMP,
    updated_by = 'SYSTEM',
    program_id = 'CM_BU_PROGRAM_20260721_000000_00002'
WHERE group_code = 'CM_BUSINESS'
  AND code = 'CO'
  AND code_name = 'Common';

UPDATE te_story_platform.sp_business
SET
    business_code = 'CM',
    updated_dt = CURRENT_TIMESTAMP,
    updated_by = 'SYSTEM',
    program_id = 'CM_BU_PROGRAM_20260721_000000_00002'
WHERE business_code = 'CO'
  AND business_name = 'Common';

COMMIT;

-- 1. Business Master 결과
SELECT
    business_code,
    business_name,
    business_description,
    active_yn,
    sort_no,
    updated_dt,
    updated_by,
    program_id
FROM te_story_platform.sp_business
WHERE business_code IN ('CO', 'CM')
ORDER BY business_code;

-- 2. CM_BUSINESS 공통코드 결과
SELECT
    group_code,
    code,
    code_name,
    common_code_description,
    sort_no,
    status_code,
    updated_dt,
    updated_by,
    program_id
FROM te_common.cm_common_code
WHERE group_code = 'CM_BUSINESS'
  AND code IN ('CO', 'CM')
ORDER BY code;

-- 3. Business CO 잔존 검증: 반드시 0
SELECT
    (
        SELECT COUNT(*)
        FROM te_story_platform.sp_business
        WHERE business_code = 'CO'
    )
    +
    (
        SELECT COUNT(*)
        FROM te_common.cm_common_code
        WHERE group_code = 'CM_BUSINESS'
          AND code = 'CO'
    ) AS remaining_business_co_count;

-- 4. Business CM 정합성 검증: 반드시 2
SELECT
    (
        SELECT COUNT(*)
        FROM te_story_platform.sp_business
        WHERE business_code = 'CM'
          AND business_name = 'Common'
    )
    +
    (
        SELECT COUNT(*)
        FROM te_common.cm_common_code
        WHERE group_code = 'CM_BUSINESS'
          AND code = 'CM'
          AND code_name = 'Common'
    ) AS migrated_business_cm_count;

-- 5. Domain CO(Core) 보존 검증: 반드시 1
SELECT
    domain_code,
    business_code,
    domain_name,
    domain_description,
    active_yn
FROM te_story_platform.sp_domain
WHERE domain_code = 'CO'
  AND domain_name = 'Core';

-- 6. Business-Domain 코드 교집합 검증: CO 충돌이 제거되어야 한다.
SELECT
    business.business_code AS overlapping_code,
    business.business_name,
    domain.domain_name
FROM te_story_platform.sp_business business
INNER JOIN te_story_platform.sp_domain domain
        ON domain.domain_code = business.business_code
ORDER BY business.business_code;

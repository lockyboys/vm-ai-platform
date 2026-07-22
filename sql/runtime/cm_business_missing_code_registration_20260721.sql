/*
  CM_BUSINESS missing-code registration

  Evidence:
    sp_business.business_code = BC, CO, HC, KC, SP
    sp_domain.domain_code     = CO, EN, GN, MT, RP, WF

  Scope:
    Register only BC and KC, which are present in sp_business and absent from
    CM_BUSINESS. Do not register them in DOMAIN_CODE, CM_DOMAIN, or SPS_DOMAIN.
*/

SET @program_id = 'CM_BU_PROGRAM_20260721_000000_00001';

START TRANSACTION;

INSERT INTO te_common.cm_common_code
(
    group_code,
    code,
    code_name,
    common_code_description,
    sort_no,
    status_code,
    created_by,
    updated_by,
    program_id
)
SELECT
    'CM_BUSINESS',
    source.code,
    source.code_name,
    source.common_code_description,
    source.sort_no,
    'ACTIVE',
    'SYSTEM',
    'SYSTEM',
    @program_id
FROM
(
    SELECT
        'BC' AS code,
        'Busan Care' AS code_name,
        '부산 돌봄 서비스 Business. 하위 Domain을 소유하는 독립 Business Classification.' AS common_code_description,
        40 AS sort_no
    UNION ALL
    SELECT
        'KC',
        'KDT Care',
        'KDT 돌봄 서비스 Business. 하위 Domain을 소유하는 독립 Business Classification.',
        50
) source
INNER JOIN te_story_platform.sp_business business
        ON business.business_code = source.code
LEFT JOIN te_story_platform.sp_domain domain
       ON domain.domain_code = source.code
WHERE domain.domain_code IS NULL
ON DUPLICATE KEY UPDATE
    code_name = VALUES(code_name),
    common_code_description = VALUES(common_code_description),
    sort_no = VALUES(sort_no),
    status_code = VALUES(status_code),
    updated_by = VALUES(updated_by),
    updated_dt = CURRENT_TIMESTAMP,
    program_id = VALUES(program_id);

COMMIT;

SELECT
    group_code,
    code,
    code_name,
    common_code_description,
    sort_no,
    status_code,
    program_id
FROM te_common.cm_common_code
WHERE group_code = 'CM_BUSINESS'
  AND code IN ('BC', 'KC')
ORDER BY sort_no, code;

SELECT COUNT(*) AS missing_cm_business_code_count
FROM te_story_platform.sp_business business
LEFT JOIN te_common.cm_common_code common_code
       ON common_code.group_code = 'CM_BUSINESS'
      AND common_code.code = business.business_code
WHERE common_code.code IS NULL;

SELECT COUNT(*) AS new_business_domain_overlap_count
FROM te_common.cm_common_code business_code
INNER JOIN te_story_platform.sp_domain domain
        ON domain.domain_code = business_code.code
WHERE business_code.group_code = 'CM_BUSINESS'
  AND business_code.code IN ('BC', 'KC');

SELECT
    group_code,
    code,
    code_name,
    status_code
FROM te_common.cm_common_code
WHERE group_code IN ('DOMAIN_CODE', 'CM_DOMAIN', 'SPS_DOMAIN')
  AND code IN ('BC', 'KC')
ORDER BY group_code, code;

SELECT
    business.business_code AS overlapping_code,
    business.business_name,
    domain.domain_name
FROM te_story_platform.sp_business business
INNER JOIN te_story_platform.sp_domain domain
        ON domain.domain_code = business.business_code
ORDER BY business.business_code;

/*
File Story:
    COMMON의 확정 Domain Code CO(Common)를 cm_business_domain SSOT에 등록한다.

Change History:
    2026-07-28 SYSTEM Initial registration.

Principles:
    - Repository First
    - Idempotent DML
    - No schema change
*/

START TRANSACTION;

INSERT INTO cm_business_domain (
    business_domain_id,
    business_domain_code,
    business_domain_name,
    description,
    sort_no,
    created_by,
    updated_by,
    program_id,
    client_ip,
    status_code
)
SELECT
    'CM_CO_BUSINESS_DOMAIN_20260728_230000_00001',
    'CO',
    'Common',
    'Framework 공통 Repository와 공통 기능을 관리하는 공식 Domain.',
    5,
    'SYSTEM',
    'SYSTEM',
    'register_common_domain_co_20260728.sql',
    '127.0.0.1',
    'ACTIVE'
WHERE NOT EXISTS (
    SELECT 1
    FROM cm_business_domain
    WHERE business_domain_code = 'CO'
      AND deleted_dt IS NULL
);

COMMIT;

SELECT
    business_domain_id,
    business_domain_code,
    business_domain_name,
    description,
    sort_no,
    status_code,
    deleted_dt
FROM cm_business_domain
WHERE business_domain_code = 'CO';

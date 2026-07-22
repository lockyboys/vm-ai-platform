-- SPS Database Role registration and Harness read-permission batch
-- Approved scope: BUSAN/KDT role registration; AI/BUSAN/KDT Harness read access.
-- Database Object registration is intentionally excluded until the approved Object Level is reconciled with the fixed SPS hierarchy.

START TRANSACTION;

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
    lifecycle_status_code
)
VALUES
(
    'SPS_DATABASE_ROLE',
    'BUSAN',
    'te_busan_care',
    'Busan Care Repository Database',
    5,
    'ACTIVE',
    'SYSTEM',
    'SYSTEM',
    '127.0.0.1',
    'SPS_DATABASE_ROLE_REGISTRATION_20260722',
    'CREATE_MAINTAIN'
),
(
    'SPS_DATABASE_ROLE',
    'KDT',
    'te_kdt_care',
    'KDT Care Repository Database',
    6,
    'ACTIVE',
    'SYSTEM',
    'SYSTEM',
    '127.0.0.1',
    'SPS_DATABASE_ROLE_REGISTRATION_20260722',
    'CREATE_MAINTAIN'
)
ON DUPLICATE KEY UPDATE
    code_name = VALUES(code_name),
    common_code_description = VALUES(common_code_description),
    sort_no = VALUES(sort_no),
    status_code = VALUES(status_code),
    updated_by = VALUES(updated_by),
    client_ip = VALUES(client_ip),
    program_id = VALUES(program_id),
    lifecycle_status_code = VALUES(lifecycle_status_code);

COMMIT;

GRANT SELECT, SHOW VIEW ON `te_ai_platform`.* TO 'te_app_user'@'localhost';
GRANT SELECT, SHOW VIEW ON `te_busan_care`.* TO 'te_app_user'@'localhost';
GRANT SELECT, SHOW VIEW ON `te_kdt_care`.* TO 'te_app_user'@'localhost';
GRANT SELECT, SHOW VIEW ON `te_ai_platform`.* TO 'te_app_user'@'%';
GRANT SELECT, SHOW VIEW ON `te_busan_care`.* TO 'te_app_user'@'%';
GRANT SELECT, SHOW VIEW ON `te_kdt_care`.* TO 'te_app_user'@'%';

SELECT
    group_code,
    code,
    code_name,
    common_code_description,
    sort_no,
    status_code,
    lifecycle_status_code,
    program_id
FROM cm_common_code
WHERE group_code = 'SPS_DATABASE_ROLE'
ORDER BY sort_no, code;

SELECT
    GRANTEE,
    TABLE_SCHEMA,
    PRIVILEGE_TYPE
FROM information_schema.schema_privileges
WHERE GRANTEE IN (
    QUOTE(CONCAT('te_app_user', '@', 'localhost')),
    QUOTE(CONCAT('te_app_user', '@', '%'))
)
  AND TABLE_SCHEMA IN (
    'te_ai_platform',
    'te_busan_care',
    'te_kdt_care'
)
ORDER BY GRANTEE, TABLE_SCHEMA, PRIVILEGE_TYPE;

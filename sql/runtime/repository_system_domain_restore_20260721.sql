-- Restore official SY Domain for System-owned identifiers.
-- Source of truth: DOMAIN_CODE.SY and immediate pre-correction backups.

START TRANSACTION;

UPDATE te_common.system_user
SET user_login_id = CONCAT('CM_SY_', SUBSTRING(user_login_id, 7))
WHERE user_login_id LIKE 'CM\\_CO\\_USER\\_LOGIN\\_%';

UPDATE te_common.system_menu_button_crud_permission
SET permission_id = CONCAT('CM_SY_', SUBSTRING(permission_id, 7))
WHERE permission_id LIKE 'CM\\_CO\\_PERMISSION\\_%';

COMMIT;

SELECT user_id, user_login_id
FROM te_common.system_user
ORDER BY user_id;

SELECT permission_id, menu_code, button_code
FROM te_common.system_menu_button_crud_permission
ORDER BY permission_id;

SELECT
    (SELECT COUNT(*) FROM te_common.system_user
     WHERE user_login_id LIKE 'CM\\_CO\\_USER\\_LOGIN\\_%') AS invalid_user_login_domain_count,
    (SELECT COUNT(*) FROM te_common.system_menu_button_crud_permission
     WHERE permission_id LIKE 'CM\\_CO\\_PERMISSION\\_%') AS invalid_permission_domain_count;

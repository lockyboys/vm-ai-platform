/*
 * File Story
 * system_user를 SUSPENDED(HOLD) 상태로 전환하고 사용자별 변경 근거를 cm_change_history에 기록한다.
 *
 * Change History
 * 20260730 | Codex | system_user 상태 전환과 변경 이력 등록을 하나의 트랜잭션으로 처리한다.
 *
 * Safety
 * - 기존 STATUS_CODE.SUSPENDED가 활성 상태일 때만 처리한다.
 * - 기존 변경 이력의 UPDATE 작업유형을 재사용한다.
 * - 공통코드 또는 이력 계약이 없으면 상태·이력 데이터를 변경하지 않는다.
 * - system_user 데이터는 삭제·rename·merge하지 않는다.
 */

USE te_common;

SET @program_id = 'SYSTEM_USER_HOLD_20260730';
SET @actor_id = 'SYSTEM';
SET @client_ip = '127.0.0.1';

SET @suspended_status_code =
(
    SELECT code
    FROM cm_common_code
    WHERE group_code = 'STATUS_CODE'
      AND code = 'SUSPENDED'
      AND status_code = 'ACTIVE'
      AND deleted_dt IS NULL
    LIMIT 1
);

SET @update_action_type =
(
    SELECT action_type
    FROM cm_change_history
    WHERE action_type = 'UPDATE'
    ORDER BY created_dt DESC
    LIMIT 1
);

SET @suspended_status_code_for_system_user =
    CONVERT(@suspended_status_code USING utf8mb4) COLLATE utf8mb4_general_ci;
SET @program_id_for_history =
    CONVERT(@program_id USING utf8mb4) COLLATE utf8mb4_unicode_ci;

START TRANSACTION;

UPDATE system_user
SET
    status_code = @suspended_status_code_for_system_user,
    updated_dt = CURRENT_TIMESTAMP,
    updated_by = @actor_id,
    program_id = @program_id,
    client_ip = @client_ip
WHERE @suspended_status_code IS NOT NULL
  AND @update_action_type IS NOT NULL
  AND status_code <> @suspended_status_code_for_system_user
  AND deleted_dt IS NULL;

INSERT INTO cm_change_history
(
    change_history_id,
    target_database_name,
    target_table_name,
    target_record_id,
    action_type,
    change_story,
    created_by,
    created_dt,
    client_ip,
    program_id,
    status_code
)
SELECT
    CONCAT(
        'CM_CO_CHANGE_HISTORY_',
        DATE_FORMAT(CURRENT_TIMESTAMP, '%Y%m%d_%H%i%s'),
        '_',
        RIGHT(system_user.user_id, 5)
    ),
    'te_common',
    'system_user',
    CONVERT(system_user.user_id USING utf8mb4) COLLATE utf8mb4_unicode_ci,
    @update_action_type,
    'system_user를 사용자·권한 Repository 재설계 전 SUSPENDED(HOLD) 상태로 전환한다. 데이터 보존, rename 금지, drop 금지이며 cm_member·cm_role·cm_member_role·RL_ROLE 대조 후 재판정한다.',
    @actor_id,
    CURRENT_TIMESTAMP,
    @client_ip,
    @program_id_for_history,
    'ACTIVE'
FROM system_user
WHERE @suspended_status_code IS NOT NULL
  AND @update_action_type IS NOT NULL
  AND status_code = @suspended_status_code_for_system_user
  AND deleted_dt IS NULL
  AND NOT EXISTS
  (
      SELECT 1
      FROM cm_change_history
      WHERE target_database_name = 'te_common'
        AND target_table_name = 'system_user'
        AND target_record_id =
            CONVERT(system_user.user_id USING utf8mb4) COLLATE utf8mb4_unicode_ci
        AND action_type = @update_action_type
        AND program_id = @program_id_for_history
  );

COMMIT;

SELECT
    @suspended_status_code AS resolved_suspended_status_code,
    @update_action_type AS resolved_update_action_type;

SELECT
    user_id,
    user_login_id,
    user_name,
    user_role_code,
    status_code,
    updated_by,
    program_id
FROM system_user
ORDER BY user_id;

SELECT
    change_history_id,
    target_record_id,
    action_type,
    change_story,
    created_dt,
    program_id
FROM cm_change_history
WHERE target_database_name = 'te_common'
  AND target_table_name = 'system_user'
  AND program_id = @program_id_for_history
ORDER BY created_dt, change_history_id;

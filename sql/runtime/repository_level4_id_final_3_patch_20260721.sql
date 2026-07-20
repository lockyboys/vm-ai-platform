-- Repository Level 4 ID Final Three Migration
-- Existing backup: te_common.cm_change_history_bkp_l4_20260721

START TRANSACTION;

UPDATE te_common.cm_change_history
SET target_record_id = CASE target_record_id
    WHEN 'COUNTRY'  THEN 'CM_CM_COUNTRY_20260720_231950_00001'
    WHEN 'LANGUAGE' THEN 'CM_CM_LANGUAGE_20260720_231950_00001'
    WHEN 'LOCALE'   THEN 'CM_CM_LOCALE_20260720_231950_00001'
    ELSE target_record_id
END
WHERE target_record_id IN ('COUNTRY', 'LANGUAGE', 'LOCALE');

COMMIT;

SELECT
    change_history_id,
    target_database_name,
    target_table_name,
    target_record_id,
    action_type
FROM te_common.cm_change_history
WHERE change_history_id IN (
    'CM_CM_CHANGE_HISTORY_20260720_231950_00003',
    'CM_CM_CHANGE_HISTORY_20260720_231950_00004',
    'CM_CM_CHANGE_HISTORY_20260720_231950_00005'
)
ORDER BY change_history_id;

SELECT COUNT(*) AS invalid_target_record_id_count
FROM te_common.cm_change_history
WHERE target_record_id IS NOT NULL
  AND target_record_id <> ''
  AND target_record_id NOT REGEXP
      '^[A-Z0-9]+_[A-Z0-9]+_[A-Z0-9_]+_[0-9]{8}_[0-9]{6}_[0-9]{5}$';

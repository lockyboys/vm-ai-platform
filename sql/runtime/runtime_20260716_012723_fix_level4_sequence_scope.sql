START TRANSACTION;

UPDATE sp_identifier_blueprint
SET
    sequence_scope_code = 'DAILY',
    updated_dt = CURRENT_TIMESTAMP,
    updated_by = 'SYSTEM',
    program_id = 'fix_level4_sequence_scope',
    client_ip = '127.0.0.1'
WHERE blueprint_code IN
(
    'LEVEL4_NORMAL',
    'LEVEL4_HIGH'
)
  AND object_level = 4
  AND sequence_scope_code IN
(
    'SECOND',
    'MILLISECOND'
)
  AND status_code = 'ACTIVE'
  AND deleted_dt IS NULL;

SELECT ROW_COUNT() AS updated_row_count;

SELECT
    blueprint_id,
    blueprint_code,
    object_level,
    identifier_pattern,
    date_format,
    time_format,
    sequence_scope_code,
    sequence_length,
    updated_dt,
    updated_by,
    program_id
FROM sp_identifier_blueprint
WHERE blueprint_code IN
(
    'LEVEL4_NORMAL',
    'LEVEL4_HIGH'
)
  AND deleted_dt IS NULL
ORDER BY blueprint_code;

COMMIT;

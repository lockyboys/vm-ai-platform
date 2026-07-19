/* SPS L0-L5 Object hierarchy compatibility migration */
SET NAMES utf8mb4;
USE te_story_platform;

/* object_id standard: VARCHAR(99) */
ALTER TABLE sp_object_lifecycle
    MODIFY object_id VARCHAR(99) NOT NULL;

ALTER TABLE sp_execution_history
    MODIFY object_id VARCHAR(99) NULL;

ALTER TABLE sp_knowledge_hold
    ADD COLUMN IF NOT EXISTS object_id VARCHAR(99) NULL
        COMMENT 'Canonical SPS Object Identifier' AFTER knowledge_id,
    ADD INDEX IF NOT EXISTS ix_sp_knowledge_object_id (object_id);

ALTER TABLE te_common.cm_verified_sql_query
    ADD COLUMN IF NOT EXISTS object_id VARCHAR(99) NULL
        COMMENT 'Canonical SPS SQL Object Identifier' AFTER query_id,
    ADD INDEX IF NOT EXISTS ix_cm_verified_sql_object_id (object_id);

/* L0 has no date, time or sequence token. */
INSERT INTO sp_identifier_blueprint
(
    blueprint_id, blueprint_code, blueprint_name, object_level,
    identifier_pattern, date_format, time_format, random_length,
    sequence_length, sequence_scope_code, sort_no, enabled_yn,
    status_code, remark, created_by, updated_by, program_id, client_ip
)
VALUES
(
    'IB_LEVEL0_PLATFORM', 'LEVEL0_PLATFORM', 'Level 0 - Platform Identifier', 0,
    '{BUSINESS}_{DOMAIN}_{OBJECT}', NULL, NULL, 0,
    5, 'NONE', 0, 'Y',
    'ACTIVE', 'L0 Platform: no date, time or sequence token',
    'OBJECT_HIERARCHY_MIGRATION', 'OBJECT_HIERARCHY_MIGRATION',
    'SPS_OBJECT_HIERARCHY_L0_L5_20260719', '127.0.0.1'
)
ON DUPLICATE KEY UPDATE
    blueprint_name = VALUES(blueprint_name),
    object_level = VALUES(object_level),
    identifier_pattern = VALUES(identifier_pattern),
    date_format = NULL,
    time_format = NULL,
    random_length = 0,
    sequence_scope_code = 'NONE',
    enabled_yn = 'Y',
    status_code = 'ACTIVE',
    updated_by = VALUES(updated_by),
    program_id = VALUES(program_id),
    client_ip = VALUES(client_ip);

/* L5 uses SSCC: seconds plus real centiseconds. */
INSERT INTO sp_identifier_blueprint
(
    blueprint_id, blueprint_code, blueprint_name, object_level,
    identifier_pattern, date_format, time_format, random_length,
    sequence_length, sequence_scope_code, sort_no, enabled_yn,
    status_code, remark, created_by, updated_by, program_id, client_ip
)
VALUES
(
    'IB_LEVEL5_NORMAL', 'LEVEL5_NORMAL', 'Level 5 - Centisecond Identifier', 5,
    '{BUSINESS}_{DOMAIN}_{OBJECT}_{YYYYMMDD}_{HHMMSSCC}_{SEQ5}',
    'YYYYMMDD', 'HHMMSSCC', 0, 5, 'DAILY', 50, 'Y',
    'ACTIVE', 'L5: SSCC means second(2) plus real centisecond(2)',
    'OBJECT_HIERARCHY_MIGRATION', 'OBJECT_HIERARCHY_MIGRATION',
    'SPS_OBJECT_HIERARCHY_L0_L5_20260719', '127.0.0.1'
)
ON DUPLICATE KEY UPDATE
    blueprint_name = VALUES(blueprint_name),
    object_level = 5,
    identifier_pattern = VALUES(identifier_pattern),
    date_format = VALUES(date_format),
    time_format = VALUES(time_format),
    random_length = 0,
    sequence_length = 5,
    sequence_scope_code = 'DAILY',
    enabled_yn = 'Y',
    status_code = 'ACTIVE',
    updated_by = VALUES(updated_by),
    program_id = VALUES(program_id),
    client_ip = VALUES(client_ip);

SELECT object_level, blueprint_code, identifier_pattern,
       time_format, random_length, sequence_scope_code, enabled_yn, status_code
FROM sp_identifier_blueprint
WHERE object_level IN (0, 4, 5)
ORDER BY object_level, sort_no, blueprint_code;

SELECT table_schema, table_name, column_name, column_type
FROM information_schema.columns
WHERE (table_schema, table_name, column_name) IN
(
    ('te_story_platform', 'sp_object', 'object_id'),
    ('te_story_platform', 'sp_object_lifecycle', 'object_id'),
    ('te_story_platform', 'sp_execution_history', 'object_id'),
    ('te_story_platform', 'sp_knowledge_hold', 'object_id'),
    ('te_common', 'cm_verified_sql_query', 'object_id')
)
ORDER BY table_schema, table_name;

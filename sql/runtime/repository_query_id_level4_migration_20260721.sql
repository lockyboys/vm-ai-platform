/* ============================================================================
SPS Query ID Level 4 Migration
Format: BUSINESS_DOMAIN_OBJECT_YYYYMMDD_HHMMSS_SEQ5
Scope : cm_verified_sql_query 7 rows and all live references
============================================================================ */

-- 1. Backup structures
CREATE TABLE IF NOT EXISTS te_common.cm_verified_sql_query_backup_query_id_20260721_01
LIKE te_common.cm_verified_sql_query;

CREATE TABLE IF NOT EXISTS te_common.system_menu_button_backup_query_id_20260721_01
LIKE te_common.system_menu_button;

CREATE TABLE IF NOT EXISTS te_story_platform.sp_relationship_backup_query_id_20260721_01
LIKE te_story_platform.sp_relationship;

-- 2. Backup exact affected rows
START TRANSACTION;

INSERT IGNORE INTO te_common.cm_verified_sql_query_backup_query_id_20260721_01
SELECT *
FROM te_common.cm_verified_sql_query
WHERE query_id IN (
    'health_report_delete',
    'health_report_insert',
    'health_report_select_list',
    'health_report_update',
    'SQL_20260712_200551K98_00001',
    'SQL_20260720_COMMON_CODE_GROUP_CANDIDATE_00001',
    'SQL_20260720_REPOSITORY_RELATION_ANALYSIS_00001'
);

INSERT IGNORE INTO te_common.system_menu_button_backup_query_id_20260721_01
SELECT *
FROM te_common.system_menu_button
WHERE query_id IN (
    'health_report_delete',
    'health_report_insert',
    'health_report_select_list',
    'health_report_update'
);

INSERT IGNORE INTO te_story_platform.sp_relationship_backup_query_id_20260721_01
SELECT *
FROM te_story_platform.sp_relationship
WHERE target_object_id = 'SQL_20260712_200551K98_00001';

COMMIT;

-- 3. Backup verification
SELECT
    (SELECT COUNT(*) FROM te_common.cm_verified_sql_query_backup_query_id_20260721_01) AS query_backup_count,
    (SELECT COUNT(*) FROM te_common.system_menu_button_backup_query_id_20260721_01) AS menu_backup_count,
    (SELECT COUNT(*) FROM te_story_platform.sp_relationship_backup_query_id_20260721_01) AS relationship_backup_count;

-- 4. Migrate references and primary identifiers together
START TRANSACTION;

UPDATE te_common.system_menu_button
SET
    query_id = CASE query_id
        WHEN 'health_report_delete'
            THEN 'SP_RP_SQL_QUERY_20260623_030631_00001'
        WHEN 'health_report_insert'
            THEN 'SP_RP_SQL_QUERY_20260623_030631_00002'
        WHEN 'health_report_select_list'
            THEN 'SP_RP_SQL_QUERY_20260623_030631_00003'
        WHEN 'health_report_update'
            THEN 'SP_RP_SQL_QUERY_20260623_030631_00004'
        ELSE query_id
    END,
    updated_dt = NOW(),
    updated_by = 'SYSTEM',
    program_id = 'SPS_QUERY_ID_LEVEL4_MIGRATION'
WHERE query_id IN (
    'health_report_delete',
    'health_report_insert',
    'health_report_select_list',
    'health_report_update'
);

UPDATE te_common.sql_guard_execution_log
SET query_id = CASE query_id
    WHEN 'health_report_delete'
        THEN 'SP_RP_SQL_QUERY_20260623_030631_00001'
    WHEN 'health_report_insert'
        THEN 'SP_RP_SQL_QUERY_20260623_030631_00002'
    WHEN 'health_report_select_list'
        THEN 'SP_RP_SQL_QUERY_20260623_030631_00003'
    WHEN 'health_report_update'
        THEN 'SP_RP_SQL_QUERY_20260623_030631_00004'
    WHEN 'SQL_20260712_200551K98_00001'
        THEN 'SP_RP_SQL_QUERY_20260712_201015_00001'
    WHEN 'SQL_20260720_COMMON_CODE_GROUP_CANDIDATE_00001'
        THEN 'SP_RP_SQL_QUERY_20260720_231939_00001'
    WHEN 'SQL_20260720_REPOSITORY_RELATION_ANALYSIS_00001'
        THEN 'SP_RP_SQL_QUERY_20260720_231939_00002'
    ELSE query_id
END
WHERE query_id IN (
    'health_report_delete',
    'health_report_insert',
    'health_report_select_list',
    'health_report_update',
    'SQL_20260712_200551K98_00001',
    'SQL_20260720_COMMON_CODE_GROUP_CANDIDATE_00001',
    'SQL_20260720_REPOSITORY_RELATION_ANALYSIS_00001'
);

UPDATE te_common.sql_guard_verification_log
SET
    query_id = CASE query_id
        WHEN 'health_report_delete'
            THEN 'SP_RP_SQL_QUERY_20260623_030631_00001'
        WHEN 'health_report_insert'
            THEN 'SP_RP_SQL_QUERY_20260623_030631_00002'
        WHEN 'health_report_select_list'
            THEN 'SP_RP_SQL_QUERY_20260623_030631_00003'
        WHEN 'health_report_update'
            THEN 'SP_RP_SQL_QUERY_20260623_030631_00004'
        WHEN 'SQL_20260712_200551K98_00001'
            THEN 'SP_RP_SQL_QUERY_20260712_201015_00001'
        WHEN 'SQL_20260720_COMMON_CODE_GROUP_CANDIDATE_00001'
            THEN 'SP_RP_SQL_QUERY_20260720_231939_00001'
        WHEN 'SQL_20260720_REPOSITORY_RELATION_ANALYSIS_00001'
            THEN 'SP_RP_SQL_QUERY_20260720_231939_00002'
        ELSE query_id
    END,
    updated_dt = NOW(),
    updated_by = 'SYSTEM',
    program_id = 'SPS_QUERY_ID_LEVEL4_MIGRATION'
WHERE query_id IN (
    'health_report_delete',
    'health_report_insert',
    'health_report_select_list',
    'health_report_update',
    'SQL_20260712_200551K98_00001',
    'SQL_20260720_COMMON_CODE_GROUP_CANDIDATE_00001',
    'SQL_20260720_REPOSITORY_RELATION_ANALYSIS_00001'
);

UPDATE te_story_platform.sp_relationship
SET
    target_object_id = 'SP_RP_SQL_QUERY_20260712_201015_00001',
    updated_dt = NOW(),
    updated_by = 'SYSTEM',
    program_id = 'SPS_QUERY_ID_LEVEL4_MIGRATION'
WHERE target_object_id = 'SQL_20260712_200551K98_00001'
  AND target_object_type_code = 'VERIFIED_SQL';

UPDATE te_common.cm_verified_sql_query
SET
    query_id = CASE query_id
        WHEN 'health_report_delete'
            THEN 'SP_RP_SQL_QUERY_20260623_030631_00001'
        WHEN 'health_report_insert'
            THEN 'SP_RP_SQL_QUERY_20260623_030631_00002'
        WHEN 'health_report_select_list'
            THEN 'SP_RP_SQL_QUERY_20260623_030631_00003'
        WHEN 'health_report_update'
            THEN 'SP_RP_SQL_QUERY_20260623_030631_00004'
        WHEN 'SQL_20260712_200551K98_00001'
            THEN 'SP_RP_SQL_QUERY_20260712_201015_00001'
        WHEN 'SQL_20260720_COMMON_CODE_GROUP_CANDIDATE_00001'
            THEN 'SP_RP_SQL_QUERY_20260720_231939_00001'
        WHEN 'SQL_20260720_REPOSITORY_RELATION_ANALYSIS_00001'
            THEN 'SP_RP_SQL_QUERY_20260720_231939_00002'
        ELSE query_id
    END,
    updated_dt = NOW(),
    updated_by = 'SYSTEM',
    program_id = 'SPS_QUERY_ID_LEVEL4_MIGRATION'
WHERE query_id IN (
    'health_report_delete',
    'health_report_insert',
    'health_report_select_list',
    'health_report_update',
    'SQL_20260712_200551K98_00001',
    'SQL_20260720_COMMON_CODE_GROUP_CANDIDATE_00001',
    'SQL_20260720_REPOSITORY_RELATION_ANALYSIS_00001'
);

COMMIT;

-- 5. Verify seven Level 4 Query IDs
SELECT
    query_id,
    query_name,
    created_dt,
    status_code
FROM te_common.cm_verified_sql_query
ORDER BY created_dt, query_id;

-- 6. Old Query IDs must be zero
SELECT COUNT(*) AS old_query_id_count
FROM te_common.cm_verified_sql_query
WHERE query_id IN (
    'health_report_delete',
    'health_report_insert',
    'health_report_select_list',
    'health_report_update',
    'SQL_20260712_200551K98_00001',
    'SQL_20260720_COMMON_CODE_GROUP_CANDIDATE_00001',
    'SQL_20260720_REPOSITORY_RELATION_ANALYSIS_00001'
);

-- 7. Every Query ID must match the confirmed Level 4 format
SELECT COUNT(*) AS invalid_query_id_count
FROM te_common.cm_verified_sql_query
WHERE query_id NOT REGEXP '^[A-Z0-9]+_[A-Z0-9]+_[A-Z0-9_]+_[0-9]{8}_[0-9]{6}_[0-9]{5}$';

-- 8. Verify live references
SELECT
    button_code,
    query_id
FROM te_common.system_menu_button
ORDER BY button_code;

SELECT
    relationship_id,
    target_object_id,
    target_object_type_code
FROM te_story_platform.sp_relationship
WHERE target_object_type_code = 'VERIFIED_SQL'
ORDER BY relationship_id;

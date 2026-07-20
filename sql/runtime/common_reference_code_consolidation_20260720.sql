/* ============================================================================
SPS Common Reference Code Consolidation
Target  : te_common.cm_country, cm_language, cm_locale
SSOT    : te_common.cm_common_code_group + cm_common_code
Groups  : COUNTRY, LANGUAGE, LOCALE
Policy  : one-time migration hardcoding is allowed; Runtime hardcoding is not.
============================================================================ */

USE te_common;

SET @migration_program_id = 'SPS_COMMON_REFERENCE_CONSOLIDATION';
SET @migration_client_ip = '127.0.0.1';

/* 1. Preflight: current rows and target Group collision */
SELECT
    (SELECT COUNT(*) FROM cm_country) AS country_source_count,
    (SELECT COUNT(*) FROM cm_language) AS language_source_count,
    (SELECT COUNT(*) FROM cm_locale) AS locale_source_count,
    (SELECT COUNT(*) FROM cm_common_code_group
      WHERE group_code IN ('COUNTRY', 'LANGUAGE', 'LOCALE')) AS existing_target_group_count,
    (SELECT COUNT(*) FROM cm_common_code
      WHERE group_code IN ('COUNTRY', 'LANGUAGE', 'LOCALE')) AS existing_target_code_count;

/* 2. Full backup */
CREATE TABLE IF NOT EXISTS cm_country_backup_common_code_20260720_01
LIKE cm_country;

CREATE TABLE IF NOT EXISTS cm_language_backup_common_code_20260720_01
LIKE cm_language;

CREATE TABLE IF NOT EXISTS cm_locale_backup_common_code_20260720_01
LIKE cm_locale;

CREATE TABLE IF NOT EXISTS cm_common_code_group_backup_reference_20260720_01
LIKE cm_common_code_group;

CREATE TABLE IF NOT EXISTS cm_common_code_backup_reference_20260720_01
LIKE cm_common_code;

START TRANSACTION;

INSERT IGNORE INTO cm_country_backup_common_code_20260720_01
SELECT * FROM cm_country;

INSERT IGNORE INTO cm_language_backup_common_code_20260720_01
SELECT * FROM cm_language;

INSERT IGNORE INTO cm_locale_backup_common_code_20260720_01
SELECT * FROM cm_locale;

INSERT IGNORE INTO cm_common_code_group_backup_reference_20260720_01
SELECT * FROM cm_common_code_group;

INSERT IGNORE INTO cm_common_code_backup_reference_20260720_01
SELECT * FROM cm_common_code;

COMMIT;

/* 3. Backup verification */
SELECT
    (SELECT COUNT(*) FROM cm_country) AS country_original_count,
    (SELECT COUNT(*) FROM cm_country_backup_common_code_20260720_01) AS country_backup_count,
    (SELECT COUNT(*) FROM cm_language) AS language_original_count,
    (SELECT COUNT(*) FROM cm_language_backup_common_code_20260720_01) AS language_backup_count,
    (SELECT COUNT(*) FROM cm_locale) AS locale_original_count,
    (SELECT COUNT(*) FROM cm_locale_backup_common_code_20260720_01) AS locale_backup_count,
    (SELECT COUNT(*) FROM cm_common_code_group) AS group_original_count,
    (SELECT COUNT(*) FROM cm_common_code_group_backup_reference_20260720_01) AS group_backup_count,
    (SELECT COUNT(*) FROM cm_common_code) AS code_original_count,
    (SELECT COUNT(*) FROM cm_common_code_backup_reference_20260720_01) AS code_backup_count;

/* 4. Canonical Common Code Groups */
START TRANSACTION;

INSERT INTO cm_common_code_group
(
    group_code,
    group_name,
    group_description,
    sort_no,
    status_code,
    reserved_yn,
    system_yn,
    created_dt,
    created_by,
    updated_dt,
    updated_by,
    client_ip,
    deleted_by,
    deleted_dt,
    program_id
)
VALUES
(
    'COUNTRY',
    'Country',
    'ISO 국가 코드, 표시 명칭 및 Native Name을 관리하는 Framework 공통 Reference Group.',
    310,
    'ACTIVE',
    'Y',
    'Y',
    NOW(),
    'SYSTEM',
    NOW(),
    'SYSTEM',
    @migration_client_ip,
    NULL,
    NULL,
    @migration_program_id
),
(
    'LANGUAGE',
    'Language',
    '지원 언어 코드, 표시 명칭 및 Native Name을 관리하는 Framework 공통 Reference Group.',
    320,
    'ACTIVE',
    'Y',
    'Y',
    NOW(),
    'SYSTEM',
    NOW(),
    'SYSTEM',
    @migration_client_ip,
    NULL,
    NULL,
    @migration_program_id
),
(
    'LOCALE',
    'Locale',
    '언어·국가 조합과 날짜·시간·숫자·Timezone 표시 형식을 관리하는 Framework 공통 Reference Group.',
    330,
    'ACTIVE',
    'Y',
    'Y',
    NOW(),
    'SYSTEM',
    NOW(),
    'SYSTEM',
    @migration_client_ip,
    NULL,
    NULL,
    @migration_program_id
)
ON DUPLICATE KEY UPDATE
    group_name        = VALUES(group_name),
    group_description = VALUES(group_description),
    sort_no           = VALUES(sort_no),
    status_code       = VALUES(status_code),
    reserved_yn       = VALUES(reserved_yn),
    system_yn         = VALUES(system_yn),
    updated_dt        = NOW(),
    updated_by        = VALUES(updated_by),
    client_ip         = VALUES(client_ip),
    deleted_by        = NULL,
    deleted_dt        = NULL,
    program_id        = VALUES(program_id);

/* 5. cm_country -> COUNTRY */
INSERT INTO cm_common_code
(
    group_code,
    code,
    code_name,
    common_code_description,
    sort_no,
    status_code,
    created_dt,
    created_by,
    updated_dt,
    updated_by,
    client_ip,
    deleted_by,
    deleted_dt,
    program_id,
    common_code_json
)
SELECT
    'COUNTRY',
    country_code,
    country_name,
    CONCAT('국가 Reference Code: ', country_name),
    sort_no,
    status_code,
    created_dt,
    created_by,
    updated_dt,
    updated_by,
    client_ip,
    deleted_by,
    deleted_dt,
    @migration_program_id,
    JSON_OBJECT(
        'source_object', 'cm_country',
        'native_name', native_name
    )
FROM cm_country
ON DUPLICATE KEY UPDATE
    code_name               = VALUES(code_name),
    common_code_description = VALUES(common_code_description),
    sort_no                 = VALUES(sort_no),
    status_code             = VALUES(status_code),
    updated_dt              = NOW(),
    updated_by              = VALUES(updated_by),
    client_ip               = VALUES(client_ip),
    deleted_by              = VALUES(deleted_by),
    deleted_dt              = VALUES(deleted_dt),
    program_id              = VALUES(program_id),
    common_code_json        = VALUES(common_code_json);

/* 6. cm_language -> LANGUAGE */
INSERT INTO cm_common_code
(
    group_code,
    code,
    code_name,
    common_code_description,
    sort_no,
    status_code,
    created_dt,
    created_by,
    updated_dt,
    updated_by,
    client_ip,
    deleted_by,
    deleted_dt,
    program_id,
    common_code_json
)
SELECT
    'LANGUAGE',
    language_code,
    language_name,
    CONCAT('언어 Reference Code: ', language_name),
    sort_no,
    status_code,
    created_dt,
    created_by,
    updated_dt,
    updated_by,
    client_ip,
    deleted_by,
    deleted_dt,
    @migration_program_id,
    JSON_OBJECT(
        'source_object', 'cm_language',
        'native_name', native_name
    )
FROM cm_language
ON DUPLICATE KEY UPDATE
    code_name               = VALUES(code_name),
    common_code_description = VALUES(common_code_description),
    sort_no                 = VALUES(sort_no),
    status_code             = VALUES(status_code),
    updated_dt              = NOW(),
    updated_by              = VALUES(updated_by),
    client_ip               = VALUES(client_ip),
    deleted_by              = VALUES(deleted_by),
    deleted_dt              = VALUES(deleted_dt),
    program_id              = VALUES(program_id),
    common_code_json        = VALUES(common_code_json);

/* 7. cm_locale -> LOCALE */
INSERT INTO cm_common_code
(
    group_code,
    code,
    code_name,
    common_code_description,
    sort_no,
    status_code,
    created_dt,
    created_by,
    updated_dt,
    updated_by,
    client_ip,
    deleted_by,
    deleted_dt,
    program_id,
    common_code_json
)
SELECT
    'LOCALE',
    locale_code,
    locale_name,
    CONCAT('Locale Reference Code: ', locale_name),
    sort_no,
    status_code,
    created_dt,
    created_by,
    updated_dt,
    updated_by,
    client_ip,
    deleted_by,
    deleted_dt,
    @migration_program_id,
    JSON_OBJECT(
        'source_object', 'cm_locale',
        'native_name', native_name,
        'language_group_code', 'LANGUAGE',
        'language_code', language_code,
        'country_group_code', 'COUNTRY',
        'country_code', country_code,
        'date_format', date_format,
        'time_format', time_format,
        'datetime_format', datetime_format,
        'number_format', number_format,
        'timezone_id', timezone_id
    )
FROM cm_locale
ON DUPLICATE KEY UPDATE
    code_name               = VALUES(code_name),
    common_code_description = VALUES(common_code_description),
    sort_no                 = VALUES(sort_no),
    status_code             = VALUES(status_code),
    updated_dt              = NOW(),
    updated_by              = VALUES(updated_by),
    client_ip               = VALUES(client_ip),
    deleted_by              = VALUES(deleted_by),
    deleted_dt              = VALUES(deleted_dt),
    program_id              = VALUES(program_id),
    common_code_json        = VALUES(common_code_json);

COMMIT;

/* 8. Migration verification guard */
SET @country_source_count = (SELECT COUNT(*) FROM cm_country);
SET @language_source_count = (SELECT COUNT(*) FROM cm_language);
SET @locale_source_count = (SELECT COUNT(*) FROM cm_locale);
SET @country_target_count = (SELECT COUNT(*) FROM cm_common_code WHERE group_code = 'COUNTRY');
SET @language_target_count = (SELECT COUNT(*) FROM cm_common_code WHERE group_code = 'LANGUAGE');
SET @locale_target_count = (SELECT COUNT(*) FROM cm_common_code WHERE group_code = 'LOCALE');
SET @invalid_json_count = (
    SELECT COUNT(*)
    FROM cm_common_code
    WHERE group_code IN ('COUNTRY', 'LANGUAGE', 'LOCALE')
      AND (common_code_json IS NULL OR JSON_VALID(common_code_json) = 0)
);
SET @migration_verified = (
    @country_source_count = @country_target_count
    AND @language_source_count = @language_target_count
    AND @locale_source_count = @locale_target_count
    AND @invalid_json_count = 0
);

SELECT
    @country_source_count AS country_source_count,
    @country_target_count AS country_target_count,
    @language_source_count AS language_source_count,
    @language_target_count AS language_target_count,
    @locale_source_count AS locale_source_count,
    @locale_target_count AS locale_target_count,
    @invalid_json_count AS invalid_json_count,
    @migration_verified AS migration_verified;

SET @guard_sql = IF(
    @migration_verified = 1,
    'SELECT ''MIGRATION_VERIFIED'' AS migration_status',
    'SELECT * FROM __SPS_COMMON_REFERENCE_MIGRATION_VALIDATION_FAILED__'
);
PREPARE migration_guard FROM @guard_sql;
EXECUTE migration_guard;
DEALLOCATE PREPARE migration_guard;

/* 9. Preserve migration evidence */
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
VALUES
(
    'CH_20260720_COUNTRY_COMMON_CODE_00001',
    DATABASE(),
    'cm_country',
    'COUNTRY',
    'DELETE',
    'cm_country 5건을 cm_common_code COUNTRY Group으로 무손실 이관하고 중복 Master Table을 제거한다.',
    'SYSTEM',
    NOW(),
    @migration_client_ip,
    @migration_program_id,
    'ACTIVE'
),
(
    'CH_20260720_LANGUAGE_COMMON_CODE_00001',
    DATABASE(),
    'cm_language',
    'LANGUAGE',
    'DELETE',
    'cm_language 4건을 cm_common_code LANGUAGE Group으로 무손실 이관하고 중복 Master Table을 제거한다.',
    'SYSTEM',
    NOW(),
    @migration_client_ip,
    @migration_program_id,
    'ACTIVE'
),
(
    'CH_20260720_LOCALE_COMMON_CODE_00001',
    DATABASE(),
    'cm_locale',
    'LOCALE',
    'DELETE',
    'cm_locale 5건과 Locale 형식·Timezone·상위 코드 관계를 cm_common_code LOCALE Group JSON으로 무손실 이관하고 중복 Master Table을 제거한다.',
    'SYSTEM',
    NOW(),
    @migration_client_ip,
    @migration_program_id,
    'ACTIVE'
);

/* 10. Remove internal FK and retired Master Tables */
ALTER TABLE cm_locale
    DROP FOREIGN KEY fk_cm_locale_country,
    DROP FOREIGN KEY fk_cm_locale_language;

DROP TABLE cm_locale;
DROP TABLE cm_language;
DROP TABLE cm_country;

/* 11. Final verification */
SELECT
    group_code,
    COUNT(*) AS code_count,
    SUM(common_code_json IS NULL OR JSON_VALID(common_code_json) = 0) AS invalid_json_count
FROM cm_common_code
WHERE group_code IN ('COUNTRY', 'LANGUAGE', 'LOCALE')
GROUP BY group_code
ORDER BY group_code;

SELECT
    table_name
FROM information_schema.tables
WHERE table_schema = DATABASE()
  AND table_name IN ('cm_country', 'cm_language', 'cm_locale')
ORDER BY table_name;

SELECT
    group_code,
    code,
    code_name,
    common_code_json
FROM cm_common_code
WHERE group_code IN ('COUNTRY', 'LANGUAGE', 'LOCALE')
ORDER BY group_code, sort_no, code;

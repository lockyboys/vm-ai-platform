/* ============================================================================
SPS Common Reference Code Consolidation Rollback
Restores cm_country, cm_language and cm_locale from migration backups.
The Verified analysis queries remain registered because they are independent.
============================================================================ */

USE te_common;

SET @rollback_program_id = 'SPS_COMMON_REFERENCE_CONSOLIDATION_ROLLBACK';
SET @rollback_client_ip = '127.0.0.1';

/* 1. Backup guard */
SET @country_backup_count = (
    SELECT COUNT(*) FROM cm_country_backup_common_code_20260720_01
);
SET @language_backup_count = (
    SELECT COUNT(*) FROM cm_language_backup_common_code_20260720_01
);
SET @locale_backup_count = (
    SELECT COUNT(*) FROM cm_locale_backup_common_code_20260720_01
);
SET @rollback_backup_verified = (
    @country_backup_count = 5
    AND @language_backup_count = 4
    AND @locale_backup_count = 5
);

SELECT
    @country_backup_count AS country_backup_count,
    @language_backup_count AS language_backup_count,
    @locale_backup_count AS locale_backup_count,
    @rollback_backup_verified AS rollback_backup_verified;

SET @rollback_guard_sql = IF(
    @rollback_backup_verified = 1,
    'SELECT ''ROLLBACK_BACKUP_VERIFIED'' AS rollback_status',
    'SELECT * FROM __SPS_COMMON_REFERENCE_ROLLBACK_BACKUP_FAILED__'
);
PREPARE rollback_guard FROM @rollback_guard_sql;
EXECUTE rollback_guard;
DEALLOCATE PREPARE rollback_guard;

/* 2. Restore retired Master Tables */
CREATE TABLE IF NOT EXISTS cm_country
LIKE cm_country_backup_common_code_20260720_01;

CREATE TABLE IF NOT EXISTS cm_language
LIKE cm_language_backup_common_code_20260720_01;

CREATE TABLE IF NOT EXISTS cm_locale
LIKE cm_locale_backup_common_code_20260720_01;

START TRANSACTION;

INSERT IGNORE INTO cm_country
SELECT * FROM cm_country_backup_common_code_20260720_01;

INSERT IGNORE INTO cm_language
SELECT * FROM cm_language_backup_common_code_20260720_01;

INSERT IGNORE INTO cm_locale
SELECT * FROM cm_locale_backup_common_code_20260720_01;

COMMIT;

/* 3. Restore physical Foreign Keys */
ALTER TABLE cm_locale
    ADD CONSTRAINT fk_cm_locale_country
        FOREIGN KEY (country_code)
        REFERENCES cm_country (country_code)
        ON UPDATE NO ACTION
        ON DELETE NO ACTION,
    ADD CONSTRAINT fk_cm_locale_language
        FOREIGN KEY (language_code)
        REFERENCES cm_language (language_code)
        ON UPDATE NO ACTION
        ON DELETE NO ACTION;

/* 4. Remove consolidated Common Code Groups */
START TRANSACTION;

DELETE FROM cm_common_code
WHERE group_code IN ('COUNTRY', 'LANGUAGE', 'LOCALE');

DELETE FROM cm_common_code_group
WHERE group_code IN ('COUNTRY', 'LANGUAGE', 'LOCALE');

COMMIT;

/* 5. Preserve rollback evidence */
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
    'CH_20260720_COMMON_REFERENCE_ROLLBACK_00001',
    DATABASE(),
    'cm_country,cm_language,cm_locale',
    'COMMON_REFERENCE_ROLLBACK',
    'UPDATE',
    'Common Code 통합을 Rollback하고 cm_country, cm_language, cm_locale 및 내부 FK를 Migration Backup에서 복원한다.',
    'SYSTEM',
    NOW(),
    @rollback_client_ip,
    @rollback_program_id,
    'ACTIVE'
);

/* 6. Final verification */
SELECT
    (SELECT COUNT(*) FROM cm_country) AS country_row_count,
    (SELECT COUNT(*) FROM cm_language) AS language_row_count,
    (SELECT COUNT(*) FROM cm_locale) AS locale_row_count,
    (SELECT COUNT(*) FROM information_schema.referential_constraints
      WHERE constraint_schema = DATABASE()
        AND constraint_name IN ('fk_cm_locale_country', 'fk_cm_locale_language')) AS restored_fk_count,
    (SELECT COUNT(*) FROM cm_common_code
      WHERE group_code IN ('COUNTRY', 'LANGUAGE', 'LOCALE')) AS remaining_common_code_count,
    (SELECT COUNT(*) FROM cm_common_code_group
      WHERE group_code IN ('COUNTRY', 'LANGUAGE', 'LOCALE')) AS remaining_group_count;

SHOW CREATE TABLE cm_country;
SHOW CREATE TABLE cm_language;
SHOW CREATE TABLE cm_locale;

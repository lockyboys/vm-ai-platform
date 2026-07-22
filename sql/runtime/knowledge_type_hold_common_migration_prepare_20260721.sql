/*
Purpose
  1. Register sp_knowledge_type_hold in the COMMON repository.
  2. Break the two legacy FK constraints safely.
  3. Preserve the legacy tables for final verification and later DROP approval.

Important
  - This batch does not DROP sp_knowledge_type_hold.
  - The common copy is created with the same physical columns and indexes.
  - FK removal is performed only after row-count and orphan prechecks.
*/

SET NAMES utf8mb4 COLLATE utf8mb4_unicode_ci;
SET @hold_identifier = 'MIGRATION:SP_KNOWLEDGE_TYPE_HOLD:COMMON';
SET @program_id = 'SP_KH_PROGRAM_20260721_000000_00001';

-- HOLD must be registered as PREPARED before migration starts.
SELECT COUNT(*) AS prepared_hold_count
FROM `te_story_platform`.`sp_knowledge_hold`
WHERE `knowledge_identifier` = @hold_identifier
  AND `source_story_text` LIKE '%|STATUS=PREPARED|%'
  AND `source_story_text` LIKE '%|DROP_ALLOWED_YN=N|%';

CREATE TEMPORARY TABLE `hold_ready_guard`
(
  `check_value` BIGINT NOT NULL,
  CONSTRAINT `chk_hold_ready_guard` CHECK (`check_value` = 1)
);

INSERT INTO `hold_ready_guard` (`check_value`)
SELECT COUNT(*)
FROM `te_story_platform`.`sp_knowledge_hold`
WHERE `knowledge_identifier` = @hold_identifier
  AND `source_story_text` LIKE '%|STATUS=PREPARED|%'
  AND `source_story_text` LIKE '%|DROP_ALLOWED_YN=N|%';

-- 0. Precheck: source rows and current orphan references.
SELECT COUNT(*) AS source_knowledge_type_count
FROM `te_story_platform`.`sp_knowledge_type_hold`;

SELECT COUNT(*) AS orphan_knowledge_type_reference_count
FROM `te_story_platform`.`sp_knowledge_hold` kh
LEFT JOIN `te_story_platform`.`sp_knowledge_type_hold` kt
  ON kt.`knowledge_type_id` = kh.`knowledge_type_id`
WHERE kt.`knowledge_type_id` IS NULL;

SELECT COUNT(*) AS orphan_parent_knowledge_type_count
FROM `te_story_platform`.`sp_knowledge_type_hold` child
LEFT JOIN `te_story_platform`.`sp_knowledge_type_hold` parent
  ON parent.`knowledge_type_id` = child.`parent_knowledge_type_id`
WHERE child.`parent_knowledge_type_id` IS NOT NULL
  AND parent.`knowledge_type_id` IS NULL;

-- Abort automatically if either legacy relationship already contains an orphan.
CREATE TEMPORARY TABLE `migration_zero_guard`
(
  `check_value` BIGINT NOT NULL,
  CONSTRAINT `chk_migration_zero_guard` CHECK (`check_value` = 0)
);

INSERT INTO `migration_zero_guard` (`check_value`)
SELECT COUNT(*)
FROM `te_story_platform`.`sp_knowledge_hold` kh
LEFT JOIN `te_story_platform`.`sp_knowledge_type_hold` kt
  ON kt.`knowledge_type_id` = kh.`knowledge_type_id`
WHERE kt.`knowledge_type_id` IS NULL;

INSERT INTO `migration_zero_guard` (`check_value`)
SELECT COUNT(*)
FROM `te_story_platform`.`sp_knowledge_type_hold` child
LEFT JOIN `te_story_platform`.`sp_knowledge_type_hold` parent
  ON parent.`knowledge_type_id` = child.`parent_knowledge_type_id`
WHERE child.`parent_knowledge_type_id` IS NOT NULL
  AND parent.`knowledge_type_id` IS NULL;

-- 1. Create the COMMON master with the current source structure.
CREATE TABLE IF NOT EXISTS `te_common`.`cm_knowledge_type_hold`
LIKE `te_story_platform`.`sp_knowledge_type_hold`;

ALTER TABLE `te_common`.`cm_knowledge_type_hold`
  COMMENT = 'Framework 공통 Knowledge Type Master. 기존 Story Platform Knowledge Type을 공통 저장소에서 보존하며 Generator, AI, Engine이 공식 분류 원천으로 사용한다.';

-- 2. Register all source data in COMMON.
-- REPLACE makes the registration repeatable while preserving source identifiers.
START TRANSACTION;

REPLACE INTO `te_common`.`cm_knowledge_type_hold`
SELECT *
FROM `te_story_platform`.`sp_knowledge_type_hold`;

COMMIT;

-- HOLD state: common registration completed, legacy FK still attached.
UPDATE `te_story_platform`.`sp_knowledge_hold`
SET
  `source_story_text` = CONCAT(
    'DECISION|SOURCE_TABLE=te_story_platform.sp_knowledge_type_hold',
    '|TARGET_TABLE=te_common.cm_knowledge_type_hold',
    '|STATUS=COMMON_REGISTERED',
    '|DROP_ALLOWED_YN=N',
    '|MIGRATION_REQUIRED_YN=Y',
    '|FK_DETACH_REQUIRED_YN=Y'
  ),
  `updated_dt` = CURRENT_TIMESTAMP,
  `updated_by` = 'SYSTEM',
  `program_id` = @program_id
WHERE `knowledge_identifier` = @hold_identifier;

-- 3. Registration verification. These two counts must match.
SELECT
  (SELECT COUNT(*)
     FROM `te_story_platform`.`sp_knowledge_type_hold`) AS source_count,
  (SELECT COUNT(*)
     FROM `te_common`.`cm_knowledge_type_hold`) AS common_count;

SELECT COUNT(*) AS source_missing_in_common_count
FROM `te_story_platform`.`sp_knowledge_type_hold` source
LEFT JOIN `te_common`.`cm_knowledge_type_hold` common
  ON common.`knowledge_type_id` = source.`knowledge_type_id`
WHERE common.`knowledge_type_id` IS NULL;

SELECT COUNT(*) AS knowledge_reference_missing_in_common_count
FROM `te_story_platform`.`sp_knowledge_hold` kh
LEFT JOIN `te_common`.`cm_knowledge_type_hold` common
  ON common.`knowledge_type_id` = kh.`knowledge_type_id`
WHERE common.`knowledge_type_id` IS NULL;

-- Abort before FK removal unless all source/reference identifiers exist in COMMON.
INSERT INTO `migration_zero_guard` (`check_value`)
SELECT COUNT(*)
FROM `te_story_platform`.`sp_knowledge_type_hold` source
LEFT JOIN `te_common`.`cm_knowledge_type_hold` common
  ON common.`knowledge_type_id` = source.`knowledge_type_id`
WHERE common.`knowledge_type_id` IS NULL;

INSERT INTO `migration_zero_guard` (`check_value`)
SELECT COUNT(*)
FROM `te_story_platform`.`sp_knowledge_hold` kh
LEFT JOIN `te_common`.`cm_knowledge_type_hold` common
  ON common.`knowledge_type_id` = kh.`knowledge_type_id`
WHERE common.`knowledge_type_id` IS NULL;

-- 4. Break the legacy FK relationships.
-- Confirm the constraint names in INFORMATION_SCHEMA before these statements.
SELECT
  `constraint_schema`,
  `table_name`,
  `constraint_name`,
  `constraint_type`
FROM `information_schema`.`table_constraints`
WHERE `constraint_schema` = 'te_story_platform'
  AND `constraint_name` IN
      ('fk_sp_knowledge_type', 'fk_sp_knowledge_type_parent')
ORDER BY `table_name`, `constraint_name`;

ALTER TABLE `te_story_platform`.`sp_knowledge_hold`
  DROP FOREIGN KEY `fk_sp_knowledge_type`;

ALTER TABLE `te_story_platform`.`sp_knowledge_type_hold`
  DROP FOREIGN KEY `fk_sp_knowledge_type_parent`;

-- HOLD state: common registration and legacy FK detachment completed.
-- DROP remains prohibited until a separate DROP_APPROVED decision is recorded.
UPDATE `te_story_platform`.`sp_knowledge_hold`
SET
  `source_story_text` = CONCAT(
    'DECISION|SOURCE_TABLE=te_story_platform.sp_knowledge_type_hold',
    '|TARGET_TABLE=te_common.cm_knowledge_type_hold',
    '|STATUS=FK_DETACHED',
    '|DROP_ALLOWED_YN=N',
    '|MIGRATION_REQUIRED_YN=N',
    '|FK_DETACH_REQUIRED_YN=N'
  ),
  `updated_dt` = CURRENT_TIMESTAMP,
  `updated_by` = 'SYSTEM',
  `program_id` = @program_id
WHERE `knowledge_identifier` = @hold_identifier;

-- 5. Final verification.
SELECT COUNT(*) AS remaining_legacy_fk_count
FROM `information_schema`.`table_constraints`
WHERE `constraint_schema` = 'te_story_platform'
  AND `constraint_name` IN
      ('fk_sp_knowledge_type', 'fk_sp_knowledge_type_parent')
  AND `constraint_type` = 'FOREIGN KEY';

SELECT
  `knowledge_type_id`,
  `knowledge_type_code`,
  `knowledge_type_name`,
  `parent_knowledge_type_id`,
  `knowledge_type_description`
FROM `te_common`.`cm_knowledge_type_hold`
ORDER BY `knowledge_type_id`;

SELECT
  `knowledge_identifier`,
  `source_story_text`,
  `updated_dt`,
  `program_id`
FROM `te_story_platform`.`sp_knowledge_hold`
WHERE `knowledge_identifier` = @hold_identifier;

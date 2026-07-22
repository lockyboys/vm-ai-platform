/* Rollback for knowledge_type_hold_common_migration_prepare_20260721.sql */

SET NAMES utf8mb4 COLLATE utf8mb4_unicode_ci;
SET @hold_identifier = 'MIGRATION:SP_KNOWLEDGE_TYPE_HOLD:COMMON';
SET @program_id = 'SP_KH_PROGRAM_20260721_000000_00001';

-- Precheck: every current reference must still resolve against the legacy master.
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

-- Restore the legacy FK relationships only when both precheck counts are zero.
ALTER TABLE `te_story_platform`.`sp_knowledge_hold`
  ADD CONSTRAINT `fk_sp_knowledge_type`
  FOREIGN KEY (`knowledge_type_id`)
  REFERENCES `te_story_platform`.`sp_knowledge_type_hold` (`knowledge_type_id`)
  ON UPDATE RESTRICT
  ON DELETE RESTRICT;

ALTER TABLE `te_story_platform`.`sp_knowledge_type_hold`
  ADD CONSTRAINT `fk_sp_knowledge_type_parent`
  FOREIGN KEY (`parent_knowledge_type_id`)
  REFERENCES `te_story_platform`.`sp_knowledge_type_hold` (`knowledge_type_id`)
  ON UPDATE RESTRICT
  ON DELETE RESTRICT;

UPDATE `te_story_platform`.`sp_knowledge_hold`
SET
  `source_story_text` = CONCAT(
    'DECISION|SOURCE_TABLE=te_story_platform.sp_knowledge_type_hold',
    '|TARGET_TABLE=te_common.cm_knowledge_type_hold',
    '|STATUS=FK_RESTORED',
    '|DROP_ALLOWED_YN=N',
    '|MIGRATION_REQUIRED_YN=Y',
    '|FK_DETACH_REQUIRED_YN=Y'
  ),
  `updated_dt` = CURRENT_TIMESTAMP,
  `updated_by` = 'SYSTEM',
  `program_id` = @program_id
WHERE `knowledge_identifier` = @hold_identifier;

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

SELECT
  `knowledge_identifier`,
  `source_story_text`,
  `updated_dt`
FROM `te_story_platform`.`sp_knowledge_hold`
WHERE `knowledge_identifier` = @hold_identifier;

-- cm_knowledge_type_hold is intentionally retained as migration evidence.

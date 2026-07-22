/*
Register the sp_knowledge_type_hold migration in the official Knowledge HOLD.
Initial state: PREPARED
*/

SET NAMES utf8mb4 COLLATE utf8mb4_unicode_ci;
SET @hold_knowledge_id = 'KH_SP_KNOWLEDGE_TYPE_HOLD_20260721_00001';
SET @hold_identifier = 'MIGRATION:SP_KNOWLEDGE_TYPE_HOLD:COMMON';
SET @program_id = 'SP_KH_PROGRAM_20260721_000000_00001';

START TRANSACTION;

INSERT INTO `te_story_platform`.`sp_knowledge_hold`
(
  `knowledge_id`,
  `knowledge_identifier`,
  `knowledge_type_id`,
  `knowledge_name`,
  `knowledge_description`,
  `source_story_text`,
  `active_yn`,
  `created_dt`,
  `created_by`,
  `updated_dt`,
  `updated_by`,
  `program_id`
)
SELECT
  @hold_knowledge_id,
  @hold_identifier,
  kt.`knowledge_type_id`,
  'sp_knowledge_type_hold 공통 이관',
  'Story Platform의 Knowledge Type Master를 공통 저장소로 이관하고 기존 FK를 해제하기 위한 공식 HOLD 기록.',
  CONCAT(
    'DECISION|SOURCE_TABLE=te_story_platform.sp_knowledge_type_hold',
    '|TARGET_TABLE=te_common.cm_knowledge_type_hold',
    '|STATUS=PREPARED',
    '|DROP_ALLOWED_YN=N',
    '|MIGRATION_REQUIRED_YN=Y',
    '|FK_DETACH_REQUIRED_YN=Y'
  ),
  'Y',
  CURRENT_TIMESTAMP,
  'SYSTEM',
  CURRENT_TIMESTAMP,
  'SYSTEM',
  @program_id
FROM `te_story_platform`.`sp_knowledge_type_hold` kt
WHERE kt.`knowledge_type_code` = 'OBJECT'
ON DUPLICATE KEY UPDATE
  `knowledge_name` = VALUES(`knowledge_name`),
  `knowledge_description` = VALUES(`knowledge_description`),
  `source_story_text` = VALUES(`source_story_text`),
  `active_yn` = 'Y',
  `updated_dt` = CURRENT_TIMESTAMP,
  `updated_by` = 'SYSTEM',
  `program_id` = VALUES(`program_id`);

COMMIT;

SELECT
  `knowledge_id`,
  `knowledge_identifier`,
  `knowledge_name`,
  `source_story_text`,
  `active_yn`,
  `updated_dt`,
  `program_id`
FROM `te_story_platform`.`sp_knowledge_hold`
WHERE `knowledge_identifier` = @hold_identifier;

SELECT COUNT(*) AS prepared_hold_count
FROM `te_story_platform`.`sp_knowledge_hold`
WHERE `knowledge_identifier` = @hold_identifier
  AND `source_story_text` LIKE '%|STATUS=PREPARED|%'
  AND `source_story_text` LIKE '%|DROP_ALLOWED_YN=N|%';

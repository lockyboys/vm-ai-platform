/* Official Domain Code correction: CM_CM->CM_CO, SP_ID->SP_RP */

SET @OLD_FOREIGN_KEY_CHECKS = @@FOREIGN_KEY_CHECKS;

SET FOREIGN_KEY_CHECKS = 0;

CREATE TABLE IF NOT EXISTS `te_common`.`cm_audit_policy_bkp_domain_20260721` LIKE `te_common`.`cm_audit_policy`;

INSERT INTO `te_common`.`cm_audit_policy_bkp_domain_20260721` SELECT * FROM `te_common`.`cm_audit_policy` WHERE NOT EXISTS (SELECT 1 FROM `te_common`.`cm_audit_policy_bkp_domain_20260721` LIMIT 1);

CREATE TABLE IF NOT EXISTS `te_common`.`cm_business_domain_bkp_domain_20260721` LIKE `te_common`.`cm_business_domain`;

INSERT INTO `te_common`.`cm_business_domain_bkp_domain_20260721` SELECT * FROM `te_common`.`cm_business_domain` WHERE NOT EXISTS (SELECT 1 FROM `te_common`.`cm_business_domain_bkp_domain_20260721` LIMIT 1);

CREATE TABLE IF NOT EXISTS `te_common`.`cm_change_history_bkp_domain_20260721` LIKE `te_common`.`cm_change_history`;

INSERT INTO `te_common`.`cm_change_history_bkp_domain_20260721` SELECT * FROM `te_common`.`cm_change_history` WHERE NOT EXISTS (SELECT 1 FROM `te_common`.`cm_change_history_bkp_domain_20260721` LIMIT 1);

CREATE TABLE IF NOT EXISTS `te_common`.`cm_common_code_bkp_domain_20260721` LIKE `te_common`.`cm_common_code`;

INSERT INTO `te_common`.`cm_common_code_bkp_domain_20260721` SELECT * FROM `te_common`.`cm_common_code` WHERE NOT EXISTS (SELECT 1 FROM `te_common`.`cm_common_code_bkp_domain_20260721` LIMIT 1);

CREATE TABLE IF NOT EXISTS `te_common`.`cm_common_code_group_bkp_domain_20260721` LIKE `te_common`.`cm_common_code_group`;

INSERT INTO `te_common`.`cm_common_code_group_bkp_domain_20260721` SELECT * FROM `te_common`.`cm_common_code_group` WHERE NOT EXISTS (SELECT 1 FROM `te_common`.`cm_common_code_group_bkp_domain_20260721` LIMIT 1);

CREATE TABLE IF NOT EXISTS `te_common`.`cm_legal_retention_policy_bkp_domain_20260721` LIKE `te_common`.`cm_legal_retention_policy`;

INSERT INTO `te_common`.`cm_legal_retention_policy_bkp_domain_20260721` SELECT * FROM `te_common`.`cm_legal_retention_policy` WHERE NOT EXISTS (SELECT 1 FROM `te_common`.`cm_legal_retention_policy_bkp_domain_20260721` LIMIT 1);

CREATE TABLE IF NOT EXISTS `te_common`.`cm_member_bkp_domain_20260721` LIKE `te_common`.`cm_member`;

INSERT INTO `te_common`.`cm_member_bkp_domain_20260721` SELECT * FROM `te_common`.`cm_member` WHERE NOT EXISTS (SELECT 1 FROM `te_common`.`cm_member_bkp_domain_20260721` LIMIT 1);

CREATE TABLE IF NOT EXISTS `te_common`.`cm_member_role_bkp_domain_20260721` LIKE `te_common`.`cm_member_role`;

INSERT INTO `te_common`.`cm_member_role_bkp_domain_20260721` SELECT * FROM `te_common`.`cm_member_role` WHERE NOT EXISTS (SELECT 1 FROM `te_common`.`cm_member_role_bkp_domain_20260721` LIMIT 1);

CREATE TABLE IF NOT EXISTS `te_common`.`cm_repository_bkp_domain_20260721` LIKE `te_common`.`cm_repository`;

INSERT INTO `te_common`.`cm_repository_bkp_domain_20260721` SELECT * FROM `te_common`.`cm_repository` WHERE NOT EXISTS (SELECT 1 FROM `te_common`.`cm_repository_bkp_domain_20260721` LIMIT 1);

CREATE TABLE IF NOT EXISTS `te_common`.`cm_role_bkp_domain_20260721` LIKE `te_common`.`cm_role`;

INSERT INTO `te_common`.`cm_role_bkp_domain_20260721` SELECT * FROM `te_common`.`cm_role` WHERE NOT EXISTS (SELECT 1 FROM `te_common`.`cm_role_bkp_domain_20260721` LIMIT 1);

CREATE TABLE IF NOT EXISTS `te_common`.`cm_sequence_format_bkp_domain_20260721` LIKE `te_common`.`cm_sequence_format`;

INSERT INTO `te_common`.`cm_sequence_format_bkp_domain_20260721` SELECT * FROM `te_common`.`cm_sequence_format` WHERE NOT EXISTS (SELECT 1 FROM `te_common`.`cm_sequence_format_bkp_domain_20260721` LIMIT 1);

CREATE TABLE IF NOT EXISTS `te_common`.`cm_sequence_policy_bkp_domain_20260721` LIKE `te_common`.`cm_sequence_policy`;

INSERT INTO `te_common`.`cm_sequence_policy_bkp_domain_20260721` SELECT * FROM `te_common`.`cm_sequence_policy` WHERE NOT EXISTS (SELECT 1 FROM `te_common`.`cm_sequence_policy_bkp_domain_20260721` LIMIT 1);

CREATE TABLE IF NOT EXISTS `te_common`.`cm_sequence_rule_bkp_domain_20260721` LIKE `te_common`.`cm_sequence_rule`;

INSERT INTO `te_common`.`cm_sequence_rule_bkp_domain_20260721` SELECT * FROM `te_common`.`cm_sequence_rule` WHERE NOT EXISTS (SELECT 1 FROM `te_common`.`cm_sequence_rule_bkp_domain_20260721` LIMIT 1);

CREATE TABLE IF NOT EXISTS `te_common`.`cm_storage_policy_bkp_domain_20260721` LIKE `te_common`.`cm_storage_policy`;

INSERT INTO `te_common`.`cm_storage_policy_bkp_domain_20260721` SELECT * FROM `te_common`.`cm_storage_policy` WHERE NOT EXISTS (SELECT 1 FROM `te_common`.`cm_storage_policy_bkp_domain_20260721` LIMIT 1);

CREATE TABLE IF NOT EXISTS `te_common`.`cm_storage_repository_bkp_domain_20260721` LIKE `te_common`.`cm_storage_repository`;

INSERT INTO `te_common`.`cm_storage_repository_bkp_domain_20260721` SELECT * FROM `te_common`.`cm_storage_repository` WHERE NOT EXISTS (SELECT 1 FROM `te_common`.`cm_storage_repository_bkp_domain_20260721` LIMIT 1);

CREATE TABLE IF NOT EXISTS `te_common`.`cm_verified_sql_query_bkp_domain_20260721` LIKE `te_common`.`cm_verified_sql_query`;

INSERT INTO `te_common`.`cm_verified_sql_query_bkp_domain_20260721` SELECT * FROM `te_common`.`cm_verified_sql_query` WHERE NOT EXISTS (SELECT 1 FROM `te_common`.`cm_verified_sql_query_bkp_domain_20260721` LIMIT 1);

CREATE TABLE IF NOT EXISTS `te_common`.`rl_rule_bkp_domain_20260721` LIKE `te_common`.`rl_rule`;

INSERT INTO `te_common`.`rl_rule_bkp_domain_20260721` SELECT * FROM `te_common`.`rl_rule` WHERE NOT EXISTS (SELECT 1 FROM `te_common`.`rl_rule_bkp_domain_20260721` LIMIT 1);

CREATE TABLE IF NOT EXISTS `te_common`.`rl_rule_action_bkp_domain_20260721` LIKE `te_common`.`rl_rule_action`;

INSERT INTO `te_common`.`rl_rule_action_bkp_domain_20260721` SELECT * FROM `te_common`.`rl_rule_action` WHERE NOT EXISTS (SELECT 1 FROM `te_common`.`rl_rule_action_bkp_domain_20260721` LIMIT 1);

CREATE TABLE IF NOT EXISTS `te_common`.`rl_rule_condition_bkp_domain_20260721` LIKE `te_common`.`rl_rule_condition`;

INSERT INTO `te_common`.`rl_rule_condition_bkp_domain_20260721` SELECT * FROM `te_common`.`rl_rule_condition` WHERE NOT EXISTS (SELECT 1 FROM `te_common`.`rl_rule_condition_bkp_domain_20260721` LIMIT 1);

CREATE TABLE IF NOT EXISTS `te_common`.`rl_rule_evidence_bkp_domain_20260721` LIKE `te_common`.`rl_rule_evidence`;

INSERT INTO `te_common`.`rl_rule_evidence_bkp_domain_20260721` SELECT * FROM `te_common`.`rl_rule_evidence` WHERE NOT EXISTS (SELECT 1 FROM `te_common`.`rl_rule_evidence_bkp_domain_20260721` LIMIT 1);

CREATE TABLE IF NOT EXISTS `te_common`.`sp_policy_rule_candidate_bkp_domain_20260721` LIKE `te_common`.`sp_policy_rule_candidate`;

INSERT INTO `te_common`.`sp_policy_rule_candidate_bkp_domain_20260721` SELECT * FROM `te_common`.`sp_policy_rule_candidate` WHERE NOT EXISTS (SELECT 1 FROM `te_common`.`sp_policy_rule_candidate_bkp_domain_20260721` LIMIT 1);

CREATE TABLE IF NOT EXISTS `te_common`.`system_menu_button_bkp_domain_20260721` LIKE `te_common`.`system_menu_button`;

INSERT INTO `te_common`.`system_menu_button_bkp_domain_20260721` SELECT * FROM `te_common`.`system_menu_button` WHERE NOT EXISTS (SELECT 1 FROM `te_common`.`system_menu_button_bkp_domain_20260721` LIMIT 1);

CREATE TABLE IF NOT EXISTS `te_common`.`system_menu_button_crud_permission_bkp_domain_20260721` LIKE `te_common`.`system_menu_button_crud_permission`;

INSERT INTO `te_common`.`system_menu_button_crud_permission_bkp_domain_20260721` SELECT * FROM `te_common`.`system_menu_button_crud_permission` WHERE NOT EXISTS (SELECT 1 FROM `te_common`.`system_menu_button_crud_permission_bkp_domain_20260721` LIMIT 1);

CREATE TABLE IF NOT EXISTS `te_common`.`system_user_bkp_domain_20260721` LIKE `te_common`.`system_user`;

INSERT INTO `te_common`.`system_user_bkp_domain_20260721` SELECT * FROM `te_common`.`system_user` WHERE NOT EXISTS (SELECT 1 FROM `te_common`.`system_user_bkp_domain_20260721` LIMIT 1);

CREATE TABLE IF NOT EXISTS `te_health_companion`.`ac_action_bkp_domain_20260721` LIKE `te_health_companion`.`ac_action`;

INSERT INTO `te_health_companion`.`ac_action_bkp_domain_20260721` SELECT * FROM `te_health_companion`.`ac_action` WHERE NOT EXISTS (SELECT 1 FROM `te_health_companion`.`ac_action_bkp_domain_20260721` LIMIT 1);

CREATE TABLE IF NOT EXISTS `te_health_companion`.`at_audit_bkp_domain_20260721` LIKE `te_health_companion`.`at_audit`;

INSERT INTO `te_health_companion`.`at_audit_bkp_domain_20260721` SELECT * FROM `te_health_companion`.`at_audit` WHERE NOT EXISTS (SELECT 1 FROM `te_health_companion`.`at_audit_bkp_domain_20260721` LIMIT 1);

CREATE TABLE IF NOT EXISTS `te_health_companion`.`dc_decision_bkp_domain_20260721` LIKE `te_health_companion`.`dc_decision`;

INSERT INTO `te_health_companion`.`dc_decision_bkp_domain_20260721` SELECT * FROM `te_health_companion`.`dc_decision` WHERE NOT EXISTS (SELECT 1 FROM `te_health_companion`.`dc_decision_bkp_domain_20260721` LIMIT 1);

CREATE TABLE IF NOT EXISTS `te_health_companion`.`dc_decision_detail_bkp_domain_20260721` LIKE `te_health_companion`.`dc_decision_detail`;

INSERT INTO `te_health_companion`.`dc_decision_detail_bkp_domain_20260721` SELECT * FROM `te_health_companion`.`dc_decision_detail` WHERE NOT EXISTS (SELECT 1 FROM `te_health_companion`.`dc_decision_detail_bkp_domain_20260721` LIMIT 1);

CREATE TABLE IF NOT EXISTS `te_health_companion`.`fb_feedback_bkp_domain_20260721` LIKE `te_health_companion`.`fb_feedback`;

INSERT INTO `te_health_companion`.`fb_feedback_bkp_domain_20260721` SELECT * FROM `te_health_companion`.`fb_feedback` WHERE NOT EXISTS (SELECT 1 FROM `te_health_companion`.`fb_feedback_bkp_domain_20260721` LIMIT 1);

CREATE TABLE IF NOT EXISTS `te_story_platform`.`sp_identifier_blueprint_bkp_domain_20260721` LIKE `te_story_platform`.`sp_identifier_blueprint`;

INSERT INTO `te_story_platform`.`sp_identifier_blueprint_bkp_domain_20260721` SELECT * FROM `te_story_platform`.`sp_identifier_blueprint` WHERE NOT EXISTS (SELECT 1 FROM `te_story_platform`.`sp_identifier_blueprint_bkp_domain_20260721` LIMIT 1);

CREATE TABLE IF NOT EXISTS `te_story_platform`.`sp_identifier_sequence_bkp_domain_20260721` LIKE `te_story_platform`.`sp_identifier_sequence`;

INSERT INTO `te_story_platform`.`sp_identifier_sequence_bkp_domain_20260721` SELECT * FROM `te_story_platform`.`sp_identifier_sequence` WHERE NOT EXISTS (SELECT 1 FROM `te_story_platform`.`sp_identifier_sequence_bkp_domain_20260721` LIMIT 1);

CREATE TABLE IF NOT EXISTS `te_story_platform`.`sp_impact_analysis_result_bkp_domain_20260721` LIKE `te_story_platform`.`sp_impact_analysis_result`;

INSERT INTO `te_story_platform`.`sp_impact_analysis_result_bkp_domain_20260721` SELECT * FROM `te_story_platform`.`sp_impact_analysis_result` WHERE NOT EXISTS (SELECT 1 FROM `te_story_platform`.`sp_impact_analysis_result_bkp_domain_20260721` LIMIT 1);

CREATE TABLE IF NOT EXISTS `te_story_platform`.`sp_knowledge_hold_bkp_domain_20260721` LIKE `te_story_platform`.`sp_knowledge_hold`;

INSERT INTO `te_story_platform`.`sp_knowledge_hold_bkp_domain_20260721` SELECT * FROM `te_story_platform`.`sp_knowledge_hold` WHERE NOT EXISTS (SELECT 1 FROM `te_story_platform`.`sp_knowledge_hold_bkp_domain_20260721` LIMIT 1);

CREATE TABLE IF NOT EXISTS `te_story_platform`.`sp_knowledge_relationship_hold_bkp_domain_20260721` LIKE `te_story_platform`.`sp_knowledge_relationship_hold`;

INSERT INTO `te_story_platform`.`sp_knowledge_relationship_hold_bkp_domain_20260721` SELECT * FROM `te_story_platform`.`sp_knowledge_relationship_hold` WHERE NOT EXISTS (SELECT 1 FROM `te_story_platform`.`sp_knowledge_relationship_hold_bkp_domain_20260721` LIMIT 1);

CREATE TABLE IF NOT EXISTS `te_story_platform`.`sp_metadata_bkp_domain_20260721` LIKE `te_story_platform`.`sp_metadata`;

INSERT INTO `te_story_platform`.`sp_metadata_bkp_domain_20260721` SELECT * FROM `te_story_platform`.`sp_metadata` WHERE NOT EXISTS (SELECT 1 FROM `te_story_platform`.`sp_metadata_bkp_domain_20260721` LIMIT 1);

CREATE TABLE IF NOT EXISTS `te_story_platform`.`sp_object_bkp_domain_20260721` LIKE `te_story_platform`.`sp_object`;

INSERT INTO `te_story_platform`.`sp_object_bkp_domain_20260721` SELECT * FROM `te_story_platform`.`sp_object` WHERE NOT EXISTS (SELECT 1 FROM `te_story_platform`.`sp_object_bkp_domain_20260721` LIMIT 1);

CREATE TABLE IF NOT EXISTS `te_story_platform`.`sp_object_lifecycle_bkp_domain_20260721` LIKE `te_story_platform`.`sp_object_lifecycle`;

INSERT INTO `te_story_platform`.`sp_object_lifecycle_bkp_domain_20260721` SELECT * FROM `te_story_platform`.`sp_object_lifecycle` WHERE NOT EXISTS (SELECT 1 FROM `te_story_platform`.`sp_object_lifecycle_bkp_domain_20260721` LIMIT 1);

CREATE TABLE IF NOT EXISTS `te_story_platform`.`sp_relationship_bkp_domain_20260721` LIKE `te_story_platform`.`sp_relationship`;

INSERT INTO `te_story_platform`.`sp_relationship_bkp_domain_20260721` SELECT * FROM `te_story_platform`.`sp_relationship` WHERE NOT EXISTS (SELECT 1 FROM `te_story_platform`.`sp_relationship_bkp_domain_20260721` LIMIT 1);

UPDATE `te_common`.`cm_audit_policy`
SET `audit_policy_id` = CASE
    WHEN `audit_policy_id` LIKE 'CM\_CM\_%%' THEN CONCAT('CM_CO_', SUBSTRING(`audit_policy_id`, 7))
    WHEN `audit_policy_id` LIKE 'CM\_SY\_%%' THEN CONCAT('CM_CO_', SUBSTRING(`audit_policy_id`, 7))
    WHEN `audit_policy_id` LIKE 'SP\_ID\_%%' THEN CONCAT('SP_RP_', SUBSTRING(`audit_policy_id`, 7))
    ELSE `audit_policy_id`
END
WHERE `audit_policy_id` LIKE 'CM\_CM\_%%'
   OR `audit_policy_id` LIKE 'CM\_SY\_%%'
   OR `audit_policy_id` LIKE 'SP\_ID\_%%';

UPDATE `te_common`.`cm_business_domain`
SET `business_domain_id` = CASE
    WHEN `business_domain_id` LIKE 'CM\_CM\_%%' THEN CONCAT('CM_CO_', SUBSTRING(`business_domain_id`, 7))
    WHEN `business_domain_id` LIKE 'CM\_SY\_%%' THEN CONCAT('CM_CO_', SUBSTRING(`business_domain_id`, 7))
    WHEN `business_domain_id` LIKE 'SP\_ID\_%%' THEN CONCAT('SP_RP_', SUBSTRING(`business_domain_id`, 7))
    ELSE `business_domain_id`
END
WHERE `business_domain_id` LIKE 'CM\_CM\_%%'
   OR `business_domain_id` LIKE 'CM\_SY\_%%'
   OR `business_domain_id` LIKE 'SP\_ID\_%%';

UPDATE `te_common`.`cm_change_history`
SET `change_history_id` = CASE
    WHEN `change_history_id` LIKE 'CM\_CM\_%%' THEN CONCAT('CM_CO_', SUBSTRING(`change_history_id`, 7))
    WHEN `change_history_id` LIKE 'CM\_SY\_%%' THEN CONCAT('CM_CO_', SUBSTRING(`change_history_id`, 7))
    WHEN `change_history_id` LIKE 'SP\_ID\_%%' THEN CONCAT('SP_RP_', SUBSTRING(`change_history_id`, 7))
    ELSE `change_history_id`
END
WHERE `change_history_id` LIKE 'CM\_CM\_%%'
   OR `change_history_id` LIKE 'CM\_SY\_%%'
   OR `change_history_id` LIKE 'SP\_ID\_%%';

UPDATE `te_common`.`cm_change_history`
SET `target_record_id` = CASE
    WHEN `target_record_id` LIKE 'CM\_CM\_%%' THEN CONCAT('CM_CO_', SUBSTRING(`target_record_id`, 7))
    WHEN `target_record_id` LIKE 'CM\_SY\_%%' THEN CONCAT('CM_CO_', SUBSTRING(`target_record_id`, 7))
    WHEN `target_record_id` LIKE 'SP\_ID\_%%' THEN CONCAT('SP_RP_', SUBSTRING(`target_record_id`, 7))
    ELSE `target_record_id`
END
WHERE `target_record_id` LIKE 'CM\_CM\_%%'
   OR `target_record_id` LIKE 'CM\_SY\_%%'
   OR `target_record_id` LIKE 'SP\_ID\_%%';

UPDATE `te_common`.`cm_change_history`
SET `program_id` = CASE
    WHEN `program_id` LIKE 'CM\_CM\_%%' THEN CONCAT('CM_CO_', SUBSTRING(`program_id`, 7))
    WHEN `program_id` LIKE 'CM\_SY\_%%' THEN CONCAT('CM_CO_', SUBSTRING(`program_id`, 7))
    WHEN `program_id` LIKE 'SP\_ID\_%%' THEN CONCAT('SP_RP_', SUBSTRING(`program_id`, 7))
    ELSE `program_id`
END
WHERE `program_id` LIKE 'CM\_CM\_%%'
   OR `program_id` LIKE 'CM\_SY\_%%'
   OR `program_id` LIKE 'SP\_ID\_%%';

UPDATE `te_common`.`cm_common_code`
SET `program_id` = CASE
    WHEN `program_id` LIKE 'CM\_CM\_%%' THEN CONCAT('CM_CO_', SUBSTRING(`program_id`, 7))
    WHEN `program_id` LIKE 'CM\_SY\_%%' THEN CONCAT('CM_CO_', SUBSTRING(`program_id`, 7))
    WHEN `program_id` LIKE 'SP\_ID\_%%' THEN CONCAT('SP_RP_', SUBSTRING(`program_id`, 7))
    ELSE `program_id`
END
WHERE `program_id` LIKE 'CM\_CM\_%%'
   OR `program_id` LIKE 'CM\_SY\_%%'
   OR `program_id` LIKE 'SP\_ID\_%%';

UPDATE `te_common`.`cm_common_code_group`
SET `program_id` = CASE
    WHEN `program_id` LIKE 'CM\_CM\_%%' THEN CONCAT('CM_CO_', SUBSTRING(`program_id`, 7))
    WHEN `program_id` LIKE 'CM\_SY\_%%' THEN CONCAT('CM_CO_', SUBSTRING(`program_id`, 7))
    WHEN `program_id` LIKE 'SP\_ID\_%%' THEN CONCAT('SP_RP_', SUBSTRING(`program_id`, 7))
    ELSE `program_id`
END
WHERE `program_id` LIKE 'CM\_CM\_%%'
   OR `program_id` LIKE 'CM\_SY\_%%'
   OR `program_id` LIKE 'SP\_ID\_%%';

UPDATE `te_common`.`cm_legal_retention_policy`
SET `legal_retention_policy_id` = CASE
    WHEN `legal_retention_policy_id` LIKE 'CM\_CM\_%%' THEN CONCAT('CM_CO_', SUBSTRING(`legal_retention_policy_id`, 7))
    WHEN `legal_retention_policy_id` LIKE 'CM\_SY\_%%' THEN CONCAT('CM_CO_', SUBSTRING(`legal_retention_policy_id`, 7))
    WHEN `legal_retention_policy_id` LIKE 'SP\_ID\_%%' THEN CONCAT('SP_RP_', SUBSTRING(`legal_retention_policy_id`, 7))
    ELSE `legal_retention_policy_id`
END
WHERE `legal_retention_policy_id` LIKE 'CM\_CM\_%%'
   OR `legal_retention_policy_id` LIKE 'CM\_SY\_%%'
   OR `legal_retention_policy_id` LIKE 'SP\_ID\_%%';

UPDATE `te_common`.`cm_member`
SET `member_id` = CASE
    WHEN `member_id` LIKE 'CM\_CM\_%%' THEN CONCAT('CM_CO_', SUBSTRING(`member_id`, 7))
    WHEN `member_id` LIKE 'CM\_SY\_%%' THEN CONCAT('CM_CO_', SUBSTRING(`member_id`, 7))
    WHEN `member_id` LIKE 'SP\_ID\_%%' THEN CONCAT('SP_RP_', SUBSTRING(`member_id`, 7))
    ELSE `member_id`
END
WHERE `member_id` LIKE 'CM\_CM\_%%'
   OR `member_id` LIKE 'CM\_SY\_%%'
   OR `member_id` LIKE 'SP\_ID\_%%';

UPDATE `te_common`.`cm_member_role`
SET `member_role_id` = CASE
    WHEN `member_role_id` LIKE 'CM\_CM\_%%' THEN CONCAT('CM_CO_', SUBSTRING(`member_role_id`, 7))
    WHEN `member_role_id` LIKE 'CM\_SY\_%%' THEN CONCAT('CM_CO_', SUBSTRING(`member_role_id`, 7))
    WHEN `member_role_id` LIKE 'SP\_ID\_%%' THEN CONCAT('SP_RP_', SUBSTRING(`member_role_id`, 7))
    ELSE `member_role_id`
END
WHERE `member_role_id` LIKE 'CM\_CM\_%%'
   OR `member_role_id` LIKE 'CM\_SY\_%%'
   OR `member_role_id` LIKE 'SP\_ID\_%%';

UPDATE `te_common`.`cm_member_role`
SET `member_id` = CASE
    WHEN `member_id` LIKE 'CM\_CM\_%%' THEN CONCAT('CM_CO_', SUBSTRING(`member_id`, 7))
    WHEN `member_id` LIKE 'CM\_SY\_%%' THEN CONCAT('CM_CO_', SUBSTRING(`member_id`, 7))
    WHEN `member_id` LIKE 'SP\_ID\_%%' THEN CONCAT('SP_RP_', SUBSTRING(`member_id`, 7))
    ELSE `member_id`
END
WHERE `member_id` LIKE 'CM\_CM\_%%'
   OR `member_id` LIKE 'CM\_SY\_%%'
   OR `member_id` LIKE 'SP\_ID\_%%';

UPDATE `te_common`.`cm_member_role`
SET `role_id` = CASE
    WHEN `role_id` LIKE 'CM\_CM\_%%' THEN CONCAT('CM_CO_', SUBSTRING(`role_id`, 7))
    WHEN `role_id` LIKE 'CM\_SY\_%%' THEN CONCAT('CM_CO_', SUBSTRING(`role_id`, 7))
    WHEN `role_id` LIKE 'SP\_ID\_%%' THEN CONCAT('SP_RP_', SUBSTRING(`role_id`, 7))
    ELSE `role_id`
END
WHERE `role_id` LIKE 'CM\_CM\_%%'
   OR `role_id` LIKE 'CM\_SY\_%%'
   OR `role_id` LIKE 'SP\_ID\_%%';

UPDATE `te_common`.`cm_member_role`
SET `program_id` = CASE
    WHEN `program_id` LIKE 'CM\_CM\_%%' THEN CONCAT('CM_CO_', SUBSTRING(`program_id`, 7))
    WHEN `program_id` LIKE 'CM\_SY\_%%' THEN CONCAT('CM_CO_', SUBSTRING(`program_id`, 7))
    WHEN `program_id` LIKE 'SP\_ID\_%%' THEN CONCAT('SP_RP_', SUBSTRING(`program_id`, 7))
    ELSE `program_id`
END
WHERE `program_id` LIKE 'CM\_CM\_%%'
   OR `program_id` LIKE 'CM\_SY\_%%'
   OR `program_id` LIKE 'SP\_ID\_%%';

UPDATE `te_common`.`cm_repository`
SET `repository_id` = CASE
    WHEN `repository_id` LIKE 'CM\_CM\_%%' THEN CONCAT('CM_CO_', SUBSTRING(`repository_id`, 7))
    WHEN `repository_id` LIKE 'CM\_SY\_%%' THEN CONCAT('CM_CO_', SUBSTRING(`repository_id`, 7))
    WHEN `repository_id` LIKE 'SP\_ID\_%%' THEN CONCAT('SP_RP_', SUBSTRING(`repository_id`, 7))
    ELSE `repository_id`
END
WHERE `repository_id` LIKE 'CM\_CM\_%%'
   OR `repository_id` LIKE 'CM\_SY\_%%'
   OR `repository_id` LIKE 'SP\_ID\_%%';

UPDATE `te_common`.`cm_repository`
SET `program_id` = CASE
    WHEN `program_id` LIKE 'CM\_CM\_%%' THEN CONCAT('CM_CO_', SUBSTRING(`program_id`, 7))
    WHEN `program_id` LIKE 'CM\_SY\_%%' THEN CONCAT('CM_CO_', SUBSTRING(`program_id`, 7))
    WHEN `program_id` LIKE 'SP\_ID\_%%' THEN CONCAT('SP_RP_', SUBSTRING(`program_id`, 7))
    ELSE `program_id`
END
WHERE `program_id` LIKE 'CM\_CM\_%%'
   OR `program_id` LIKE 'CM\_SY\_%%'
   OR `program_id` LIKE 'SP\_ID\_%%';

UPDATE `te_common`.`cm_role`
SET `role_id` = CASE
    WHEN `role_id` LIKE 'CM\_CM\_%%' THEN CONCAT('CM_CO_', SUBSTRING(`role_id`, 7))
    WHEN `role_id` LIKE 'CM\_SY\_%%' THEN CONCAT('CM_CO_', SUBSTRING(`role_id`, 7))
    WHEN `role_id` LIKE 'SP\_ID\_%%' THEN CONCAT('SP_RP_', SUBSTRING(`role_id`, 7))
    ELSE `role_id`
END
WHERE `role_id` LIKE 'CM\_CM\_%%'
   OR `role_id` LIKE 'CM\_SY\_%%'
   OR `role_id` LIKE 'SP\_ID\_%%';

UPDATE `te_common`.`cm_role`
SET `program_id` = CASE
    WHEN `program_id` LIKE 'CM\_CM\_%%' THEN CONCAT('CM_CO_', SUBSTRING(`program_id`, 7))
    WHEN `program_id` LIKE 'CM\_SY\_%%' THEN CONCAT('CM_CO_', SUBSTRING(`program_id`, 7))
    WHEN `program_id` LIKE 'SP\_ID\_%%' THEN CONCAT('SP_RP_', SUBSTRING(`program_id`, 7))
    ELSE `program_id`
END
WHERE `program_id` LIKE 'CM\_CM\_%%'
   OR `program_id` LIKE 'CM\_SY\_%%'
   OR `program_id` LIKE 'SP\_ID\_%%';

UPDATE `te_common`.`cm_sequence_format`
SET `program_id` = CASE
    WHEN `program_id` LIKE 'CM\_CM\_%%' THEN CONCAT('CM_CO_', SUBSTRING(`program_id`, 7))
    WHEN `program_id` LIKE 'CM\_SY\_%%' THEN CONCAT('CM_CO_', SUBSTRING(`program_id`, 7))
    WHEN `program_id` LIKE 'SP\_ID\_%%' THEN CONCAT('SP_RP_', SUBSTRING(`program_id`, 7))
    ELSE `program_id`
END
WHERE `program_id` LIKE 'CM\_CM\_%%'
   OR `program_id` LIKE 'CM\_SY\_%%'
   OR `program_id` LIKE 'SP\_ID\_%%';

UPDATE `te_common`.`cm_sequence_policy`
SET `program_id` = CASE
    WHEN `program_id` LIKE 'CM\_CM\_%%' THEN CONCAT('CM_CO_', SUBSTRING(`program_id`, 7))
    WHEN `program_id` LIKE 'CM\_SY\_%%' THEN CONCAT('CM_CO_', SUBSTRING(`program_id`, 7))
    WHEN `program_id` LIKE 'SP\_ID\_%%' THEN CONCAT('SP_RP_', SUBSTRING(`program_id`, 7))
    ELSE `program_id`
END
WHERE `program_id` LIKE 'CM\_CM\_%%'
   OR `program_id` LIKE 'CM\_SY\_%%'
   OR `program_id` LIKE 'SP\_ID\_%%';

UPDATE `te_common`.`cm_sequence_rule`
SET `program_id` = CASE
    WHEN `program_id` LIKE 'CM\_CM\_%%' THEN CONCAT('CM_CO_', SUBSTRING(`program_id`, 7))
    WHEN `program_id` LIKE 'CM\_SY\_%%' THEN CONCAT('CM_CO_', SUBSTRING(`program_id`, 7))
    WHEN `program_id` LIKE 'SP\_ID\_%%' THEN CONCAT('SP_RP_', SUBSTRING(`program_id`, 7))
    ELSE `program_id`
END
WHERE `program_id` LIKE 'CM\_CM\_%%'
   OR `program_id` LIKE 'CM\_SY\_%%'
   OR `program_id` LIKE 'SP\_ID\_%%';

UPDATE `te_common`.`cm_storage_policy`
SET `policy_id` = CASE
    WHEN `policy_id` LIKE 'CM\_CM\_%%' THEN CONCAT('CM_CO_', SUBSTRING(`policy_id`, 7))
    WHEN `policy_id` LIKE 'CM\_SY\_%%' THEN CONCAT('CM_CO_', SUBSTRING(`policy_id`, 7))
    WHEN `policy_id` LIKE 'SP\_ID\_%%' THEN CONCAT('SP_RP_', SUBSTRING(`policy_id`, 7))
    ELSE `policy_id`
END
WHERE `policy_id` LIKE 'CM\_CM\_%%'
   OR `policy_id` LIKE 'CM\_SY\_%%'
   OR `policy_id` LIKE 'SP\_ID\_%%';

UPDATE `te_common`.`cm_storage_policy`
SET `repository_id` = CASE
    WHEN `repository_id` LIKE 'CM\_CM\_%%' THEN CONCAT('CM_CO_', SUBSTRING(`repository_id`, 7))
    WHEN `repository_id` LIKE 'CM\_SY\_%%' THEN CONCAT('CM_CO_', SUBSTRING(`repository_id`, 7))
    WHEN `repository_id` LIKE 'SP\_ID\_%%' THEN CONCAT('SP_RP_', SUBSTRING(`repository_id`, 7))
    ELSE `repository_id`
END
WHERE `repository_id` LIKE 'CM\_CM\_%%'
   OR `repository_id` LIKE 'CM\_SY\_%%'
   OR `repository_id` LIKE 'SP\_ID\_%%';

UPDATE `te_common`.`cm_storage_repository`
SET `repository_id` = CASE
    WHEN `repository_id` LIKE 'CM\_CM\_%%' THEN CONCAT('CM_CO_', SUBSTRING(`repository_id`, 7))
    WHEN `repository_id` LIKE 'CM\_SY\_%%' THEN CONCAT('CM_CO_', SUBSTRING(`repository_id`, 7))
    WHEN `repository_id` LIKE 'SP\_ID\_%%' THEN CONCAT('SP_RP_', SUBSTRING(`repository_id`, 7))
    ELSE `repository_id`
END
WHERE `repository_id` LIKE 'CM\_CM\_%%'
   OR `repository_id` LIKE 'CM\_SY\_%%'
   OR `repository_id` LIKE 'SP\_ID\_%%';

UPDATE `te_common`.`cm_verified_sql_query`
SET `program_id` = CASE
    WHEN `program_id` LIKE 'CM\_CM\_%%' THEN CONCAT('CM_CO_', SUBSTRING(`program_id`, 7))
    WHEN `program_id` LIKE 'CM\_SY\_%%' THEN CONCAT('CM_CO_', SUBSTRING(`program_id`, 7))
    WHEN `program_id` LIKE 'SP\_ID\_%%' THEN CONCAT('SP_RP_', SUBSTRING(`program_id`, 7))
    ELSE `program_id`
END
WHERE `program_id` LIKE 'CM\_CM\_%%'
   OR `program_id` LIKE 'CM\_SY\_%%'
   OR `program_id` LIKE 'SP\_ID\_%%';

UPDATE `te_common`.`rl_rule`
SET `rule_id` = CASE
    WHEN `rule_id` LIKE 'CM\_CM\_%%' THEN CONCAT('CM_CO_', SUBSTRING(`rule_id`, 7))
    WHEN `rule_id` LIKE 'CM\_SY\_%%' THEN CONCAT('CM_CO_', SUBSTRING(`rule_id`, 7))
    WHEN `rule_id` LIKE 'SP\_ID\_%%' THEN CONCAT('SP_RP_', SUBSTRING(`rule_id`, 7))
    ELSE `rule_id`
END
WHERE `rule_id` LIKE 'CM\_CM\_%%'
   OR `rule_id` LIKE 'CM\_SY\_%%'
   OR `rule_id` LIKE 'SP\_ID\_%%';

UPDATE `te_common`.`rl_rule`
SET `program_id` = CASE
    WHEN `program_id` LIKE 'CM\_CM\_%%' THEN CONCAT('CM_CO_', SUBSTRING(`program_id`, 7))
    WHEN `program_id` LIKE 'CM\_SY\_%%' THEN CONCAT('CM_CO_', SUBSTRING(`program_id`, 7))
    WHEN `program_id` LIKE 'SP\_ID\_%%' THEN CONCAT('SP_RP_', SUBSTRING(`program_id`, 7))
    ELSE `program_id`
END
WHERE `program_id` LIKE 'CM\_CM\_%%'
   OR `program_id` LIKE 'CM\_SY\_%%'
   OR `program_id` LIKE 'SP\_ID\_%%';

UPDATE `te_common`.`rl_rule_action`
SET `rule_id` = CASE
    WHEN `rule_id` LIKE 'CM\_CM\_%%' THEN CONCAT('CM_CO_', SUBSTRING(`rule_id`, 7))
    WHEN `rule_id` LIKE 'CM\_SY\_%%' THEN CONCAT('CM_CO_', SUBSTRING(`rule_id`, 7))
    WHEN `rule_id` LIKE 'SP\_ID\_%%' THEN CONCAT('SP_RP_', SUBSTRING(`rule_id`, 7))
    ELSE `rule_id`
END
WHERE `rule_id` LIKE 'CM\_CM\_%%'
   OR `rule_id` LIKE 'CM\_SY\_%%'
   OR `rule_id` LIKE 'SP\_ID\_%%';

UPDATE `te_common`.`rl_rule_condition`
SET `rule_id` = CASE
    WHEN `rule_id` LIKE 'CM\_CM\_%%' THEN CONCAT('CM_CO_', SUBSTRING(`rule_id`, 7))
    WHEN `rule_id` LIKE 'CM\_SY\_%%' THEN CONCAT('CM_CO_', SUBSTRING(`rule_id`, 7))
    WHEN `rule_id` LIKE 'SP\_ID\_%%' THEN CONCAT('SP_RP_', SUBSTRING(`rule_id`, 7))
    ELSE `rule_id`
END
WHERE `rule_id` LIKE 'CM\_CM\_%%'
   OR `rule_id` LIKE 'CM\_SY\_%%'
   OR `rule_id` LIKE 'SP\_ID\_%%';

UPDATE `te_common`.`rl_rule_evidence`
SET `rule_id` = CASE
    WHEN `rule_id` LIKE 'CM\_CM\_%%' THEN CONCAT('CM_CO_', SUBSTRING(`rule_id`, 7))
    WHEN `rule_id` LIKE 'CM\_SY\_%%' THEN CONCAT('CM_CO_', SUBSTRING(`rule_id`, 7))
    WHEN `rule_id` LIKE 'SP\_ID\_%%' THEN CONCAT('SP_RP_', SUBSTRING(`rule_id`, 7))
    ELSE `rule_id`
END
WHERE `rule_id` LIKE 'CM\_CM\_%%'
   OR `rule_id` LIKE 'CM\_SY\_%%'
   OR `rule_id` LIKE 'SP\_ID\_%%';

UPDATE `te_common`.`sp_policy_rule_candidate`
SET `program_id` = CASE
    WHEN `program_id` LIKE 'CM\_CM\_%%' THEN CONCAT('CM_CO_', SUBSTRING(`program_id`, 7))
    WHEN `program_id` LIKE 'CM\_SY\_%%' THEN CONCAT('CM_CO_', SUBSTRING(`program_id`, 7))
    WHEN `program_id` LIKE 'SP\_ID\_%%' THEN CONCAT('SP_RP_', SUBSTRING(`program_id`, 7))
    ELSE `program_id`
END
WHERE `program_id` LIKE 'CM\_CM\_%%'
   OR `program_id` LIKE 'CM\_SY\_%%'
   OR `program_id` LIKE 'SP\_ID\_%%';

UPDATE `te_common`.`system_menu_button`
SET `program_id` = CASE
    WHEN `program_id` LIKE 'CM\_CM\_%%' THEN CONCAT('CM_CO_', SUBSTRING(`program_id`, 7))
    WHEN `program_id` LIKE 'CM\_SY\_%%' THEN CONCAT('CM_CO_', SUBSTRING(`program_id`, 7))
    WHEN `program_id` LIKE 'SP\_ID\_%%' THEN CONCAT('SP_RP_', SUBSTRING(`program_id`, 7))
    ELSE `program_id`
END
WHERE `program_id` LIKE 'CM\_CM\_%%'
   OR `program_id` LIKE 'CM\_SY\_%%'
   OR `program_id` LIKE 'SP\_ID\_%%';

UPDATE `te_common`.`system_menu_button_crud_permission`
SET `permission_id` = CASE
    WHEN `permission_id` LIKE 'CM\_CM\_%%' THEN CONCAT('CM_CO_', SUBSTRING(`permission_id`, 7))
    WHEN `permission_id` LIKE 'CM\_SY\_%%' THEN CONCAT('CM_CO_', SUBSTRING(`permission_id`, 7))
    WHEN `permission_id` LIKE 'SP\_ID\_%%' THEN CONCAT('SP_RP_', SUBSTRING(`permission_id`, 7))
    ELSE `permission_id`
END
WHERE `permission_id` LIKE 'CM\_CM\_%%'
   OR `permission_id` LIKE 'CM\_SY\_%%'
   OR `permission_id` LIKE 'SP\_ID\_%%';

UPDATE `te_common`.`system_user`
SET `user_id` = CASE
    WHEN `user_id` LIKE 'CM\_CM\_%%' THEN CONCAT('CM_CO_', SUBSTRING(`user_id`, 7))
    WHEN `user_id` LIKE 'CM\_SY\_%%' THEN CONCAT('CM_CO_', SUBSTRING(`user_id`, 7))
    WHEN `user_id` LIKE 'SP\_ID\_%%' THEN CONCAT('SP_RP_', SUBSTRING(`user_id`, 7))
    ELSE `user_id`
END
WHERE `user_id` LIKE 'CM\_CM\_%%'
   OR `user_id` LIKE 'CM\_SY\_%%'
   OR `user_id` LIKE 'SP\_ID\_%%';

UPDATE `te_common`.`system_user`
SET `user_login_id` = CASE
    WHEN `user_login_id` LIKE 'CM\_CM\_%%' THEN CONCAT('CM_CO_', SUBSTRING(`user_login_id`, 7))
    WHEN `user_login_id` LIKE 'CM\_SY\_%%' THEN CONCAT('CM_CO_', SUBSTRING(`user_login_id`, 7))
    WHEN `user_login_id` LIKE 'SP\_ID\_%%' THEN CONCAT('SP_RP_', SUBSTRING(`user_login_id`, 7))
    ELSE `user_login_id`
END
WHERE `user_login_id` LIKE 'CM\_CM\_%%'
   OR `user_login_id` LIKE 'CM\_SY\_%%'
   OR `user_login_id` LIKE 'SP\_ID\_%%';

UPDATE `te_health_companion`.`ac_action`
SET `action_target_id` = CASE
    WHEN `action_target_id` LIKE 'CM\_CM\_%%' THEN CONCAT('CM_CO_', SUBSTRING(`action_target_id`, 7))
    WHEN `action_target_id` LIKE 'CM\_SY\_%%' THEN CONCAT('CM_CO_', SUBSTRING(`action_target_id`, 7))
    WHEN `action_target_id` LIKE 'SP\_ID\_%%' THEN CONCAT('SP_RP_', SUBSTRING(`action_target_id`, 7))
    ELSE `action_target_id`
END
WHERE `action_target_id` LIKE 'CM\_CM\_%%'
   OR `action_target_id` LIKE 'CM\_SY\_%%'
   OR `action_target_id` LIKE 'SP\_ID\_%%';

UPDATE `te_health_companion`.`ac_action`
SET `program_id` = CASE
    WHEN `program_id` LIKE 'CM\_CM\_%%' THEN CONCAT('CM_CO_', SUBSTRING(`program_id`, 7))
    WHEN `program_id` LIKE 'CM\_SY\_%%' THEN CONCAT('CM_CO_', SUBSTRING(`program_id`, 7))
    WHEN `program_id` LIKE 'SP\_ID\_%%' THEN CONCAT('SP_RP_', SUBSTRING(`program_id`, 7))
    ELSE `program_id`
END
WHERE `program_id` LIKE 'CM\_CM\_%%'
   OR `program_id` LIKE 'CM\_SY\_%%'
   OR `program_id` LIKE 'SP\_ID\_%%';

UPDATE `te_health_companion`.`at_audit`
SET `rule_id` = CASE
    WHEN `rule_id` LIKE 'CM\_CM\_%%' THEN CONCAT('CM_CO_', SUBSTRING(`rule_id`, 7))
    WHEN `rule_id` LIKE 'CM\_SY\_%%' THEN CONCAT('CM_CO_', SUBSTRING(`rule_id`, 7))
    WHEN `rule_id` LIKE 'SP\_ID\_%%' THEN CONCAT('SP_RP_', SUBSTRING(`rule_id`, 7))
    ELSE `rule_id`
END
WHERE `rule_id` LIKE 'CM\_CM\_%%'
   OR `rule_id` LIKE 'CM\_SY\_%%'
   OR `rule_id` LIKE 'SP\_ID\_%%';

UPDATE `te_health_companion`.`at_audit`
SET `program_id` = CASE
    WHEN `program_id` LIKE 'CM\_CM\_%%' THEN CONCAT('CM_CO_', SUBSTRING(`program_id`, 7))
    WHEN `program_id` LIKE 'CM\_SY\_%%' THEN CONCAT('CM_CO_', SUBSTRING(`program_id`, 7))
    WHEN `program_id` LIKE 'SP\_ID\_%%' THEN CONCAT('SP_RP_', SUBSTRING(`program_id`, 7))
    ELSE `program_id`
END
WHERE `program_id` LIKE 'CM\_CM\_%%'
   OR `program_id` LIKE 'CM\_SY\_%%'
   OR `program_id` LIKE 'SP\_ID\_%%';

UPDATE `te_health_companion`.`dc_decision`
SET `user_id` = CASE
    WHEN `user_id` LIKE 'CM\_CM\_%%' THEN CONCAT('CM_CO_', SUBSTRING(`user_id`, 7))
    WHEN `user_id` LIKE 'CM\_SY\_%%' THEN CONCAT('CM_CO_', SUBSTRING(`user_id`, 7))
    WHEN `user_id` LIKE 'SP\_ID\_%%' THEN CONCAT('SP_RP_', SUBSTRING(`user_id`, 7))
    ELSE `user_id`
END
WHERE `user_id` LIKE 'CM\_CM\_%%'
   OR `user_id` LIKE 'CM\_SY\_%%'
   OR `user_id` LIKE 'SP\_ID\_%%';

UPDATE `te_health_companion`.`dc_decision`
SET `rule_id` = CASE
    WHEN `rule_id` LIKE 'CM\_CM\_%%' THEN CONCAT('CM_CO_', SUBSTRING(`rule_id`, 7))
    WHEN `rule_id` LIKE 'CM\_SY\_%%' THEN CONCAT('CM_CO_', SUBSTRING(`rule_id`, 7))
    WHEN `rule_id` LIKE 'SP\_ID\_%%' THEN CONCAT('SP_RP_', SUBSTRING(`rule_id`, 7))
    ELSE `rule_id`
END
WHERE `rule_id` LIKE 'CM\_CM\_%%'
   OR `rule_id` LIKE 'CM\_SY\_%%'
   OR `rule_id` LIKE 'SP\_ID\_%%';

UPDATE `te_health_companion`.`dc_decision`
SET `program_id` = CASE
    WHEN `program_id` LIKE 'CM\_CM\_%%' THEN CONCAT('CM_CO_', SUBSTRING(`program_id`, 7))
    WHEN `program_id` LIKE 'CM\_SY\_%%' THEN CONCAT('CM_CO_', SUBSTRING(`program_id`, 7))
    WHEN `program_id` LIKE 'SP\_ID\_%%' THEN CONCAT('SP_RP_', SUBSTRING(`program_id`, 7))
    ELSE `program_id`
END
WHERE `program_id` LIKE 'CM\_CM\_%%'
   OR `program_id` LIKE 'CM\_SY\_%%'
   OR `program_id` LIKE 'SP\_ID\_%%';

UPDATE `te_health_companion`.`dc_decision_detail`
SET `rule_id` = CASE
    WHEN `rule_id` LIKE 'CM\_CM\_%%' THEN CONCAT('CM_CO_', SUBSTRING(`rule_id`, 7))
    WHEN `rule_id` LIKE 'CM\_SY\_%%' THEN CONCAT('CM_CO_', SUBSTRING(`rule_id`, 7))
    WHEN `rule_id` LIKE 'SP\_ID\_%%' THEN CONCAT('SP_RP_', SUBSTRING(`rule_id`, 7))
    ELSE `rule_id`
END
WHERE `rule_id` LIKE 'CM\_CM\_%%'
   OR `rule_id` LIKE 'CM\_SY\_%%'
   OR `rule_id` LIKE 'SP\_ID\_%%';

UPDATE `te_health_companion`.`dc_decision_detail`
SET `program_id` = CASE
    WHEN `program_id` LIKE 'CM\_CM\_%%' THEN CONCAT('CM_CO_', SUBSTRING(`program_id`, 7))
    WHEN `program_id` LIKE 'CM\_SY\_%%' THEN CONCAT('CM_CO_', SUBSTRING(`program_id`, 7))
    WHEN `program_id` LIKE 'SP\_ID\_%%' THEN CONCAT('SP_RP_', SUBSTRING(`program_id`, 7))
    ELSE `program_id`
END
WHERE `program_id` LIKE 'CM\_CM\_%%'
   OR `program_id` LIKE 'CM\_SY\_%%'
   OR `program_id` LIKE 'SP\_ID\_%%';

UPDATE `te_health_companion`.`fb_feedback`
SET `user_id` = CASE
    WHEN `user_id` LIKE 'CM\_CM\_%%' THEN CONCAT('CM_CO_', SUBSTRING(`user_id`, 7))
    WHEN `user_id` LIKE 'CM\_SY\_%%' THEN CONCAT('CM_CO_', SUBSTRING(`user_id`, 7))
    WHEN `user_id` LIKE 'SP\_ID\_%%' THEN CONCAT('SP_RP_', SUBSTRING(`user_id`, 7))
    ELSE `user_id`
END
WHERE `user_id` LIKE 'CM\_CM\_%%'
   OR `user_id` LIKE 'CM\_SY\_%%'
   OR `user_id` LIKE 'SP\_ID\_%%';

UPDATE `te_health_companion`.`fb_feedback`
SET `program_id` = CASE
    WHEN `program_id` LIKE 'CM\_CM\_%%' THEN CONCAT('CM_CO_', SUBSTRING(`program_id`, 7))
    WHEN `program_id` LIKE 'CM\_SY\_%%' THEN CONCAT('CM_CO_', SUBSTRING(`program_id`, 7))
    WHEN `program_id` LIKE 'SP\_ID\_%%' THEN CONCAT('SP_RP_', SUBSTRING(`program_id`, 7))
    ELSE `program_id`
END
WHERE `program_id` LIKE 'CM\_CM\_%%'
   OR `program_id` LIKE 'CM\_SY\_%%'
   OR `program_id` LIKE 'SP\_ID\_%%';

UPDATE `te_story_platform`.`sp_identifier_blueprint`
SET `blueprint_id` = CASE
    WHEN `blueprint_id` LIKE 'CM\_CM\_%%' THEN CONCAT('CM_CO_', SUBSTRING(`blueprint_id`, 7))
    WHEN `blueprint_id` LIKE 'CM\_SY\_%%' THEN CONCAT('CM_CO_', SUBSTRING(`blueprint_id`, 7))
    WHEN `blueprint_id` LIKE 'SP\_ID\_%%' THEN CONCAT('SP_RP_', SUBSTRING(`blueprint_id`, 7))
    ELSE `blueprint_id`
END
WHERE `blueprint_id` LIKE 'CM\_CM\_%%'
   OR `blueprint_id` LIKE 'CM\_SY\_%%'
   OR `blueprint_id` LIKE 'SP\_ID\_%%';

UPDATE `te_story_platform`.`sp_identifier_blueprint`
SET `program_id` = CASE
    WHEN `program_id` LIKE 'CM\_CM\_%%' THEN CONCAT('CM_CO_', SUBSTRING(`program_id`, 7))
    WHEN `program_id` LIKE 'CM\_SY\_%%' THEN CONCAT('CM_CO_', SUBSTRING(`program_id`, 7))
    WHEN `program_id` LIKE 'SP\_ID\_%%' THEN CONCAT('SP_RP_', SUBSTRING(`program_id`, 7))
    ELSE `program_id`
END
WHERE `program_id` LIKE 'CM\_CM\_%%'
   OR `program_id` LIKE 'CM\_SY\_%%'
   OR `program_id` LIKE 'SP\_ID\_%%';

UPDATE `te_story_platform`.`sp_identifier_sequence`
SET `identifier_sequence_id` = CASE
    WHEN `identifier_sequence_id` LIKE 'CM\_CM\_%%' THEN CONCAT('CM_CO_', SUBSTRING(`identifier_sequence_id`, 7))
    WHEN `identifier_sequence_id` LIKE 'CM\_SY\_%%' THEN CONCAT('CM_CO_', SUBSTRING(`identifier_sequence_id`, 7))
    WHEN `identifier_sequence_id` LIKE 'SP\_ID\_%%' THEN CONCAT('SP_RP_', SUBSTRING(`identifier_sequence_id`, 7))
    ELSE `identifier_sequence_id`
END
WHERE `identifier_sequence_id` LIKE 'CM\_CM\_%%'
   OR `identifier_sequence_id` LIKE 'CM\_SY\_%%'
   OR `identifier_sequence_id` LIKE 'SP\_ID\_%%';

UPDATE `te_story_platform`.`sp_identifier_sequence`
SET `program_id` = CASE
    WHEN `program_id` LIKE 'CM\_CM\_%%' THEN CONCAT('CM_CO_', SUBSTRING(`program_id`, 7))
    WHEN `program_id` LIKE 'CM\_SY\_%%' THEN CONCAT('CM_CO_', SUBSTRING(`program_id`, 7))
    WHEN `program_id` LIKE 'SP\_ID\_%%' THEN CONCAT('SP_RP_', SUBSTRING(`program_id`, 7))
    ELSE `program_id`
END
WHERE `program_id` LIKE 'CM\_CM\_%%'
   OR `program_id` LIKE 'CM\_SY\_%%'
   OR `program_id` LIKE 'SP\_ID\_%%';

UPDATE `te_story_platform`.`sp_impact_analysis_result`
SET `program_id` = CASE
    WHEN `program_id` LIKE 'CM\_CM\_%%' THEN CONCAT('CM_CO_', SUBSTRING(`program_id`, 7))
    WHEN `program_id` LIKE 'CM\_SY\_%%' THEN CONCAT('CM_CO_', SUBSTRING(`program_id`, 7))
    WHEN `program_id` LIKE 'SP\_ID\_%%' THEN CONCAT('SP_RP_', SUBSTRING(`program_id`, 7))
    ELSE `program_id`
END
WHERE `program_id` LIKE 'CM\_CM\_%%'
   OR `program_id` LIKE 'CM\_SY\_%%'
   OR `program_id` LIKE 'SP\_ID\_%%';

UPDATE `te_story_platform`.`sp_knowledge_hold`
SET `program_id` = CASE
    WHEN `program_id` LIKE 'CM\_CM\_%%' THEN CONCAT('CM_CO_', SUBSTRING(`program_id`, 7))
    WHEN `program_id` LIKE 'CM\_SY\_%%' THEN CONCAT('CM_CO_', SUBSTRING(`program_id`, 7))
    WHEN `program_id` LIKE 'SP\_ID\_%%' THEN CONCAT('SP_RP_', SUBSTRING(`program_id`, 7))
    ELSE `program_id`
END
WHERE `program_id` LIKE 'CM\_CM\_%%'
   OR `program_id` LIKE 'CM\_SY\_%%'
   OR `program_id` LIKE 'SP\_ID\_%%';

UPDATE `te_story_platform`.`sp_knowledge_relationship_hold`
SET `program_id` = CASE
    WHEN `program_id` LIKE 'CM\_CM\_%%' THEN CONCAT('CM_CO_', SUBSTRING(`program_id`, 7))
    WHEN `program_id` LIKE 'CM\_SY\_%%' THEN CONCAT('CM_CO_', SUBSTRING(`program_id`, 7))
    WHEN `program_id` LIKE 'SP\_ID\_%%' THEN CONCAT('SP_RP_', SUBSTRING(`program_id`, 7))
    ELSE `program_id`
END
WHERE `program_id` LIKE 'CM\_CM\_%%'
   OR `program_id` LIKE 'CM\_SY\_%%'
   OR `program_id` LIKE 'SP\_ID\_%%';

UPDATE `te_story_platform`.`sp_metadata`
SET `program_id` = CASE
    WHEN `program_id` LIKE 'CM\_CM\_%%' THEN CONCAT('CM_CO_', SUBSTRING(`program_id`, 7))
    WHEN `program_id` LIKE 'CM\_SY\_%%' THEN CONCAT('CM_CO_', SUBSTRING(`program_id`, 7))
    WHEN `program_id` LIKE 'SP\_ID\_%%' THEN CONCAT('SP_RP_', SUBSTRING(`program_id`, 7))
    ELSE `program_id`
END
WHERE `program_id` LIKE 'CM\_CM\_%%'
   OR `program_id` LIKE 'CM\_SY\_%%'
   OR `program_id` LIKE 'SP\_ID\_%%';

UPDATE `te_story_platform`.`sp_object`
SET `lifecycle_id` = CASE
    WHEN `lifecycle_id` LIKE 'CM\_CM\_%%' THEN CONCAT('CM_CO_', SUBSTRING(`lifecycle_id`, 7))
    WHEN `lifecycle_id` LIKE 'CM\_SY\_%%' THEN CONCAT('CM_CO_', SUBSTRING(`lifecycle_id`, 7))
    WHEN `lifecycle_id` LIKE 'SP\_ID\_%%' THEN CONCAT('SP_RP_', SUBSTRING(`lifecycle_id`, 7))
    ELSE `lifecycle_id`
END
WHERE `lifecycle_id` LIKE 'CM\_CM\_%%'
   OR `lifecycle_id` LIKE 'CM\_SY\_%%'
   OR `lifecycle_id` LIKE 'SP\_ID\_%%';

UPDATE `te_story_platform`.`sp_object`
SET `program_id` = CASE
    WHEN `program_id` LIKE 'CM\_CM\_%%' THEN CONCAT('CM_CO_', SUBSTRING(`program_id`, 7))
    WHEN `program_id` LIKE 'CM\_SY\_%%' THEN CONCAT('CM_CO_', SUBSTRING(`program_id`, 7))
    WHEN `program_id` LIKE 'SP\_ID\_%%' THEN CONCAT('SP_RP_', SUBSTRING(`program_id`, 7))
    ELSE `program_id`
END
WHERE `program_id` LIKE 'CM\_CM\_%%'
   OR `program_id` LIKE 'CM\_SY\_%%'
   OR `program_id` LIKE 'SP\_ID\_%%';

UPDATE `te_story_platform`.`sp_object_lifecycle`
SET `program_id` = CASE
    WHEN `program_id` LIKE 'CM\_CM\_%%' THEN CONCAT('CM_CO_', SUBSTRING(`program_id`, 7))
    WHEN `program_id` LIKE 'CM\_SY\_%%' THEN CONCAT('CM_CO_', SUBSTRING(`program_id`, 7))
    WHEN `program_id` LIKE 'SP\_ID\_%%' THEN CONCAT('SP_RP_', SUBSTRING(`program_id`, 7))
    ELSE `program_id`
END
WHERE `program_id` LIKE 'CM\_CM\_%%'
   OR `program_id` LIKE 'CM\_SY\_%%'
   OR `program_id` LIKE 'SP\_ID\_%%';

UPDATE `te_story_platform`.`sp_relationship`
SET `source_object_id` = CASE
    WHEN `source_object_id` LIKE 'CM\_CM\_%%' THEN CONCAT('CM_CO_', SUBSTRING(`source_object_id`, 7))
    WHEN `source_object_id` LIKE 'CM\_SY\_%%' THEN CONCAT('CM_CO_', SUBSTRING(`source_object_id`, 7))
    WHEN `source_object_id` LIKE 'SP\_ID\_%%' THEN CONCAT('SP_RP_', SUBSTRING(`source_object_id`, 7))
    ELSE `source_object_id`
END
WHERE `source_object_id` LIKE 'CM\_CM\_%%'
   OR `source_object_id` LIKE 'CM\_SY\_%%'
   OR `source_object_id` LIKE 'SP\_ID\_%%';

UPDATE `te_story_platform`.`sp_relationship`
SET `target_object_id` = CASE
    WHEN `target_object_id` LIKE 'CM\_CM\_%%' THEN CONCAT('CM_CO_', SUBSTRING(`target_object_id`, 7))
    WHEN `target_object_id` LIKE 'CM\_SY\_%%' THEN CONCAT('CM_CO_', SUBSTRING(`target_object_id`, 7))
    WHEN `target_object_id` LIKE 'SP\_ID\_%%' THEN CONCAT('SP_RP_', SUBSTRING(`target_object_id`, 7))
    ELSE `target_object_id`
END
WHERE `target_object_id` LIKE 'CM\_CM\_%%'
   OR `target_object_id` LIKE 'CM\_SY\_%%'
   OR `target_object_id` LIKE 'SP\_ID\_%%';

UPDATE `te_story_platform`.`sp_relationship`
SET `program_id` = CASE
    WHEN `program_id` LIKE 'CM\_CM\_%%' THEN CONCAT('CM_CO_', SUBSTRING(`program_id`, 7))
    WHEN `program_id` LIKE 'CM\_SY\_%%' THEN CONCAT('CM_CO_', SUBSTRING(`program_id`, 7))
    WHEN `program_id` LIKE 'SP\_ID\_%%' THEN CONCAT('SP_RP_', SUBSTRING(`program_id`, 7))
    ELSE `program_id`
END
WHERE `program_id` LIKE 'CM\_CM\_%%'
   OR `program_id` LIKE 'CM\_SY\_%%'
   OR `program_id` LIKE 'SP\_ID\_%%';

SET FOREIGN_KEY_CHECKS = @OLD_FOREIGN_KEY_CHECKS;

SELECT 'te_common' AS table_schema, 'cm_audit_policy' AS table_name,
       'audit_policy_id' AS column_name, COUNT(*) AS invalid_domain_prefix_count
FROM `te_common`.`cm_audit_policy`
WHERE `audit_policy_id` LIKE 'CM\_CM\_%%'
   OR `audit_policy_id` LIKE 'CM\_SY\_%%'
   OR `audit_policy_id` LIKE 'SP\_ID\_%%';

SELECT 'te_common' AS table_schema, 'cm_business_domain' AS table_name,
       'business_domain_id' AS column_name, COUNT(*) AS invalid_domain_prefix_count
FROM `te_common`.`cm_business_domain`
WHERE `business_domain_id` LIKE 'CM\_CM\_%%'
   OR `business_domain_id` LIKE 'CM\_SY\_%%'
   OR `business_domain_id` LIKE 'SP\_ID\_%%';

SELECT 'te_common' AS table_schema, 'cm_change_history' AS table_name,
       'change_history_id' AS column_name, COUNT(*) AS invalid_domain_prefix_count
FROM `te_common`.`cm_change_history`
WHERE `change_history_id` LIKE 'CM\_CM\_%%'
   OR `change_history_id` LIKE 'CM\_SY\_%%'
   OR `change_history_id` LIKE 'SP\_ID\_%%';

SELECT 'te_common' AS table_schema, 'cm_change_history' AS table_name,
       'target_record_id' AS column_name, COUNT(*) AS invalid_domain_prefix_count
FROM `te_common`.`cm_change_history`
WHERE `target_record_id` LIKE 'CM\_CM\_%%'
   OR `target_record_id` LIKE 'CM\_SY\_%%'
   OR `target_record_id` LIKE 'SP\_ID\_%%';

SELECT 'te_common' AS table_schema, 'cm_change_history' AS table_name,
       'program_id' AS column_name, COUNT(*) AS invalid_domain_prefix_count
FROM `te_common`.`cm_change_history`
WHERE `program_id` LIKE 'CM\_CM\_%%'
   OR `program_id` LIKE 'CM\_SY\_%%'
   OR `program_id` LIKE 'SP\_ID\_%%';

SELECT 'te_common' AS table_schema, 'cm_common_code' AS table_name,
       'program_id' AS column_name, COUNT(*) AS invalid_domain_prefix_count
FROM `te_common`.`cm_common_code`
WHERE `program_id` LIKE 'CM\_CM\_%%'
   OR `program_id` LIKE 'CM\_SY\_%%'
   OR `program_id` LIKE 'SP\_ID\_%%';

SELECT 'te_common' AS table_schema, 'cm_common_code_group' AS table_name,
       'program_id' AS column_name, COUNT(*) AS invalid_domain_prefix_count
FROM `te_common`.`cm_common_code_group`
WHERE `program_id` LIKE 'CM\_CM\_%%'
   OR `program_id` LIKE 'CM\_SY\_%%'
   OR `program_id` LIKE 'SP\_ID\_%%';

SELECT 'te_common' AS table_schema, 'cm_legal_retention_policy' AS table_name,
       'legal_retention_policy_id' AS column_name, COUNT(*) AS invalid_domain_prefix_count
FROM `te_common`.`cm_legal_retention_policy`
WHERE `legal_retention_policy_id` LIKE 'CM\_CM\_%%'
   OR `legal_retention_policy_id` LIKE 'CM\_SY\_%%'
   OR `legal_retention_policy_id` LIKE 'SP\_ID\_%%';

SELECT 'te_common' AS table_schema, 'cm_member' AS table_name,
       'member_id' AS column_name, COUNT(*) AS invalid_domain_prefix_count
FROM `te_common`.`cm_member`
WHERE `member_id` LIKE 'CM\_CM\_%%'
   OR `member_id` LIKE 'CM\_SY\_%%'
   OR `member_id` LIKE 'SP\_ID\_%%';

SELECT 'te_common' AS table_schema, 'cm_member_role' AS table_name,
       'member_role_id' AS column_name, COUNT(*) AS invalid_domain_prefix_count
FROM `te_common`.`cm_member_role`
WHERE `member_role_id` LIKE 'CM\_CM\_%%'
   OR `member_role_id` LIKE 'CM\_SY\_%%'
   OR `member_role_id` LIKE 'SP\_ID\_%%';

SELECT 'te_common' AS table_schema, 'cm_member_role' AS table_name,
       'member_id' AS column_name, COUNT(*) AS invalid_domain_prefix_count
FROM `te_common`.`cm_member_role`
WHERE `member_id` LIKE 'CM\_CM\_%%'
   OR `member_id` LIKE 'CM\_SY\_%%'
   OR `member_id` LIKE 'SP\_ID\_%%';

SELECT 'te_common' AS table_schema, 'cm_member_role' AS table_name,
       'role_id' AS column_name, COUNT(*) AS invalid_domain_prefix_count
FROM `te_common`.`cm_member_role`
WHERE `role_id` LIKE 'CM\_CM\_%%'
   OR `role_id` LIKE 'CM\_SY\_%%'
   OR `role_id` LIKE 'SP\_ID\_%%';

SELECT 'te_common' AS table_schema, 'cm_member_role' AS table_name,
       'program_id' AS column_name, COUNT(*) AS invalid_domain_prefix_count
FROM `te_common`.`cm_member_role`
WHERE `program_id` LIKE 'CM\_CM\_%%'
   OR `program_id` LIKE 'CM\_SY\_%%'
   OR `program_id` LIKE 'SP\_ID\_%%';

SELECT 'te_common' AS table_schema, 'cm_repository' AS table_name,
       'repository_id' AS column_name, COUNT(*) AS invalid_domain_prefix_count
FROM `te_common`.`cm_repository`
WHERE `repository_id` LIKE 'CM\_CM\_%%'
   OR `repository_id` LIKE 'CM\_SY\_%%'
   OR `repository_id` LIKE 'SP\_ID\_%%';

SELECT 'te_common' AS table_schema, 'cm_repository' AS table_name,
       'program_id' AS column_name, COUNT(*) AS invalid_domain_prefix_count
FROM `te_common`.`cm_repository`
WHERE `program_id` LIKE 'CM\_CM\_%%'
   OR `program_id` LIKE 'CM\_SY\_%%'
   OR `program_id` LIKE 'SP\_ID\_%%';

SELECT 'te_common' AS table_schema, 'cm_role' AS table_name,
       'role_id' AS column_name, COUNT(*) AS invalid_domain_prefix_count
FROM `te_common`.`cm_role`
WHERE `role_id` LIKE 'CM\_CM\_%%'
   OR `role_id` LIKE 'CM\_SY\_%%'
   OR `role_id` LIKE 'SP\_ID\_%%';

SELECT 'te_common' AS table_schema, 'cm_role' AS table_name,
       'program_id' AS column_name, COUNT(*) AS invalid_domain_prefix_count
FROM `te_common`.`cm_role`
WHERE `program_id` LIKE 'CM\_CM\_%%'
   OR `program_id` LIKE 'CM\_SY\_%%'
   OR `program_id` LIKE 'SP\_ID\_%%';

SELECT 'te_common' AS table_schema, 'cm_sequence_format' AS table_name,
       'program_id' AS column_name, COUNT(*) AS invalid_domain_prefix_count
FROM `te_common`.`cm_sequence_format`
WHERE `program_id` LIKE 'CM\_CM\_%%'
   OR `program_id` LIKE 'CM\_SY\_%%'
   OR `program_id` LIKE 'SP\_ID\_%%';

SELECT 'te_common' AS table_schema, 'cm_sequence_policy' AS table_name,
       'program_id' AS column_name, COUNT(*) AS invalid_domain_prefix_count
FROM `te_common`.`cm_sequence_policy`
WHERE `program_id` LIKE 'CM\_CM\_%%'
   OR `program_id` LIKE 'CM\_SY\_%%'
   OR `program_id` LIKE 'SP\_ID\_%%';

SELECT 'te_common' AS table_schema, 'cm_sequence_rule' AS table_name,
       'program_id' AS column_name, COUNT(*) AS invalid_domain_prefix_count
FROM `te_common`.`cm_sequence_rule`
WHERE `program_id` LIKE 'CM\_CM\_%%'
   OR `program_id` LIKE 'CM\_SY\_%%'
   OR `program_id` LIKE 'SP\_ID\_%%';

SELECT 'te_common' AS table_schema, 'cm_storage_policy' AS table_name,
       'policy_id' AS column_name, COUNT(*) AS invalid_domain_prefix_count
FROM `te_common`.`cm_storage_policy`
WHERE `policy_id` LIKE 'CM\_CM\_%%'
   OR `policy_id` LIKE 'CM\_SY\_%%'
   OR `policy_id` LIKE 'SP\_ID\_%%';

SELECT 'te_common' AS table_schema, 'cm_storage_policy' AS table_name,
       'repository_id' AS column_name, COUNT(*) AS invalid_domain_prefix_count
FROM `te_common`.`cm_storage_policy`
WHERE `repository_id` LIKE 'CM\_CM\_%%'
   OR `repository_id` LIKE 'CM\_SY\_%%'
   OR `repository_id` LIKE 'SP\_ID\_%%';

SELECT 'te_common' AS table_schema, 'cm_storage_repository' AS table_name,
       'repository_id' AS column_name, COUNT(*) AS invalid_domain_prefix_count
FROM `te_common`.`cm_storage_repository`
WHERE `repository_id` LIKE 'CM\_CM\_%%'
   OR `repository_id` LIKE 'CM\_SY\_%%'
   OR `repository_id` LIKE 'SP\_ID\_%%';

SELECT 'te_common' AS table_schema, 'cm_verified_sql_query' AS table_name,
       'program_id' AS column_name, COUNT(*) AS invalid_domain_prefix_count
FROM `te_common`.`cm_verified_sql_query`
WHERE `program_id` LIKE 'CM\_CM\_%%'
   OR `program_id` LIKE 'CM\_SY\_%%'
   OR `program_id` LIKE 'SP\_ID\_%%';

SELECT 'te_common' AS table_schema, 'rl_rule' AS table_name,
       'rule_id' AS column_name, COUNT(*) AS invalid_domain_prefix_count
FROM `te_common`.`rl_rule`
WHERE `rule_id` LIKE 'CM\_CM\_%%'
   OR `rule_id` LIKE 'CM\_SY\_%%'
   OR `rule_id` LIKE 'SP\_ID\_%%';

SELECT 'te_common' AS table_schema, 'rl_rule' AS table_name,
       'program_id' AS column_name, COUNT(*) AS invalid_domain_prefix_count
FROM `te_common`.`rl_rule`
WHERE `program_id` LIKE 'CM\_CM\_%%'
   OR `program_id` LIKE 'CM\_SY\_%%'
   OR `program_id` LIKE 'SP\_ID\_%%';

SELECT 'te_common' AS table_schema, 'rl_rule_action' AS table_name,
       'rule_id' AS column_name, COUNT(*) AS invalid_domain_prefix_count
FROM `te_common`.`rl_rule_action`
WHERE `rule_id` LIKE 'CM\_CM\_%%'
   OR `rule_id` LIKE 'CM\_SY\_%%'
   OR `rule_id` LIKE 'SP\_ID\_%%';

SELECT 'te_common' AS table_schema, 'rl_rule_condition' AS table_name,
       'rule_id' AS column_name, COUNT(*) AS invalid_domain_prefix_count
FROM `te_common`.`rl_rule_condition`
WHERE `rule_id` LIKE 'CM\_CM\_%%'
   OR `rule_id` LIKE 'CM\_SY\_%%'
   OR `rule_id` LIKE 'SP\_ID\_%%';

SELECT 'te_common' AS table_schema, 'rl_rule_evidence' AS table_name,
       'rule_id' AS column_name, COUNT(*) AS invalid_domain_prefix_count
FROM `te_common`.`rl_rule_evidence`
WHERE `rule_id` LIKE 'CM\_CM\_%%'
   OR `rule_id` LIKE 'CM\_SY\_%%'
   OR `rule_id` LIKE 'SP\_ID\_%%';

SELECT 'te_common' AS table_schema, 'sp_policy_rule_candidate' AS table_name,
       'program_id' AS column_name, COUNT(*) AS invalid_domain_prefix_count
FROM `te_common`.`sp_policy_rule_candidate`
WHERE `program_id` LIKE 'CM\_CM\_%%'
   OR `program_id` LIKE 'CM\_SY\_%%'
   OR `program_id` LIKE 'SP\_ID\_%%';

SELECT 'te_common' AS table_schema, 'system_menu_button' AS table_name,
       'program_id' AS column_name, COUNT(*) AS invalid_domain_prefix_count
FROM `te_common`.`system_menu_button`
WHERE `program_id` LIKE 'CM\_CM\_%%'
   OR `program_id` LIKE 'CM\_SY\_%%'
   OR `program_id` LIKE 'SP\_ID\_%%';

SELECT 'te_common' AS table_schema, 'system_menu_button_crud_permission' AS table_name,
       'permission_id' AS column_name, COUNT(*) AS invalid_domain_prefix_count
FROM `te_common`.`system_menu_button_crud_permission`
WHERE `permission_id` LIKE 'CM\_CM\_%%'
   OR `permission_id` LIKE 'CM\_SY\_%%'
   OR `permission_id` LIKE 'SP\_ID\_%%';

SELECT 'te_common' AS table_schema, 'system_user' AS table_name,
       'user_id' AS column_name, COUNT(*) AS invalid_domain_prefix_count
FROM `te_common`.`system_user`
WHERE `user_id` LIKE 'CM\_CM\_%%'
   OR `user_id` LIKE 'CM\_SY\_%%'
   OR `user_id` LIKE 'SP\_ID\_%%';

SELECT 'te_common' AS table_schema, 'system_user' AS table_name,
       'user_login_id' AS column_name, COUNT(*) AS invalid_domain_prefix_count
FROM `te_common`.`system_user`
WHERE `user_login_id` LIKE 'CM\_CM\_%%'
   OR `user_login_id` LIKE 'CM\_SY\_%%'
   OR `user_login_id` LIKE 'SP\_ID\_%%';

SELECT 'te_health_companion' AS table_schema, 'ac_action' AS table_name,
       'action_target_id' AS column_name, COUNT(*) AS invalid_domain_prefix_count
FROM `te_health_companion`.`ac_action`
WHERE `action_target_id` LIKE 'CM\_CM\_%%'
   OR `action_target_id` LIKE 'CM\_SY\_%%'
   OR `action_target_id` LIKE 'SP\_ID\_%%';

SELECT 'te_health_companion' AS table_schema, 'ac_action' AS table_name,
       'program_id' AS column_name, COUNT(*) AS invalid_domain_prefix_count
FROM `te_health_companion`.`ac_action`
WHERE `program_id` LIKE 'CM\_CM\_%%'
   OR `program_id` LIKE 'CM\_SY\_%%'
   OR `program_id` LIKE 'SP\_ID\_%%';

SELECT 'te_health_companion' AS table_schema, 'at_audit' AS table_name,
       'rule_id' AS column_name, COUNT(*) AS invalid_domain_prefix_count
FROM `te_health_companion`.`at_audit`
WHERE `rule_id` LIKE 'CM\_CM\_%%'
   OR `rule_id` LIKE 'CM\_SY\_%%'
   OR `rule_id` LIKE 'SP\_ID\_%%';

SELECT 'te_health_companion' AS table_schema, 'at_audit' AS table_name,
       'program_id' AS column_name, COUNT(*) AS invalid_domain_prefix_count
FROM `te_health_companion`.`at_audit`
WHERE `program_id` LIKE 'CM\_CM\_%%'
   OR `program_id` LIKE 'CM\_SY\_%%'
   OR `program_id` LIKE 'SP\_ID\_%%';

SELECT 'te_health_companion' AS table_schema, 'dc_decision' AS table_name,
       'user_id' AS column_name, COUNT(*) AS invalid_domain_prefix_count
FROM `te_health_companion`.`dc_decision`
WHERE `user_id` LIKE 'CM\_CM\_%%'
   OR `user_id` LIKE 'CM\_SY\_%%'
   OR `user_id` LIKE 'SP\_ID\_%%';

SELECT 'te_health_companion' AS table_schema, 'dc_decision' AS table_name,
       'rule_id' AS column_name, COUNT(*) AS invalid_domain_prefix_count
FROM `te_health_companion`.`dc_decision`
WHERE `rule_id` LIKE 'CM\_CM\_%%'
   OR `rule_id` LIKE 'CM\_SY\_%%'
   OR `rule_id` LIKE 'SP\_ID\_%%';

SELECT 'te_health_companion' AS table_schema, 'dc_decision' AS table_name,
       'program_id' AS column_name, COUNT(*) AS invalid_domain_prefix_count
FROM `te_health_companion`.`dc_decision`
WHERE `program_id` LIKE 'CM\_CM\_%%'
   OR `program_id` LIKE 'CM\_SY\_%%'
   OR `program_id` LIKE 'SP\_ID\_%%';

SELECT 'te_health_companion' AS table_schema, 'dc_decision_detail' AS table_name,
       'rule_id' AS column_name, COUNT(*) AS invalid_domain_prefix_count
FROM `te_health_companion`.`dc_decision_detail`
WHERE `rule_id` LIKE 'CM\_CM\_%%'
   OR `rule_id` LIKE 'CM\_SY\_%%'
   OR `rule_id` LIKE 'SP\_ID\_%%';

SELECT 'te_health_companion' AS table_schema, 'dc_decision_detail' AS table_name,
       'program_id' AS column_name, COUNT(*) AS invalid_domain_prefix_count
FROM `te_health_companion`.`dc_decision_detail`
WHERE `program_id` LIKE 'CM\_CM\_%%'
   OR `program_id` LIKE 'CM\_SY\_%%'
   OR `program_id` LIKE 'SP\_ID\_%%';

SELECT 'te_health_companion' AS table_schema, 'fb_feedback' AS table_name,
       'user_id' AS column_name, COUNT(*) AS invalid_domain_prefix_count
FROM `te_health_companion`.`fb_feedback`
WHERE `user_id` LIKE 'CM\_CM\_%%'
   OR `user_id` LIKE 'CM\_SY\_%%'
   OR `user_id` LIKE 'SP\_ID\_%%';

SELECT 'te_health_companion' AS table_schema, 'fb_feedback' AS table_name,
       'program_id' AS column_name, COUNT(*) AS invalid_domain_prefix_count
FROM `te_health_companion`.`fb_feedback`
WHERE `program_id` LIKE 'CM\_CM\_%%'
   OR `program_id` LIKE 'CM\_SY\_%%'
   OR `program_id` LIKE 'SP\_ID\_%%';

SELECT 'te_story_platform' AS table_schema, 'sp_identifier_blueprint' AS table_name,
       'blueprint_id' AS column_name, COUNT(*) AS invalid_domain_prefix_count
FROM `te_story_platform`.`sp_identifier_blueprint`
WHERE `blueprint_id` LIKE 'CM\_CM\_%%'
   OR `blueprint_id` LIKE 'CM\_SY\_%%'
   OR `blueprint_id` LIKE 'SP\_ID\_%%';

SELECT 'te_story_platform' AS table_schema, 'sp_identifier_blueprint' AS table_name,
       'program_id' AS column_name, COUNT(*) AS invalid_domain_prefix_count
FROM `te_story_platform`.`sp_identifier_blueprint`
WHERE `program_id` LIKE 'CM\_CM\_%%'
   OR `program_id` LIKE 'CM\_SY\_%%'
   OR `program_id` LIKE 'SP\_ID\_%%';

SELECT 'te_story_platform' AS table_schema, 'sp_identifier_sequence' AS table_name,
       'identifier_sequence_id' AS column_name, COUNT(*) AS invalid_domain_prefix_count
FROM `te_story_platform`.`sp_identifier_sequence`
WHERE `identifier_sequence_id` LIKE 'CM\_CM\_%%'
   OR `identifier_sequence_id` LIKE 'CM\_SY\_%%'
   OR `identifier_sequence_id` LIKE 'SP\_ID\_%%';

SELECT 'te_story_platform' AS table_schema, 'sp_identifier_sequence' AS table_name,
       'program_id' AS column_name, COUNT(*) AS invalid_domain_prefix_count
FROM `te_story_platform`.`sp_identifier_sequence`
WHERE `program_id` LIKE 'CM\_CM\_%%'
   OR `program_id` LIKE 'CM\_SY\_%%'
   OR `program_id` LIKE 'SP\_ID\_%%';

SELECT 'te_story_platform' AS table_schema, 'sp_impact_analysis_result' AS table_name,
       'program_id' AS column_name, COUNT(*) AS invalid_domain_prefix_count
FROM `te_story_platform`.`sp_impact_analysis_result`
WHERE `program_id` LIKE 'CM\_CM\_%%'
   OR `program_id` LIKE 'CM\_SY\_%%'
   OR `program_id` LIKE 'SP\_ID\_%%';

SELECT 'te_story_platform' AS table_schema, 'sp_knowledge_hold' AS table_name,
       'program_id' AS column_name, COUNT(*) AS invalid_domain_prefix_count
FROM `te_story_platform`.`sp_knowledge_hold`
WHERE `program_id` LIKE 'CM\_CM\_%%'
   OR `program_id` LIKE 'CM\_SY\_%%'
   OR `program_id` LIKE 'SP\_ID\_%%';

SELECT 'te_story_platform' AS table_schema, 'sp_knowledge_relationship_hold' AS table_name,
       'program_id' AS column_name, COUNT(*) AS invalid_domain_prefix_count
FROM `te_story_platform`.`sp_knowledge_relationship_hold`
WHERE `program_id` LIKE 'CM\_CM\_%%'
   OR `program_id` LIKE 'CM\_SY\_%%'
   OR `program_id` LIKE 'SP\_ID\_%%';

SELECT 'te_story_platform' AS table_schema, 'sp_metadata' AS table_name,
       'program_id' AS column_name, COUNT(*) AS invalid_domain_prefix_count
FROM `te_story_platform`.`sp_metadata`
WHERE `program_id` LIKE 'CM\_CM\_%%'
   OR `program_id` LIKE 'CM\_SY\_%%'
   OR `program_id` LIKE 'SP\_ID\_%%';

SELECT 'te_story_platform' AS table_schema, 'sp_object' AS table_name,
       'lifecycle_id' AS column_name, COUNT(*) AS invalid_domain_prefix_count
FROM `te_story_platform`.`sp_object`
WHERE `lifecycle_id` LIKE 'CM\_CM\_%%'
   OR `lifecycle_id` LIKE 'CM\_SY\_%%'
   OR `lifecycle_id` LIKE 'SP\_ID\_%%';

SELECT 'te_story_platform' AS table_schema, 'sp_object' AS table_name,
       'program_id' AS column_name, COUNT(*) AS invalid_domain_prefix_count
FROM `te_story_platform`.`sp_object`
WHERE `program_id` LIKE 'CM\_CM\_%%'
   OR `program_id` LIKE 'CM\_SY\_%%'
   OR `program_id` LIKE 'SP\_ID\_%%';

SELECT 'te_story_platform' AS table_schema, 'sp_object_lifecycle' AS table_name,
       'program_id' AS column_name, COUNT(*) AS invalid_domain_prefix_count
FROM `te_story_platform`.`sp_object_lifecycle`
WHERE `program_id` LIKE 'CM\_CM\_%%'
   OR `program_id` LIKE 'CM\_SY\_%%'
   OR `program_id` LIKE 'SP\_ID\_%%';

SELECT 'te_story_platform' AS table_schema, 'sp_relationship' AS table_name,
       'source_object_id' AS column_name, COUNT(*) AS invalid_domain_prefix_count
FROM `te_story_platform`.`sp_relationship`
WHERE `source_object_id` LIKE 'CM\_CM\_%%'
   OR `source_object_id` LIKE 'CM\_SY\_%%'
   OR `source_object_id` LIKE 'SP\_ID\_%%';

SELECT 'te_story_platform' AS table_schema, 'sp_relationship' AS table_name,
       'target_object_id' AS column_name, COUNT(*) AS invalid_domain_prefix_count
FROM `te_story_platform`.`sp_relationship`
WHERE `target_object_id` LIKE 'CM\_CM\_%%'
   OR `target_object_id` LIKE 'CM\_SY\_%%'
   OR `target_object_id` LIKE 'SP\_ID\_%%';

SELECT 'te_story_platform' AS table_schema, 'sp_relationship' AS table_name,
       'program_id' AS column_name, COUNT(*) AS invalid_domain_prefix_count
FROM `te_story_platform`.`sp_relationship`
WHERE `program_id` LIKE 'CM\_CM\_%%'
   OR `program_id` LIKE 'CM\_SY\_%%'
   OR `program_id` LIKE 'SP\_ID\_%%';

-- Roll back only the blanket Domain Code correction.
-- Restores live tables from immediate pre-correction backups.

SET @OLD_FOREIGN_KEY_CHECKS = @@FOREIGN_KEY_CHECKS;
SET FOREIGN_KEY_CHECKS = 0;

START TRANSACTION;

DELETE FROM `te_common`.`cm_audit_policy`;
INSERT INTO `te_common`.`cm_audit_policy` SELECT * FROM `te_common`.`cm_audit_policy_bkp_domain_20260721`;

DELETE FROM `te_common`.`cm_business_domain`;
INSERT INTO `te_common`.`cm_business_domain` SELECT * FROM `te_common`.`cm_business_domain_bkp_domain_20260721`;

DELETE FROM `te_common`.`cm_change_history`;
INSERT INTO `te_common`.`cm_change_history` SELECT * FROM `te_common`.`cm_change_history_bkp_domain_20260721`;

DELETE FROM `te_common`.`cm_common_code`;
INSERT INTO `te_common`.`cm_common_code` SELECT * FROM `te_common`.`cm_common_code_bkp_domain_20260721`;

DELETE FROM `te_common`.`cm_common_code_group`;
INSERT INTO `te_common`.`cm_common_code_group` SELECT * FROM `te_common`.`cm_common_code_group_bkp_domain_20260721`;

DELETE FROM `te_common`.`cm_legal_retention_policy`;
INSERT INTO `te_common`.`cm_legal_retention_policy` SELECT * FROM `te_common`.`cm_legal_retention_policy_bkp_domain_20260721`;

DELETE FROM `te_common`.`cm_member`;
INSERT INTO `te_common`.`cm_member` SELECT * FROM `te_common`.`cm_member_bkp_domain_20260721`;

DELETE FROM `te_common`.`cm_member_role`;
INSERT INTO `te_common`.`cm_member_role` SELECT * FROM `te_common`.`cm_member_role_bkp_domain_20260721`;

DELETE FROM `te_common`.`cm_repository`;
INSERT INTO `te_common`.`cm_repository` SELECT * FROM `te_common`.`cm_repository_bkp_domain_20260721`;

DELETE FROM `te_common`.`cm_role`;
INSERT INTO `te_common`.`cm_role` SELECT * FROM `te_common`.`cm_role_bkp_domain_20260721`;

DELETE FROM `te_common`.`cm_sequence_format`;
INSERT INTO `te_common`.`cm_sequence_format` SELECT * FROM `te_common`.`cm_sequence_format_bkp_domain_20260721`;

DELETE FROM `te_common`.`cm_sequence_policy`;
INSERT INTO `te_common`.`cm_sequence_policy` SELECT * FROM `te_common`.`cm_sequence_policy_bkp_domain_20260721`;

DELETE FROM `te_common`.`cm_sequence_rule`;
INSERT INTO `te_common`.`cm_sequence_rule` SELECT * FROM `te_common`.`cm_sequence_rule_bkp_domain_20260721`;

DELETE FROM `te_common`.`cm_storage_policy`;
INSERT INTO `te_common`.`cm_storage_policy` SELECT * FROM `te_common`.`cm_storage_policy_bkp_domain_20260721`;

DELETE FROM `te_common`.`cm_storage_repository`;
INSERT INTO `te_common`.`cm_storage_repository` SELECT * FROM `te_common`.`cm_storage_repository_bkp_domain_20260721`;

DELETE FROM `te_common`.`cm_verified_sql_query`;
INSERT INTO `te_common`.`cm_verified_sql_query` SELECT * FROM `te_common`.`cm_verified_sql_query_bkp_domain_20260721`;

DELETE FROM `te_common`.`rl_rule`;
INSERT INTO `te_common`.`rl_rule` SELECT * FROM `te_common`.`rl_rule_bkp_domain_20260721`;

DELETE FROM `te_common`.`rl_rule_action`;
INSERT INTO `te_common`.`rl_rule_action` SELECT * FROM `te_common`.`rl_rule_action_bkp_domain_20260721`;

DELETE FROM `te_common`.`rl_rule_condition`;
INSERT INTO `te_common`.`rl_rule_condition` SELECT * FROM `te_common`.`rl_rule_condition_bkp_domain_20260721`;

DELETE FROM `te_common`.`rl_rule_evidence`;
INSERT INTO `te_common`.`rl_rule_evidence` SELECT * FROM `te_common`.`rl_rule_evidence_bkp_domain_20260721`;

DELETE FROM `te_common`.`sp_policy_rule_candidate`;
INSERT INTO `te_common`.`sp_policy_rule_candidate` SELECT * FROM `te_common`.`sp_policy_rule_candidate_bkp_domain_20260721`;

DELETE FROM `te_common`.`system_menu_button`;
INSERT INTO `te_common`.`system_menu_button` SELECT * FROM `te_common`.`system_menu_button_bkp_domain_20260721`;

DELETE FROM `te_common`.`system_menu_button_crud_permission`;
INSERT INTO `te_common`.`system_menu_button_crud_permission` SELECT * FROM `te_common`.`system_menu_button_crud_permission_bkp_domain_20260721`;

DELETE FROM `te_common`.`system_user`;
INSERT INTO `te_common`.`system_user` SELECT * FROM `te_common`.`system_user_bkp_domain_20260721`;

DELETE FROM `te_health_companion`.`ac_action`;
INSERT INTO `te_health_companion`.`ac_action` SELECT * FROM `te_health_companion`.`ac_action_bkp_domain_20260721`;

DELETE FROM `te_health_companion`.`at_audit`;
INSERT INTO `te_health_companion`.`at_audit` SELECT * FROM `te_health_companion`.`at_audit_bkp_domain_20260721`;

DELETE FROM `te_health_companion`.`dc_decision`;
INSERT INTO `te_health_companion`.`dc_decision` SELECT * FROM `te_health_companion`.`dc_decision_bkp_domain_20260721`;

DELETE FROM `te_health_companion`.`dc_decision_detail`;
INSERT INTO `te_health_companion`.`dc_decision_detail` SELECT * FROM `te_health_companion`.`dc_decision_detail_bkp_domain_20260721`;

DELETE FROM `te_health_companion`.`fb_feedback`;
INSERT INTO `te_health_companion`.`fb_feedback` SELECT * FROM `te_health_companion`.`fb_feedback_bkp_domain_20260721`;

DELETE FROM `te_story_platform`.`sp_identifier_blueprint`;
INSERT INTO `te_story_platform`.`sp_identifier_blueprint` SELECT * FROM `te_story_platform`.`sp_identifier_blueprint_bkp_domain_20260721`;

DELETE FROM `te_story_platform`.`sp_identifier_sequence`;
INSERT INTO `te_story_platform`.`sp_identifier_sequence` SELECT * FROM `te_story_platform`.`sp_identifier_sequence_bkp_domain_20260721`;

DELETE FROM `te_story_platform`.`sp_impact_analysis_result`;
INSERT INTO `te_story_platform`.`sp_impact_analysis_result` SELECT * FROM `te_story_platform`.`sp_impact_analysis_result_bkp_domain_20260721`;

DELETE FROM `te_story_platform`.`sp_knowledge_hold`;
INSERT INTO `te_story_platform`.`sp_knowledge_hold` SELECT * FROM `te_story_platform`.`sp_knowledge_hold_bkp_domain_20260721`;

DELETE FROM `te_story_platform`.`sp_knowledge_relationship_hold`;
INSERT INTO `te_story_platform`.`sp_knowledge_relationship_hold` SELECT * FROM `te_story_platform`.`sp_knowledge_relationship_hold_bkp_domain_20260721`;

DELETE FROM `te_story_platform`.`sp_metadata`;
INSERT INTO `te_story_platform`.`sp_metadata` SELECT * FROM `te_story_platform`.`sp_metadata_bkp_domain_20260721`;

DELETE FROM `te_story_platform`.`sp_object`;
INSERT INTO `te_story_platform`.`sp_object` SELECT * FROM `te_story_platform`.`sp_object_bkp_domain_20260721`;

DELETE FROM `te_story_platform`.`sp_object_lifecycle`;
INSERT INTO `te_story_platform`.`sp_object_lifecycle` SELECT * FROM `te_story_platform`.`sp_object_lifecycle_bkp_domain_20260721`;

DELETE FROM `te_story_platform`.`sp_relationship`;
INSERT INTO `te_story_platform`.`sp_relationship` SELECT * FROM `te_story_platform`.`sp_relationship_bkp_domain_20260721`;

COMMIT;

SET FOREIGN_KEY_CHECKS = @OLD_FOREIGN_KEY_CHECKS;

SELECT COUNT(*) AS restored_backup_table_count
FROM information_schema.tables
WHERE table_schema IN ('te_common', 'te_health_companion', 'te_story_platform')
  AND table_name LIKE '%\\_bkp\\_domain\\_20260721';

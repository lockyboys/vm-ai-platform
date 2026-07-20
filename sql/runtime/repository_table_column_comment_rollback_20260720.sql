/*
File Name : repository_table_column_comment_rollback_20260720.sql
Purpose   : Restore TABLE/COLUMN COMMENT values captured before patch
Data Change: NONE
*/

SET NAMES utf8mb4;
SET FOREIGN_KEY_CHECKS = 0;

/* Drop affected Foreign Keys */
ALTER TABLE `te_common`.`cm_common_code` DROP FOREIGN KEY `fk_cm_common_code_group`;
ALTER TABLE `te_common`.`cm_locale` DROP FOREIGN KEY `fk_cm_locale_country`;
ALTER TABLE `te_common`.`cm_locale` DROP FOREIGN KEY `fk_cm_locale_language`;
ALTER TABLE `te_common`.`cm_login_history` DROP FOREIGN KEY `fk_cm_login_history_member`;
ALTER TABLE `te_common`.`cm_member_private` DROP FOREIGN KEY `fk_cm_member_private_member`;
ALTER TABLE `te_common`.`cm_member_role` DROP FOREIGN KEY `fk_cm_member_role_member`;
ALTER TABLE `te_common`.`cm_member_role` DROP FOREIGN KEY `fk_cm_member_role_role`;
ALTER TABLE `te_common`.`cm_role_rule` DROP FOREIGN KEY `fk_cm_role_rule_role`;
ALTER TABLE `te_common`.`cm_sequence_definition` DROP FOREIGN KEY `fk_cm_sequence_definition_format`;
ALTER TABLE `te_common`.`cm_sequence_definition` DROP FOREIGN KEY `fk_cm_sequence_definition_policy`;
ALTER TABLE `te_common`.`cm_sequence_rule` DROP FOREIGN KEY `fk_cm_sequence_rule_format`;
ALTER TABLE `te_common`.`cm_sequence_rule` DROP FOREIGN KEY `fk_cm_sequence_rule_policy`;
ALTER TABLE `te_common`.`md_object` DROP FOREIGN KEY `fk_md_object_type`;
ALTER TABLE `te_common`.`md_relation` DROP FOREIGN KEY `fk_md_relation_source`;
ALTER TABLE `te_common`.`md_relation` DROP FOREIGN KEY `fk_md_relation_target`;
ALTER TABLE `te_common`.`system_menu_button` DROP FOREIGN KEY `fk_system_menu_button_menu`;
ALTER TABLE `te_common`.`system_menu_button_crud_permission` DROP FOREIGN KEY `fk_button_permission_button`;
ALTER TABLE `te_common`.`system_menu_button_crud_permission` DROP FOREIGN KEY `fk_button_permission_menu`;
ALTER TABLE `te_story_platform`.`sp_knowledge_hold` DROP FOREIGN KEY `fk_sp_knowledge_type`;
ALTER TABLE `te_story_platform`.`sp_knowledge_relationship_hold` DROP FOREIGN KEY `fk_sp_knowledge_relationship_source`;
ALTER TABLE `te_story_platform`.`sp_knowledge_relationship_hold` DROP FOREIGN KEY `fk_sp_knowledge_relationship_target`;
ALTER TABLE `te_story_platform`.`sp_knowledge_type_hold` DROP FOREIGN KEY `fk_sp_knowledge_type_parent`;

/* te_common.system_user */
ALTER TABLE `te_common`.`system_user`
    MODIFY COLUMN `user_id` varchar(99) NOT NULL COMMENT '',
    MODIFY COLUMN `user_login_id` varchar(99) NOT NULL COMMENT '',
    MODIFY COLUMN `user_name` varchar(150) NOT NULL COMMENT '',
    MODIFY COLUMN `user_role_code` varchar(99) NOT NULL COMMENT '',
    MODIFY COLUMN `created_dt` datetime NOT NULL DEFAULT current_timestamp() COMMENT '',
    MODIFY COLUMN `updated_dt` datetime DEFAULT NULL COMMENT '',
    MODIFY COLUMN `created_by` varchar(99) NOT NULL DEFAULT 'SYSTEM' COMMENT '',
    MODIFY COLUMN `updated_by` varchar(99) DEFAULT NULL COMMENT '',
    MODIFY COLUMN `deleted_by` varchar(99) DEFAULT NULL COMMENT '',
    MODIFY COLUMN `deleted_dt` datetime DEFAULT NULL COMMENT '',
    MODIFY COLUMN `client_ip` varchar(99) DEFAULT NULL COMMENT '',
    MODIFY COLUMN `program_id` varchar(99) DEFAULT NULL COMMENT '',
    MODIFY COLUMN `status_code` varchar(99) NOT NULL DEFAULT 'ACTIVE' COMMENT '',
    COMMENT = '';

/* te_common.system_menu_button_crud_permission */
ALTER TABLE `te_common`.`system_menu_button_crud_permission`
    MODIFY COLUMN `permission_id` varchar(99) NOT NULL COMMENT '',
    MODIFY COLUMN `menu_code` varchar(99) NOT NULL COMMENT '',
    MODIFY COLUMN `button_code` varchar(99) NOT NULL COMMENT '',
    MODIFY COLUMN `user_role_code` varchar(99) NOT NULL COMMENT '',
    MODIFY COLUMN `can_create_yn` char(1) NOT NULL DEFAULT 'N' COMMENT '',
    MODIFY COLUMN `can_read_yn` char(1) NOT NULL DEFAULT 'N' COMMENT '',
    MODIFY COLUMN `can_update_yn` char(1) NOT NULL DEFAULT 'N' COMMENT '',
    MODIFY COLUMN `can_delete_yn` char(1) NOT NULL DEFAULT 'N' COMMENT '',
    MODIFY COLUMN `can_alter_yn` char(1) NOT NULL DEFAULT 'N' COMMENT '',
    MODIFY COLUMN `created_dt` datetime NOT NULL DEFAULT current_timestamp() COMMENT '',
    MODIFY COLUMN `updated_dt` datetime DEFAULT NULL COMMENT '',
    MODIFY COLUMN `created_by` varchar(99) NOT NULL DEFAULT 'SYSTEM' COMMENT '',
    MODIFY COLUMN `updated_by` varchar(99) DEFAULT NULL COMMENT '',
    MODIFY COLUMN `deleted_by` varchar(99) DEFAULT NULL COMMENT '',
    MODIFY COLUMN `deleted_dt` datetime DEFAULT NULL COMMENT '',
    MODIFY COLUMN `client_ip` varchar(99) DEFAULT NULL COMMENT '',
    MODIFY COLUMN `program_id` varchar(99) DEFAULT NULL COMMENT '',
    MODIFY COLUMN `status_code` varchar(99) NOT NULL DEFAULT 'ACTIVE' COMMENT '',
    COMMENT = '';

/* te_common.system_menu_button */
ALTER TABLE `te_common`.`system_menu_button`
    MODIFY COLUMN `button_code` varchar(99) NOT NULL COMMENT '',
    MODIFY COLUMN `menu_code` varchar(99) NOT NULL COMMENT '',
    MODIFY COLUMN `button_name` varchar(150) NOT NULL COMMENT '',
    MODIFY COLUMN `crud_type` varchar(99) NOT NULL COMMENT '',
    MODIFY COLUMN `query_id` varchar(99) NOT NULL COMMENT '',
    MODIFY COLUMN `button_sort_no` int(11) NOT NULL DEFAULT 0 COMMENT '',
    MODIFY COLUMN `created_dt` datetime NOT NULL DEFAULT current_timestamp() COMMENT '',
    MODIFY COLUMN `updated_dt` datetime DEFAULT NULL COMMENT '',
    MODIFY COLUMN `created_by` varchar(99) NOT NULL DEFAULT 'SYSTEM' COMMENT '',
    MODIFY COLUMN `updated_by` varchar(99) DEFAULT NULL COMMENT '',
    MODIFY COLUMN `deleted_by` varchar(99) DEFAULT NULL COMMENT '',
    MODIFY COLUMN `deleted_dt` datetime DEFAULT NULL COMMENT '',
    MODIFY COLUMN `client_ip` varchar(99) DEFAULT NULL COMMENT '',
    MODIFY COLUMN `program_id` varchar(99) DEFAULT NULL COMMENT '',
    MODIFY COLUMN `status_code` varchar(99) NOT NULL DEFAULT 'ACTIVE' COMMENT '',
    COMMENT = '';

/* te_common.system_menu */
ALTER TABLE `te_common`.`system_menu`
    MODIFY COLUMN `menu_code` varchar(99) NOT NULL COMMENT '',
    MODIFY COLUMN `menu_name` varchar(150) NOT NULL COMMENT '',
    MODIFY COLUMN `menu_url` varchar(2000) DEFAULT NULL COMMENT '',
    MODIFY COLUMN `menu_sort_no` int(11) NOT NULL DEFAULT 0 COMMENT '',
    MODIFY COLUMN `created_dt` datetime NOT NULL DEFAULT current_timestamp() COMMENT '',
    MODIFY COLUMN `updated_dt` datetime DEFAULT NULL COMMENT '',
    MODIFY COLUMN `created_by` varchar(99) NOT NULL DEFAULT 'SYSTEM' COMMENT '',
    MODIFY COLUMN `updated_by` varchar(99) DEFAULT NULL COMMENT '',
    MODIFY COLUMN `deleted_by` varchar(99) DEFAULT NULL COMMENT '',
    MODIFY COLUMN `deleted_dt` datetime DEFAULT NULL COMMENT '',
    MODIFY COLUMN `client_ip` varchar(99) DEFAULT NULL COMMENT '',
    MODIFY COLUMN `program_id` varchar(99) DEFAULT NULL COMMENT '',
    MODIFY COLUMN `status_code` varchar(99) NOT NULL DEFAULT 'ACTIVE' COMMENT '',
    COMMENT = '';

/* te_common.sql_guard_verification_log */
ALTER TABLE `te_common`.`sql_guard_verification_log`
    MODIFY COLUMN `log_id` varchar(99) NOT NULL COMMENT '',
    MODIFY COLUMN `query_id` varchar(99) DEFAULT NULL COMMENT '',
    MODIFY COLUMN `check_step` varchar(99) NOT NULL COMMENT '',
    MODIFY COLUMN `pass_yn` char(1) NOT NULL COMMENT '',
    MODIFY COLUMN `message` text DEFAULT NULL COMMENT '',
    MODIFY COLUMN `created_dt` datetime NOT NULL DEFAULT current_timestamp() COMMENT '',
    MODIFY COLUMN `created_by` varchar(99) NOT NULL DEFAULT 'SYSTEM' COMMENT '',
    MODIFY COLUMN `updated_by` varchar(99) DEFAULT NULL COMMENT '',
    MODIFY COLUMN `updated_dt` datetime DEFAULT NULL COMMENT '',
    MODIFY COLUMN `deleted_by` varchar(99) DEFAULT NULL COMMENT '',
    MODIFY COLUMN `deleted_dt` datetime DEFAULT NULL COMMENT '',
    MODIFY COLUMN `change_story` varchar(2000) DEFAULT NULL COMMENT '',
    MODIFY COLUMN `client_ip` varchar(99) DEFAULT NULL COMMENT '',
    MODIFY COLUMN `program_id` varchar(99) DEFAULT NULL COMMENT '',
    MODIFY COLUMN `status_code` varchar(99) NOT NULL DEFAULT 'ACTIVE' COMMENT '',
    COMMENT = '';

/* te_common.sql_guard_execution_log */
ALTER TABLE `te_common`.`sql_guard_execution_log`
    MODIFY COLUMN `execution_id` varchar(99) NOT NULL COMMENT '',
    MODIFY COLUMN `user_id` varchar(99) NOT NULL COMMENT '',
    MODIFY COLUMN `menu_code` varchar(99) NOT NULL COMMENT '',
    MODIFY COLUMN `button_code` varchar(99) NOT NULL COMMENT '',
    MODIFY COLUMN `query_id` varchar(99) NOT NULL COMMENT '',
    MODIFY COLUMN `crud_type` varchar(99) NOT NULL COMMENT '',
    MODIFY COLUMN `success_yn` char(1) NOT NULL COMMENT '',
    MODIFY COLUMN `row_count` int(11) DEFAULT NULL COMMENT '',
    MODIFY COLUMN `error_message` text DEFAULT NULL COMMENT '',
    MODIFY COLUMN `executed_dt` datetime NOT NULL DEFAULT current_timestamp() COMMENT '',
    MODIFY COLUMN `status_code` varchar(99) NOT NULL DEFAULT 'ACTIVE' COMMENT '',
    COMMENT = '';

/* te_common.sp_policy_rule_keyword */
ALTER TABLE `te_common`.`sp_policy_rule_keyword`
    MODIFY COLUMN `rule_keyword_id` varchar(99) NOT NULL COMMENT '',
    MODIFY COLUMN `rule_keyword_text` text NOT NULL COMMENT '',
    MODIFY COLUMN `rule_keyword_category_code` varchar(99) NOT NULL COMMENT '',
    MODIFY COLUMN `rule_keyword_description` varchar(2000) DEFAULT NULL COMMENT '',
    MODIFY COLUMN `use_yn` char(1) NOT NULL DEFAULT 'Y' COMMENT '',
    MODIFY COLUMN `created_by` varchar(99) NOT NULL DEFAULT 'SYSTEM' COMMENT '',
    MODIFY COLUMN `created_dt` datetime NOT NULL DEFAULT current_timestamp() COMMENT '',
    MODIFY COLUMN `updated_by` varchar(99) DEFAULT NULL COMMENT '',
    MODIFY COLUMN `updated_dt` datetime DEFAULT NULL COMMENT '',
    MODIFY COLUMN `deleted_yn` char(1) NOT NULL DEFAULT 'N' COMMENT '',
    MODIFY COLUMN `deleted_by` varchar(99) DEFAULT NULL COMMENT '',
    MODIFY COLUMN `deleted_dt` datetime DEFAULT NULL COMMENT '',
    MODIFY COLUMN `change_reason` varchar(2000) DEFAULT NULL COMMENT '',
    MODIFY COLUMN `client_ip` varchar(99) DEFAULT NULL COMMENT '',
    MODIFY COLUMN `program_id` varchar(99) DEFAULT NULL COMMENT '',
    COMMENT = '';

/* te_common.sp_policy_rule_candidate */
ALTER TABLE `te_common`.`sp_policy_rule_candidate`
    MODIFY COLUMN `rule_candidate_id` varchar(99) NOT NULL COMMENT '',
    MODIFY COLUMN `policy_id` varchar(99) DEFAULT NULL COMMENT '',
    MODIFY COLUMN `source_document_name` varchar(150) DEFAULT NULL COMMENT '',
    MODIFY COLUMN `source_page_no` int(11) DEFAULT NULL COMMENT '',
    MODIFY COLUMN `source_sentence_text` text NOT NULL COMMENT '',
    MODIFY COLUMN `matched_keyword_text` text DEFAULT NULL COMMENT '',
    MODIFY COLUMN `rule_candidate_category_code` varchar(99) DEFAULT NULL COMMENT '',
    MODIFY COLUMN `confidence_score` decimal(10,4) DEFAULT 0.0000 COMMENT '',
    MODIFY COLUMN `confirm_yn` char(1) NOT NULL DEFAULT 'N' COMMENT '',
    MODIFY COLUMN `use_yn` char(1) NOT NULL DEFAULT 'Y' COMMENT '',
    MODIFY COLUMN `created_by` varchar(99) NOT NULL DEFAULT 'SYSTEM' COMMENT '',
    MODIFY COLUMN `created_dt` datetime NOT NULL DEFAULT current_timestamp() COMMENT '',
    MODIFY COLUMN `updated_by` varchar(99) DEFAULT NULL COMMENT '',
    MODIFY COLUMN `updated_dt` datetime DEFAULT NULL COMMENT '',
    MODIFY COLUMN `deleted_yn` char(1) NOT NULL DEFAULT 'N' COMMENT '',
    MODIFY COLUMN `deleted_by` varchar(99) DEFAULT NULL COMMENT '',
    MODIFY COLUMN `deleted_dt` datetime DEFAULT NULL COMMENT '',
    MODIFY COLUMN `change_reason` varchar(2000) DEFAULT NULL COMMENT '',
    MODIFY COLUMN `client_ip` varchar(99) DEFAULT NULL COMMENT '',
    MODIFY COLUMN `program_id` varchar(99) DEFAULT NULL COMMENT '',
    COMMENT = '';

/* te_common.rl_rule_evidence */
ALTER TABLE `te_common`.`rl_rule_evidence`
    MODIFY COLUMN `created_dt` datetime NOT NULL DEFAULT current_timestamp() COMMENT '',
    MODIFY COLUMN `created_by` varchar(99) NOT NULL DEFAULT 'SYSTEM' COMMENT '',
    MODIFY COLUMN `updated_dt` datetime NOT NULL DEFAULT current_timestamp() ON UPDATE current_timestamp() COMMENT '',
    MODIFY COLUMN `updated_by` varchar(99) NOT NULL DEFAULT 'SYSTEM' COMMENT '',
    MODIFY COLUMN `deleted_by` varchar(99) DEFAULT NULL COMMENT '',
    MODIFY COLUMN `deleted_dt` datetime DEFAULT NULL COMMENT '',
    MODIFY COLUMN `program_id` varchar(99) DEFAULT NULL COMMENT '',
    MODIFY COLUMN `client_ip` varchar(99) DEFAULT NULL COMMENT '',
    MODIFY COLUMN `status_code` varchar(99) NOT NULL DEFAULT 'ACTIVE' COMMENT '',
    COMMENT = '업무 규칙 근거 연결';

/* te_common.rl_rule_condition */
ALTER TABLE `te_common`.`rl_rule_condition`
    MODIFY COLUMN `field_code` varchar(99) NOT NULL COMMENT '대상 필드 코드',
    MODIFY COLUMN `operator_code` varchar(99) NOT NULL COMMENT '연산자 코드',
    MODIFY COLUMN `logical_operator_code` varchar(99) DEFAULT NULL COMMENT '논리 연산자 코드',
    MODIFY COLUMN `created_dt` datetime NOT NULL DEFAULT current_timestamp() COMMENT '',
    MODIFY COLUMN `created_by` varchar(99) NOT NULL DEFAULT 'SYSTEM' COMMENT '',
    MODIFY COLUMN `updated_dt` datetime NOT NULL DEFAULT current_timestamp() ON UPDATE current_timestamp() COMMENT '',
    MODIFY COLUMN `updated_by` varchar(99) NOT NULL DEFAULT 'SYSTEM' COMMENT '',
    MODIFY COLUMN `deleted_by` varchar(99) DEFAULT NULL COMMENT '',
    MODIFY COLUMN `deleted_dt` datetime DEFAULT NULL COMMENT '',
    MODIFY COLUMN `program_id` varchar(99) DEFAULT NULL COMMENT '',
    MODIFY COLUMN `client_ip` varchar(99) DEFAULT NULL COMMENT '',
    MODIFY COLUMN `status_code` varchar(99) NOT NULL DEFAULT 'ACTIVE' COMMENT '',
    COMMENT = '업무 규칙 조건';

/* te_common.rl_rule_action */
ALTER TABLE `te_common`.`rl_rule_action`
    MODIFY COLUMN `action_type_code` varchar(99) NOT NULL COMMENT '실행 유형 코드',
    MODIFY COLUMN `created_dt` datetime NOT NULL DEFAULT current_timestamp() COMMENT '',
    MODIFY COLUMN `created_by` varchar(99) NOT NULL DEFAULT 'SYSTEM' COMMENT '',
    MODIFY COLUMN `updated_dt` datetime NOT NULL DEFAULT current_timestamp() ON UPDATE current_timestamp() COMMENT '',
    MODIFY COLUMN `updated_by` varchar(99) NOT NULL DEFAULT 'SYSTEM' COMMENT '',
    MODIFY COLUMN `deleted_by` varchar(99) DEFAULT NULL COMMENT '',
    MODIFY COLUMN `deleted_dt` datetime DEFAULT NULL COMMENT '',
    MODIFY COLUMN `program_id` varchar(99) DEFAULT NULL COMMENT '',
    MODIFY COLUMN `client_ip` varchar(99) DEFAULT NULL COMMENT '',
    MODIFY COLUMN `status_code` varchar(99) NOT NULL DEFAULT 'ACTIVE' COMMENT '',
    COMMENT = '업무 규칙 실행';

/* te_common.rl_rule */
ALTER TABLE `te_common`.`rl_rule`
    MODIFY COLUMN `rule_code` varchar(99) NOT NULL COMMENT '규칙 코드',
    MODIFY COLUMN `rule_type_code` varchar(99) NOT NULL COMMENT '규칙 유형 코드',
    MODIFY COLUMN `rule_group_code` varchar(99) DEFAULT NULL COMMENT '규칙 그룹 코드',
    MODIFY COLUMN `status_code` varchar(99) NOT NULL DEFAULT 'ACTIVE' COMMENT '상태 코드',
    MODIFY COLUMN `version_num` varchar(99) DEFAULT NULL COMMENT '',
    MODIFY COLUMN `created_dt` datetime NOT NULL DEFAULT current_timestamp() COMMENT '',
    MODIFY COLUMN `created_by` varchar(99) NOT NULL DEFAULT 'SYSTEM' COMMENT '',
    MODIFY COLUMN `updated_dt` datetime NOT NULL DEFAULT current_timestamp() ON UPDATE current_timestamp() COMMENT '',
    MODIFY COLUMN `updated_by` varchar(99) NOT NULL DEFAULT 'SYSTEM' COMMENT '',
    MODIFY COLUMN `deleted_by` varchar(99) DEFAULT NULL COMMENT '',
    MODIFY COLUMN `deleted_dt` datetime DEFAULT NULL COMMENT '',
    MODIFY COLUMN `program_id` varchar(99) DEFAULT NULL COMMENT '',
    MODIFY COLUMN `client_ip` varchar(99) DEFAULT NULL COMMENT '',
    COMMENT = '업무 규칙';

/* te_common.md_relation */
ALTER TABLE `te_common`.`md_relation`
    MODIFY COLUMN `md_relation_id` varchar(99) NOT NULL COMMENT '',
    MODIFY COLUMN `source_md_object_id` varchar(99) NOT NULL COMMENT '',
    MODIFY COLUMN `target_md_object_id` varchar(99) NOT NULL COMMENT '',
    MODIFY COLUMN `relation_type_code` varchar(99) NOT NULL COMMENT '',
    MODIFY COLUMN `direction_code` varchar(99) NOT NULL DEFAULT 'UNI' COMMENT '',
    MODIFY COLUMN `cardinality_code` varchar(99) NOT NULL DEFAULT 'N:N' COMMENT '',
    MODIFY COLUMN `description` varchar(2000) DEFAULT NULL COMMENT '',
    MODIFY COLUMN `sort_no` int(11) NOT NULL DEFAULT 0 COMMENT '',
    MODIFY COLUMN `status_code` varchar(99) NOT NULL DEFAULT 'ACTIVE' COMMENT '',
    MODIFY COLUMN `created_dt` datetime NOT NULL DEFAULT current_timestamp() COMMENT '',
    MODIFY COLUMN `created_by` varchar(99) NOT NULL DEFAULT 'SYSTEM' COMMENT '',
    MODIFY COLUMN `updated_dt` datetime NOT NULL DEFAULT current_timestamp() ON UPDATE current_timestamp() COMMENT '',
    MODIFY COLUMN `updated_by` varchar(99) NOT NULL DEFAULT 'SYSTEM' COMMENT '',
    MODIFY COLUMN `deleted_by` varchar(99) DEFAULT NULL COMMENT '',
    MODIFY COLUMN `deleted_dt` datetime DEFAULT NULL COMMENT '',
    MODIFY COLUMN `client_ip` varchar(99) DEFAULT NULL COMMENT '',
    MODIFY COLUMN `program_id` varchar(99) DEFAULT NULL COMMENT '',
    COMMENT = '';

/* te_common.md_object */
ALTER TABLE `te_common`.`md_object`
    MODIFY COLUMN `md_object_id` varchar(99) NOT NULL COMMENT '',
    MODIFY COLUMN `object_type_group_code` varchar(99) NOT NULL DEFAULT 'OBJECT_TYPE' COMMENT '',
    MODIFY COLUMN `object_type_code` varchar(99) NOT NULL COMMENT '',
    MODIFY COLUMN `object_code` varchar(99) NOT NULL COMMENT '',
    MODIFY COLUMN `object_name` varchar(150) NOT NULL COMMENT '',
    MODIFY COLUMN `description` varchar(2000) DEFAULT NULL COMMENT '',
    MODIFY COLUMN `attribute_json` longtext CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '' CHECK (json_valid(`attribute_json`)),
    MODIFY COLUMN `sort_no` int(11) NOT NULL DEFAULT 0 COMMENT '',
    MODIFY COLUMN `status_code` varchar(99) NOT NULL DEFAULT 'ACTIVE' COMMENT '',
    MODIFY COLUMN `created_dt` datetime NOT NULL DEFAULT current_timestamp() COMMENT '',
    MODIFY COLUMN `created_by` varchar(99) NOT NULL DEFAULT 'SYSTEM' COMMENT '',
    MODIFY COLUMN `updated_dt` datetime NOT NULL DEFAULT current_timestamp() ON UPDATE current_timestamp() COMMENT '',
    MODIFY COLUMN `updated_by` varchar(99) NOT NULL DEFAULT 'SYSTEM' COMMENT '',
    MODIFY COLUMN `deleted_by` varchar(99) DEFAULT NULL COMMENT '',
    MODIFY COLUMN `deleted_dt` datetime DEFAULT NULL COMMENT '',
    MODIFY COLUMN `client_ip` varchar(99) DEFAULT NULL COMMENT '',
    MODIFY COLUMN `program_id` varchar(99) DEFAULT NULL COMMENT '',
    COMMENT = '';

/* te_common.health_report */
ALTER TABLE `te_common`.`health_report`
    MODIFY COLUMN `health_report_id` varchar(99) NOT NULL COMMENT '',
    MODIFY COLUMN `patient_id` varchar(99) NOT NULL COMMENT '',
    MODIFY COLUMN `report_title` varchar(500) NOT NULL COMMENT '',
    MODIFY COLUMN `report_content` text DEFAULT NULL COMMENT '',
    MODIFY COLUMN `created_dt` datetime NOT NULL DEFAULT current_timestamp() COMMENT '',
    MODIFY COLUMN `updated_dt` datetime DEFAULT NULL COMMENT '',
    MODIFY COLUMN `created_by` varchar(99) NOT NULL DEFAULT 'SYSTEM' COMMENT '',
    MODIFY COLUMN `updated_by` varchar(99) DEFAULT NULL COMMENT '',
    MODIFY COLUMN `deleted_by` varchar(99) DEFAULT NULL COMMENT '',
    MODIFY COLUMN `deleted_dt` datetime DEFAULT NULL COMMENT '',
    MODIFY COLUMN `change_story` varchar(2000) DEFAULT NULL COMMENT '',
    MODIFY COLUMN `client_ip` varchar(99) DEFAULT NULL COMMENT '',
    MODIFY COLUMN `program_id` varchar(99) DEFAULT NULL COMMENT '',
    MODIFY COLUMN `status_code` varchar(99) NOT NULL DEFAULT 'ACTIVE' COMMENT '',
    COMMENT = '';

/* te_common.ev_evidence_version */
ALTER TABLE `te_common`.`ev_evidence_version`
    MODIFY COLUMN `version_num` varchar(99) DEFAULT NULL COMMENT '',
    MODIFY COLUMN `created_dt` datetime NOT NULL DEFAULT current_timestamp() COMMENT '',
    MODIFY COLUMN `created_by` varchar(99) NOT NULL DEFAULT 'SYSTEM' COMMENT '',
    MODIFY COLUMN `updated_dt` datetime NOT NULL DEFAULT current_timestamp() ON UPDATE current_timestamp() COMMENT '',
    MODIFY COLUMN `updated_by` varchar(99) NOT NULL DEFAULT 'SYSTEM' COMMENT '',
    MODIFY COLUMN `deleted_by` varchar(99) DEFAULT NULL COMMENT '',
    MODIFY COLUMN `deleted_dt` datetime DEFAULT NULL COMMENT '',
    MODIFY COLUMN `program_id` varchar(99) DEFAULT NULL COMMENT '',
    MODIFY COLUMN `client_ip` varchar(99) DEFAULT NULL COMMENT '',
    MODIFY COLUMN `status_code` varchar(99) NOT NULL DEFAULT 'ACTIVE' COMMENT '',
    COMMENT = '근거 버전';

/* te_common.ev_evidence_reference */
ALTER TABLE `te_common`.`ev_evidence_reference`
    MODIFY COLUMN `reference_type_code` varchar(99) NOT NULL COMMENT '참조 유형 코드',
    MODIFY COLUMN `created_dt` datetime NOT NULL DEFAULT current_timestamp() COMMENT '',
    MODIFY COLUMN `created_by` varchar(99) NOT NULL DEFAULT 'SYSTEM' COMMENT '',
    MODIFY COLUMN `updated_dt` datetime NOT NULL DEFAULT current_timestamp() ON UPDATE current_timestamp() COMMENT '',
    MODIFY COLUMN `updated_by` varchar(99) NOT NULL DEFAULT 'SYSTEM' COMMENT '',
    MODIFY COLUMN `deleted_by` varchar(99) DEFAULT NULL COMMENT '',
    MODIFY COLUMN `deleted_dt` datetime DEFAULT NULL COMMENT '',
    MODIFY COLUMN `program_id` varchar(99) DEFAULT NULL COMMENT '',
    MODIFY COLUMN `client_ip` varchar(99) DEFAULT NULL COMMENT '',
    MODIFY COLUMN `status_code` varchar(99) NOT NULL DEFAULT 'ACTIVE' COMMENT '',
    COMMENT = '근거 참조';

/* te_common.ev_evidence */
ALTER TABLE `te_common`.`ev_evidence`
    MODIFY COLUMN `evidence_code` varchar(99) NOT NULL COMMENT '근거 코드',
    MODIFY COLUMN `evidence_level_code` varchar(99) NOT NULL COMMENT '근거수준 A/B/C/D',
    MODIFY COLUMN `evidence_category_code` varchar(99) NOT NULL COMMENT '근거 분류 코드',
    MODIFY COLUMN `version_num` varchar(99) DEFAULT NULL COMMENT '',
    MODIFY COLUMN `status_code` varchar(99) NOT NULL DEFAULT 'ACTIVE' COMMENT '상태 코드',
    MODIFY COLUMN `created_dt` datetime NOT NULL DEFAULT current_timestamp() COMMENT '',
    MODIFY COLUMN `created_by` varchar(99) NOT NULL DEFAULT 'SYSTEM' COMMENT '',
    MODIFY COLUMN `updated_dt` datetime NOT NULL DEFAULT current_timestamp() ON UPDATE current_timestamp() COMMENT '',
    MODIFY COLUMN `updated_by` varchar(99) NOT NULL DEFAULT 'SYSTEM' COMMENT '',
    MODIFY COLUMN `deleted_by` varchar(99) DEFAULT NULL COMMENT '',
    MODIFY COLUMN `deleted_dt` datetime DEFAULT NULL COMMENT '',
    MODIFY COLUMN `program_id` varchar(99) DEFAULT NULL COMMENT '',
    MODIFY COLUMN `client_ip` varchar(99) DEFAULT NULL COMMENT '',
    COMMENT = '근거';

/* te_common.cm_verified_sql_query */
ALTER TABLE `te_common`.`cm_verified_sql_query`
    MODIFY COLUMN `query_id` varchar(99) NOT NULL COMMENT '',
    MODIFY COLUMN `query_name` varchar(150) NOT NULL COMMENT '',
    MODIFY COLUMN `crud_type` varchar(99) NOT NULL COMMENT '',
    MODIFY COLUMN `sql_text` text NOT NULL COMMENT '',
    MODIFY COLUMN `verified_yn` char(1) NOT NULL DEFAULT 'N' COMMENT '',
    MODIFY COLUMN `certified_level_code` varchar(99) DEFAULT NULL COMMENT '검증 인증 수준 코드',
    MODIFY COLUMN `created_by` varchar(99) DEFAULT NULL COMMENT '',
    MODIFY COLUMN `created_dt` datetime NOT NULL DEFAULT current_timestamp() COMMENT '',
    MODIFY COLUMN `verified_by` varchar(99) DEFAULT NULL COMMENT '',
    MODIFY COLUMN `updated_dt` datetime DEFAULT NULL COMMENT '',
    MODIFY COLUMN `deleted_dt` datetime DEFAULT NULL COMMENT '',
    MODIFY COLUMN `status_code` varchar(99) NOT NULL DEFAULT 'ACTIVE' COMMENT '',
    COMMENT = '검증이 완료된 SQL Query Object를 관리하는 공통 Repository';

/* te_common.cm_storage_repository */
ALTER TABLE `te_common`.`cm_storage_repository`
    MODIFY COLUMN `created_dt` datetime DEFAULT current_timestamp() COMMENT '',
    MODIFY COLUMN `updated_dt` datetime DEFAULT current_timestamp() ON UPDATE current_timestamp() COMMENT '',
    MODIFY COLUMN `created_by` varchar(99) NOT NULL DEFAULT 'SYSTEM' COMMENT '',
    MODIFY COLUMN `updated_by` varchar(99) DEFAULT NULL COMMENT '',
    MODIFY COLUMN `deleted_by` varchar(99) DEFAULT NULL COMMENT '',
    MODIFY COLUMN `deleted_dt` datetime DEFAULT NULL COMMENT '',
    MODIFY COLUMN `change_story` varchar(2000) DEFAULT NULL COMMENT '',
    MODIFY COLUMN `client_ip` varchar(99) DEFAULT NULL COMMENT '',
    MODIFY COLUMN `program_id` varchar(99) DEFAULT NULL COMMENT '',
    MODIFY COLUMN `status_code` varchar(99) NOT NULL DEFAULT 'ACTIVE' COMMENT '',
    COMMENT = '저장소 관리';

/* te_common.cm_storage_policy */
ALTER TABLE `te_common`.`cm_storage_policy`
    MODIFY COLUMN `policy_id` varchar(99) NOT NULL COMMENT '',
    MODIFY COLUMN `created_dt` datetime DEFAULT current_timestamp() COMMENT '',
    MODIFY COLUMN `updated_dt` datetime DEFAULT current_timestamp() ON UPDATE current_timestamp() COMMENT '',
    MODIFY COLUMN `created_by` varchar(99) NOT NULL DEFAULT 'SYSTEM' COMMENT '',
    MODIFY COLUMN `updated_by` varchar(99) DEFAULT NULL COMMENT '',
    MODIFY COLUMN `deleted_by` varchar(99) DEFAULT NULL COMMENT '',
    MODIFY COLUMN `deleted_dt` datetime DEFAULT NULL COMMENT '',
    MODIFY COLUMN `change_story` varchar(2000) DEFAULT NULL COMMENT '',
    MODIFY COLUMN `client_ip` varchar(99) DEFAULT NULL COMMENT '',
    MODIFY COLUMN `program_id` varchar(99) DEFAULT NULL COMMENT '',
    MODIFY COLUMN `status_code` varchar(99) NOT NULL DEFAULT 'ACTIVE' COMMENT '',
    COMMENT = '데이터 저장 정책';

/* te_common.cm_sequence_rule */
ALTER TABLE `te_common`.`cm_sequence_rule`
    MODIFY COLUMN `sequence_code` varchar(99) NOT NULL COMMENT '시퀀스 코드',
    MODIFY COLUMN `classification_code` varchar(99) DEFAULT NULL COMMENT '분류 코드',
    MODIFY COLUMN `domain_code` varchar(99) DEFAULT NULL COMMENT '도메인 코드',
    MODIFY COLUMN `work_type_code` varchar(99) DEFAULT NULL COMMENT '업무유형 코드',
    MODIFY COLUMN `policy_code` varchar(99) NOT NULL COMMENT '초기화 정책 코드',
    MODIFY COLUMN `format_code` varchar(99) NOT NULL COMMENT '포맷 코드',
    MODIFY COLUMN `prefix_code` varchar(99) DEFAULT NULL COMMENT 'Prefix 코드',
    MODIFY COLUMN `created_dt` datetime NOT NULL DEFAULT current_timestamp() COMMENT '',
    MODIFY COLUMN `updated_dt` datetime NOT NULL DEFAULT current_timestamp() ON UPDATE current_timestamp() COMMENT '',
    MODIFY COLUMN `created_by` varchar(99) NOT NULL DEFAULT 'SYSTEM' COMMENT '',
    MODIFY COLUMN `updated_by` varchar(99) DEFAULT NULL COMMENT '',
    MODIFY COLUMN `deleted_by` varchar(99) DEFAULT NULL COMMENT '',
    MODIFY COLUMN `deleted_dt` datetime DEFAULT NULL COMMENT '',
    MODIFY COLUMN `client_ip` varchar(99) DEFAULT NULL COMMENT '',
    MODIFY COLUMN `program_id` varchar(99) DEFAULT NULL COMMENT '',
    MODIFY COLUMN `status_code` varchar(99) NOT NULL DEFAULT 'ACTIVE' COMMENT '',
    COMMENT = 'SPS 시퀀스 생성 규칙 메타데이터';

/* te_common.cm_sequence_policy_definition */
ALTER TABLE `te_common`.`cm_sequence_policy_definition`
    MODIFY COLUMN `policy_code` varchar(99) NOT NULL COMMENT '시퀀스 정책 코드',
    MODIFY COLUMN `sequence_date_rule_code` varchar(99) NOT NULL COMMENT '00000000/YYYY0000/YYYYMM00/YYYYMMDD',
    MODIFY COLUMN `sort_no` int(11) NOT NULL DEFAULT 0 COMMENT '',
    MODIFY COLUMN `status_code` varchar(99) NOT NULL DEFAULT 'ACTIVE' COMMENT '',
    MODIFY COLUMN `created_dt` datetime NOT NULL DEFAULT current_timestamp() COMMENT '',
    MODIFY COLUMN `created_by` varchar(99) NOT NULL DEFAULT 'SYSTEM' COMMENT '',
    MODIFY COLUMN `updated_dt` datetime NOT NULL DEFAULT current_timestamp() ON UPDATE current_timestamp() COMMENT '',
    MODIFY COLUMN `updated_by` varchar(99) NOT NULL DEFAULT 'SYSTEM' COMMENT '',
    MODIFY COLUMN `client_ip` varchar(99) DEFAULT NULL COMMENT '',
    MODIFY COLUMN `deleted_by` varchar(99) DEFAULT NULL COMMENT '',
    MODIFY COLUMN `deleted_dt` datetime DEFAULT NULL COMMENT '',
    MODIFY COLUMN `program_id` varchar(99) DEFAULT NULL COMMENT '',
    COMMENT = 'SPS Sequence Policy Definition';

/* te_common.cm_sequence_policy */
ALTER TABLE `te_common`.`cm_sequence_policy`
    MODIFY COLUMN `policy_code` varchar(99) NOT NULL COMMENT '시퀀스 초기화 정책 코드',
    MODIFY COLUMN `created_dt` datetime NOT NULL DEFAULT current_timestamp() COMMENT '',
    MODIFY COLUMN `updated_dt` datetime NOT NULL DEFAULT current_timestamp() ON UPDATE current_timestamp() COMMENT '',
    MODIFY COLUMN `created_by` varchar(99) NOT NULL DEFAULT 'SYSTEM' COMMENT '',
    MODIFY COLUMN `updated_by` varchar(99) DEFAULT NULL COMMENT '',
    MODIFY COLUMN `deleted_by` varchar(99) DEFAULT NULL COMMENT '',
    MODIFY COLUMN `deleted_dt` datetime DEFAULT NULL COMMENT '',
    MODIFY COLUMN `client_ip` varchar(99) DEFAULT NULL COMMENT '',
    MODIFY COLUMN `program_id` varchar(99) DEFAULT NULL COMMENT '',
    MODIFY COLUMN `status_code` varchar(99) NOT NULL DEFAULT 'ACTIVE' COMMENT '',
    COMMENT = 'SPS 시퀀스 초기화 정책';

/* te_common.cm_sequence_format_definition */
ALTER TABLE `te_common`.`cm_sequence_format_definition`
    MODIFY COLUMN `format_code` varchar(99) NOT NULL COMMENT '시퀀스 포맷 코드',
    MODIFY COLUMN `sort_no` int(11) NOT NULL DEFAULT 0 COMMENT '',
    MODIFY COLUMN `status_code` varchar(99) NOT NULL DEFAULT 'ACTIVE' COMMENT '',
    MODIFY COLUMN `created_dt` datetime NOT NULL DEFAULT current_timestamp() COMMENT '',
    MODIFY COLUMN `created_by` varchar(99) NOT NULL DEFAULT 'SYSTEM' COMMENT '',
    MODIFY COLUMN `updated_dt` datetime NOT NULL DEFAULT current_timestamp() ON UPDATE current_timestamp() COMMENT '',
    MODIFY COLUMN `updated_by` varchar(99) NOT NULL DEFAULT 'SYSTEM' COMMENT '',
    MODIFY COLUMN `client_ip` varchar(99) DEFAULT NULL COMMENT '',
    MODIFY COLUMN `deleted_by` varchar(99) DEFAULT NULL COMMENT '',
    MODIFY COLUMN `deleted_dt` datetime DEFAULT NULL COMMENT '',
    MODIFY COLUMN `program_id` varchar(99) DEFAULT NULL COMMENT '',
    COMMENT = 'SPS Sequence Format Definition';

/* te_common.cm_sequence_format */
ALTER TABLE `te_common`.`cm_sequence_format`
    MODIFY COLUMN `format_code` varchar(99) NOT NULL COMMENT '시퀀스 포맷 코드',
    MODIFY COLUMN `created_dt` datetime NOT NULL DEFAULT current_timestamp() COMMENT '',
    MODIFY COLUMN `updated_dt` datetime NOT NULL DEFAULT current_timestamp() ON UPDATE current_timestamp() COMMENT '',
    MODIFY COLUMN `created_by` varchar(99) NOT NULL DEFAULT 'SYSTEM' COMMENT '',
    MODIFY COLUMN `updated_by` varchar(99) DEFAULT NULL COMMENT '',
    MODIFY COLUMN `deleted_by` varchar(99) DEFAULT NULL COMMENT '',
    MODIFY COLUMN `deleted_dt` datetime DEFAULT NULL COMMENT '',
    MODIFY COLUMN `client_ip` varchar(99) DEFAULT NULL COMMENT '',
    MODIFY COLUMN `program_id` varchar(99) DEFAULT NULL COMMENT '',
    MODIFY COLUMN `status_code` varchar(99) NOT NULL DEFAULT 'ACTIVE' COMMENT '',
    COMMENT = 'SPS 시퀀스 포맷 메타데이터';

/* te_common.cm_sequence_definition */
ALTER TABLE `te_common`.`cm_sequence_definition`
    MODIFY COLUMN `sequence_code` varchar(99) NOT NULL COMMENT '시퀀스 코드',
    MODIFY COLUMN `function_code` varchar(99) NOT NULL COMMENT '기능 코드',
    MODIFY COLUMN `domain_code` varchar(99) NOT NULL COMMENT '도메인 코드',
    MODIFY COLUMN `policy_code` varchar(99) NOT NULL COMMENT '시퀀스 정책 코드',
    MODIFY COLUMN `format_code` varchar(99) NOT NULL COMMENT '시퀀스 포맷 코드',
    MODIFY COLUMN `prefix_code` varchar(99) DEFAULT NULL COMMENT 'Prefix 코드',
    MODIFY COLUMN `sort_no` int(11) NOT NULL DEFAULT 0 COMMENT '',
    MODIFY COLUMN `status_code` varchar(99) NOT NULL DEFAULT 'ACTIVE' COMMENT '',
    MODIFY COLUMN `created_dt` datetime NOT NULL DEFAULT current_timestamp() COMMENT '',
    MODIFY COLUMN `created_by` varchar(99) NOT NULL DEFAULT 'SYSTEM' COMMENT '',
    MODIFY COLUMN `updated_dt` datetime NOT NULL DEFAULT current_timestamp() ON UPDATE current_timestamp() COMMENT '',
    MODIFY COLUMN `updated_by` varchar(99) NOT NULL DEFAULT 'SYSTEM' COMMENT '',
    MODIFY COLUMN `client_ip` varchar(99) DEFAULT NULL COMMENT '',
    MODIFY COLUMN `deleted_by` varchar(99) DEFAULT NULL COMMENT '',
    MODIFY COLUMN `deleted_dt` datetime DEFAULT NULL COMMENT '',
    MODIFY COLUMN `program_id` varchar(99) DEFAULT NULL COMMENT '',
    COMMENT = 'SPS Sequence Definition';

/* te_common.cm_sequence */
ALTER TABLE `te_common`.`cm_sequence`
    MODIFY COLUMN `sequence_code` varchar(99) NOT NULL COMMENT '',
    MODIFY COLUMN `sequence_dt` datetime NOT NULL COMMENT '',
    MODIFY COLUMN `current_value` varchar(2000) NOT NULL DEFAULT '0' COMMENT '',
    MODIFY COLUMN `created_dt` datetime NOT NULL DEFAULT current_timestamp() COMMENT '',
    MODIFY COLUMN `updated_dt` datetime NOT NULL DEFAULT current_timestamp() ON UPDATE current_timestamp() COMMENT '',
    MODIFY COLUMN `created_by` varchar(99) NOT NULL DEFAULT 'SYSTEM' COMMENT '',
    MODIFY COLUMN `updated_by` varchar(99) DEFAULT NULL COMMENT '',
    MODIFY COLUMN `deleted_by` varchar(99) DEFAULT NULL COMMENT '',
    MODIFY COLUMN `deleted_dt` datetime DEFAULT NULL COMMENT '',
    MODIFY COLUMN `client_ip` varchar(99) DEFAULT NULL COMMENT '',
    MODIFY COLUMN `program_id` varchar(99) DEFAULT NULL COMMENT '',
    MODIFY COLUMN `status_code` varchar(99) NOT NULL DEFAULT 'ACTIVE' COMMENT '',
    COMMENT = '';

/* te_common.cm_role_rule */
ALTER TABLE `te_common`.`cm_role_rule`
    COMMENT = 'Role과 Rule의 N:N 관계를 해소하는 최소 매핑 Object';

/* te_common.cm_role */
ALTER TABLE `te_common`.`cm_role`
    MODIFY COLUMN `role_id` varchar(99) NOT NULL COMMENT '',
    MODIFY COLUMN `role_code` varchar(99) NOT NULL COMMENT '',
    MODIFY COLUMN `role_name` varchar(150) NOT NULL COMMENT '',
    MODIFY COLUMN `created_dt` datetime NOT NULL DEFAULT current_timestamp() COMMENT '',
    MODIFY COLUMN `created_by` varchar(99) NOT NULL DEFAULT 'SYSTEM' COMMENT '',
    MODIFY COLUMN `updated_dt` datetime NOT NULL DEFAULT current_timestamp() ON UPDATE current_timestamp() COMMENT '',
    MODIFY COLUMN `updated_by` varchar(99) NOT NULL DEFAULT 'SYSTEM' COMMENT '',
    MODIFY COLUMN `client_ip` varchar(99) DEFAULT NULL COMMENT '',
    MODIFY COLUMN `deleted_by` varchar(99) DEFAULT NULL COMMENT '',
    MODIFY COLUMN `deleted_dt` datetime DEFAULT NULL COMMENT '',
    MODIFY COLUMN `program_id` varchar(99) DEFAULT NULL COMMENT '',
    MODIFY COLUMN `status_code` varchar(99) NOT NULL DEFAULT 'ACTIVE' COMMENT '',
    COMMENT = '';

/* te_common.cm_repository */
ALTER TABLE `te_common`.`cm_repository`
    MODIFY COLUMN `book_code` varchar(99) DEFAULT NULL COMMENT 'Story Book 코드',
    MODIFY COLUMN `chapter_code` varchar(99) DEFAULT NULL COMMENT 'Chapter 코드',
    MODIFY COLUMN `section_code` varchar(99) DEFAULT NULL COMMENT 'Section 코드',
    MODIFY COLUMN `business_code` varchar(99) NOT NULL COMMENT '업무분류 코드',
    MODIFY COLUMN `domain_code` varchar(99) NOT NULL COMMENT '도메인 코드',
    MODIFY COLUMN `data_type_code` varchar(99) NOT NULL COMMENT '자료구분 코드',
    MODIFY COLUMN `data_code` varchar(99) NOT NULL COMMENT '자료 코드',
    MODIFY COLUMN `sort_no` int(11) NOT NULL DEFAULT 0 COMMENT '',
    MODIFY COLUMN `status_code` varchar(99) NOT NULL DEFAULT 'ACTIVE' COMMENT '',
    MODIFY COLUMN `created_dt` datetime NOT NULL DEFAULT current_timestamp() COMMENT '',
    MODIFY COLUMN `created_by` varchar(99) NOT NULL DEFAULT 'SYSTEM' COMMENT '',
    MODIFY COLUMN `updated_dt` datetime NOT NULL DEFAULT current_timestamp() ON UPDATE current_timestamp() COMMENT '',
    MODIFY COLUMN `updated_by` varchar(99) NOT NULL DEFAULT 'SYSTEM' COMMENT '',
    MODIFY COLUMN `client_ip` varchar(99) DEFAULT NULL COMMENT '',
    MODIFY COLUMN `deleted_by` varchar(99) DEFAULT NULL COMMENT '',
    MODIFY COLUMN `deleted_dt` datetime DEFAULT NULL COMMENT '',
    MODIFY COLUMN `program_id` varchar(99) DEFAULT NULL COMMENT '',
    COMMENT = 'SPS Repository Core Table';

/* te_common.cm_member_role */
ALTER TABLE `te_common`.`cm_member_role`
    MODIFY COLUMN `member_role_id` varchar(99) NOT NULL COMMENT '',
    MODIFY COLUMN `member_id` varchar(99) NOT NULL COMMENT '',
    MODIFY COLUMN `role_id` varchar(99) NOT NULL COMMENT '',
    MODIFY COLUMN `created_dt` datetime NOT NULL DEFAULT current_timestamp() COMMENT '',
    MODIFY COLUMN `created_by` varchar(99) NOT NULL DEFAULT 'SYSTEM' COMMENT '',
    MODIFY COLUMN `updated_dt` datetime NOT NULL DEFAULT current_timestamp() ON UPDATE current_timestamp() COMMENT '',
    MODIFY COLUMN `updated_by` varchar(99) NOT NULL DEFAULT 'SYSTEM' COMMENT '',
    MODIFY COLUMN `client_ip` varchar(99) DEFAULT NULL COMMENT '',
    MODIFY COLUMN `deleted_by` varchar(99) DEFAULT NULL COMMENT '',
    MODIFY COLUMN `deleted_dt` datetime DEFAULT NULL COMMENT '',
    MODIFY COLUMN `program_id` varchar(99) DEFAULT NULL COMMENT '',
    MODIFY COLUMN `status_code` varchar(99) NOT NULL DEFAULT 'ACTIVE' COMMENT '',
    COMMENT = '';

/* te_common.cm_member_private */
ALTER TABLE `te_common`.`cm_member_private`
    MODIFY COLUMN `member_id` varchar(99) NOT NULL COMMENT '',
    MODIFY COLUMN `birth_dt` datetime DEFAULT NULL COMMENT '',
    MODIFY COLUMN `phone` varchar(50) DEFAULT NULL COMMENT '',
    MODIFY COLUMN `email` varchar(500) DEFAULT NULL COMMENT '',
    MODIFY COLUMN `address` varchar(500) DEFAULT NULL COMMENT '',
    MODIFY COLUMN `created_dt` datetime NOT NULL DEFAULT current_timestamp() COMMENT '',
    MODIFY COLUMN `created_by` varchar(99) NOT NULL DEFAULT 'SYSTEM' COMMENT '',
    MODIFY COLUMN `updated_dt` datetime NOT NULL DEFAULT current_timestamp() ON UPDATE current_timestamp() COMMENT '',
    MODIFY COLUMN `updated_by` varchar(99) NOT NULL DEFAULT 'SYSTEM' COMMENT '',
    MODIFY COLUMN `client_ip` varchar(99) DEFAULT NULL COMMENT '',
    MODIFY COLUMN `deleted_by` varchar(99) DEFAULT NULL COMMENT '',
    MODIFY COLUMN `deleted_dt` datetime DEFAULT NULL COMMENT '',
    MODIFY COLUMN `program_id` varchar(99) DEFAULT NULL COMMENT '',
    MODIFY COLUMN `status_code` varchar(99) NOT NULL DEFAULT 'ACTIVE' COMMENT '',
    COMMENT = '';

/* te_common.cm_member */
ALTER TABLE `te_common`.`cm_member`
    MODIFY COLUMN `member_id` varchar(99) NOT NULL COMMENT '',
    MODIFY COLUMN `email` varchar(500) NOT NULL COMMENT '',
    MODIFY COLUMN `password_hash` varchar(128) NOT NULL COMMENT '',
    MODIFY COLUMN `member_name` varchar(150) NOT NULL COMMENT '',
    MODIFY COLUMN `member_type_code` varchar(99) NOT NULL COMMENT '',
    MODIFY COLUMN `created_dt` datetime NOT NULL DEFAULT current_timestamp() COMMENT '',
    MODIFY COLUMN `created_by` varchar(99) NOT NULL DEFAULT 'SYSTEM' COMMENT '',
    MODIFY COLUMN `updated_dt` datetime NOT NULL DEFAULT current_timestamp() ON UPDATE current_timestamp() COMMENT '',
    MODIFY COLUMN `updated_by` varchar(99) NOT NULL DEFAULT 'SYSTEM' COMMENT '',
    MODIFY COLUMN `client_ip` varchar(99) DEFAULT NULL COMMENT '',
    MODIFY COLUMN `deleted_by` varchar(99) DEFAULT NULL COMMENT '',
    MODIFY COLUMN `deleted_dt` datetime DEFAULT NULL COMMENT '',
    MODIFY COLUMN `program_id` varchar(99) DEFAULT NULL COMMENT '',
    MODIFY COLUMN `status_code` varchar(99) NOT NULL DEFAULT 'ACTIVE' COMMENT '',
    COMMENT = '';

/* te_common.cm_login_history */
ALTER TABLE `te_common`.`cm_login_history`
    MODIFY COLUMN `login_history_id` varchar(99) NOT NULL COMMENT '',
    MODIFY COLUMN `member_id` varchar(99) DEFAULT NULL COMMENT '',
    MODIFY COLUMN `login_id` varchar(99) NOT NULL COMMENT '',
    MODIFY COLUMN `login_status_code` varchar(99) NOT NULL COMMENT '',
    MODIFY COLUMN `client_ip` varchar(99) DEFAULT NULL COMMENT '',
    MODIFY COLUMN `user_agent` varchar(500) DEFAULT NULL COMMENT '',
    MODIFY COLUMN `login_dt` datetime NOT NULL DEFAULT current_timestamp() COMMENT '',
    MODIFY COLUMN `status_code` varchar(99) NOT NULL DEFAULT 'ACTIVE' COMMENT '',
    COMMENT = '';

/* te_common.cm_locale */
ALTER TABLE `te_common`.`cm_locale`
    MODIFY COLUMN `locale_code` varchar(99) NOT NULL COMMENT '',
    MODIFY COLUMN `language_code` varchar(99) NOT NULL COMMENT '',
    MODIFY COLUMN `country_code` varchar(99) NOT NULL COMMENT '',
    MODIFY COLUMN `locale_name` varchar(150) NOT NULL COMMENT '',
    MODIFY COLUMN `native_name` varchar(150) NOT NULL COMMENT '',
    MODIFY COLUMN `date_format` varchar(99) DEFAULT NULL COMMENT '',
    MODIFY COLUMN `time_format` varchar(99) DEFAULT NULL COMMENT '',
    MODIFY COLUMN `datetime_format` varchar(99) DEFAULT NULL COMMENT '',
    MODIFY COLUMN `number_format` varchar(99) DEFAULT NULL COMMENT '',
    MODIFY COLUMN `timezone_id` varchar(99) DEFAULT NULL COMMENT '',
    MODIFY COLUMN `sort_no` int(11) NOT NULL DEFAULT 0 COMMENT '',
    MODIFY COLUMN `status_code` varchar(99) NOT NULL DEFAULT 'ACTIVE' COMMENT '',
    MODIFY COLUMN `created_dt` datetime NOT NULL DEFAULT current_timestamp() COMMENT '',
    MODIFY COLUMN `created_by` varchar(99) NOT NULL DEFAULT 'SYSTEM' COMMENT '',
    MODIFY COLUMN `updated_dt` datetime NOT NULL DEFAULT current_timestamp() ON UPDATE current_timestamp() COMMENT '',
    MODIFY COLUMN `updated_by` varchar(99) NOT NULL DEFAULT 'SYSTEM' COMMENT '',
    MODIFY COLUMN `deleted_by` varchar(99) DEFAULT NULL COMMENT '',
    MODIFY COLUMN `deleted_dt` datetime DEFAULT NULL COMMENT '',
    MODIFY COLUMN `client_ip` varchar(99) DEFAULT NULL COMMENT '',
    MODIFY COLUMN `program_id` varchar(99) DEFAULT NULL COMMENT '',
    COMMENT = '';

/* te_common.cm_legal_retention_policy */
ALTER TABLE `te_common`.`cm_legal_retention_policy`
    MODIFY COLUMN `legal_basis_code` varchar(99) NOT NULL COMMENT '법적 근거 코드',
    MODIFY COLUMN `disposal_action_code` varchar(99) NOT NULL COMMENT '보존기간 만료 후 처리 방식',
    MODIFY COLUMN `created_by` varchar(99) NOT NULL DEFAULT 'SYSTEM' COMMENT '',
    MODIFY COLUMN `created_dt` datetime NOT NULL DEFAULT current_timestamp() COMMENT '',
    MODIFY COLUMN `updated_by` varchar(99) DEFAULT NULL COMMENT '',
    MODIFY COLUMN `updated_dt` datetime DEFAULT NULL COMMENT '',
    MODIFY COLUMN `deleted_by` varchar(99) DEFAULT NULL COMMENT '',
    MODIFY COLUMN `deleted_dt` datetime DEFAULT NULL COMMENT '',
    MODIFY COLUMN `client_ip` varchar(99) DEFAULT NULL COMMENT '',
    MODIFY COLUMN `program_id` varchar(99) DEFAULT NULL COMMENT '',
    MODIFY COLUMN `status_code` varchar(99) NOT NULL DEFAULT 'ACTIVE' COMMENT '',
    COMMENT = '법적 보존기한 정책';

/* te_common.cm_language */
ALTER TABLE `te_common`.`cm_language`
    MODIFY COLUMN `language_code` varchar(99) NOT NULL COMMENT '',
    MODIFY COLUMN `language_name` varchar(150) NOT NULL COMMENT '',
    MODIFY COLUMN `native_name` varchar(150) NOT NULL COMMENT '',
    MODIFY COLUMN `sort_no` int(11) NOT NULL DEFAULT 0 COMMENT '',
    MODIFY COLUMN `status_code` varchar(99) NOT NULL DEFAULT 'ACTIVE' COMMENT '',
    MODIFY COLUMN `created_dt` datetime NOT NULL DEFAULT current_timestamp() COMMENT '',
    MODIFY COLUMN `created_by` varchar(99) NOT NULL DEFAULT 'SYSTEM' COMMENT '',
    MODIFY COLUMN `updated_dt` datetime NOT NULL DEFAULT current_timestamp() ON UPDATE current_timestamp() COMMENT '',
    MODIFY COLUMN `updated_by` varchar(99) NOT NULL DEFAULT 'SYSTEM' COMMENT '',
    MODIFY COLUMN `client_ip` varchar(99) DEFAULT NULL COMMENT '',
    MODIFY COLUMN `deleted_by` varchar(99) DEFAULT NULL COMMENT '',
    MODIFY COLUMN `deleted_dt` datetime DEFAULT NULL COMMENT '',
    MODIFY COLUMN `program_id` varchar(99) DEFAULT NULL COMMENT '',
    COMMENT = '';

/* te_common.cm_data_type */
ALTER TABLE `te_common`.`cm_data_type`
    MODIFY COLUMN `data_type_code` varchar(99) NOT NULL COMMENT '',
    MODIFY COLUMN `data_type_name` varchar(150) DEFAULT NULL COMMENT '',
    MODIFY COLUMN `description` varchar(2000) DEFAULT NULL COMMENT '',
    MODIFY COLUMN `default_classification_code` varchar(99) DEFAULT NULL COMMENT '',
    MODIFY COLUMN `default_storage_type` varchar(99) DEFAULT NULL COMMENT '',
    MODIFY COLUMN `default_retention_policy_code` varchar(99) DEFAULT NULL COMMENT '',
    MODIFY COLUMN `ai_analysis_allowed_yn` char(1) DEFAULT 'Y' COMMENT '',
    MODIFY COLUMN `encryption_required_yn` char(1) DEFAULT 'N' COMMENT '',
    MODIFY COLUMN `created_by` varchar(99) NOT NULL DEFAULT 'SYSTEM' COMMENT '',
    MODIFY COLUMN `created_dt` datetime NOT NULL DEFAULT current_timestamp() COMMENT '',
    MODIFY COLUMN `updated_by` varchar(99) DEFAULT NULL COMMENT '',
    MODIFY COLUMN `updated_dt` datetime DEFAULT NULL COMMENT '',
    MODIFY COLUMN `deleted_by` varchar(99) DEFAULT NULL COMMENT '',
    MODIFY COLUMN `deleted_dt` datetime DEFAULT NULL COMMENT '',
    MODIFY COLUMN `client_ip` varchar(99) DEFAULT NULL COMMENT '',
    MODIFY COLUMN `program_id` varchar(99) DEFAULT NULL COMMENT '',
    MODIFY COLUMN `status_code` varchar(99) NOT NULL DEFAULT 'ACTIVE' COMMENT '',
    COMMENT = '';

/* te_common.cm_data_lifecycle_index */
ALTER TABLE `te_common`.`cm_data_lifecycle_index`
    MODIFY COLUMN `status_code` varchar(99) NOT NULL COMMENT '상태',
    MODIFY COLUMN `created_dt` datetime NOT NULL DEFAULT current_timestamp() COMMENT '',
    MODIFY COLUMN `updated_dt` datetime DEFAULT NULL COMMENT '',
    MODIFY COLUMN `created_by` varchar(99) NOT NULL DEFAULT 'SYSTEM' COMMENT '',
    MODIFY COLUMN `updated_by` varchar(99) DEFAULT NULL COMMENT '',
    MODIFY COLUMN `deleted_by` varchar(99) DEFAULT NULL COMMENT '',
    MODIFY COLUMN `deleted_dt` datetime DEFAULT NULL COMMENT '',
    MODIFY COLUMN `change_story` varchar(2000) DEFAULT NULL COMMENT '',
    MODIFY COLUMN `client_ip` varchar(99) DEFAULT NULL COMMENT '',
    MODIFY COLUMN `program_id` varchar(99) DEFAULT NULL COMMENT '',
    COMMENT = '데이터 생명주기 추적';

/* te_common.cm_data_classification */
ALTER TABLE `te_common`.`cm_data_classification`
    MODIFY COLUMN `classification_code` varchar(99) NOT NULL COMMENT '데이터 등급 코드',
    MODIFY COLUMN `description` varchar(2000) DEFAULT NULL COMMENT '',
    MODIFY COLUMN `encryption_required_yn` char(1) DEFAULT 'N' COMMENT '',
    MODIFY COLUMN `masking_required_yn` char(1) DEFAULT 'N' COMMENT '',
    MODIFY COLUMN `ai_access_allowed_yn` char(1) DEFAULT 'Y' COMMENT '',
    MODIFY COLUMN `external_transfer_allowed_yn` char(1) DEFAULT 'N' COMMENT '',
    MODIFY COLUMN `created_by` varchar(99) NOT NULL DEFAULT 'SYSTEM' COMMENT '',
    MODIFY COLUMN `created_dt` datetime NOT NULL DEFAULT current_timestamp() COMMENT '',
    MODIFY COLUMN `updated_by` varchar(99) DEFAULT NULL COMMENT '',
    MODIFY COLUMN `updated_dt` datetime DEFAULT NULL COMMENT '',
    MODIFY COLUMN `deleted_by` varchar(99) DEFAULT NULL COMMENT '',
    MODIFY COLUMN `deleted_dt` datetime DEFAULT NULL COMMENT '',
    MODIFY COLUMN `client_ip` varchar(99) DEFAULT NULL COMMENT '',
    MODIFY COLUMN `program_id` varchar(99) DEFAULT NULL COMMENT '',
    MODIFY COLUMN `status_code` varchar(99) NOT NULL DEFAULT 'ACTIVE' COMMENT '',
    COMMENT = '';

/* te_common.cm_country */
ALTER TABLE `te_common`.`cm_country`
    MODIFY COLUMN `country_code` varchar(99) NOT NULL COMMENT '',
    MODIFY COLUMN `country_name` varchar(150) NOT NULL COMMENT '',
    MODIFY COLUMN `native_name` varchar(150) DEFAULT NULL COMMENT '',
    MODIFY COLUMN `sort_no` int(11) NOT NULL DEFAULT 0 COMMENT '',
    MODIFY COLUMN `status_code` varchar(99) NOT NULL DEFAULT 'ACTIVE' COMMENT '',
    MODIFY COLUMN `created_dt` datetime NOT NULL DEFAULT current_timestamp() COMMENT '',
    MODIFY COLUMN `created_by` varchar(99) NOT NULL DEFAULT 'SYSTEM' COMMENT '',
    MODIFY COLUMN `updated_dt` datetime NOT NULL DEFAULT current_timestamp() ON UPDATE current_timestamp() COMMENT '',
    MODIFY COLUMN `updated_by` varchar(99) NOT NULL DEFAULT 'SYSTEM' COMMENT '',
    MODIFY COLUMN `client_ip` varchar(99) DEFAULT NULL COMMENT '',
    MODIFY COLUMN `deleted_by` varchar(99) DEFAULT NULL COMMENT '',
    MODIFY COLUMN `deleted_dt` datetime DEFAULT NULL COMMENT '',
    MODIFY COLUMN `program_id` varchar(99) DEFAULT NULL COMMENT '',
    COMMENT = '';

/* te_common.cm_consent_history */
ALTER TABLE `te_common`.`cm_consent_history`
    MODIFY COLUMN `consent_history_id` varchar(99) NOT NULL COMMENT '',
    MODIFY COLUMN `user_id` varchar(99) NOT NULL COMMENT '',
    MODIFY COLUMN `consent_type` varchar(99) NOT NULL COMMENT '',
    MODIFY COLUMN `consent_yn` char(1) NOT NULL COMMENT '',
    MODIFY COLUMN `created_by` varchar(99) NOT NULL COMMENT '',
    MODIFY COLUMN `created_dt` datetime NOT NULL DEFAULT current_timestamp() COMMENT '',
    MODIFY COLUMN `updated_by` varchar(99) DEFAULT NULL COMMENT '',
    MODIFY COLUMN `updated_dt` datetime DEFAULT NULL COMMENT '',
    MODIFY COLUMN `deleted_by` varchar(99) DEFAULT NULL COMMENT '',
    MODIFY COLUMN `deleted_dt` datetime DEFAULT NULL COMMENT '',
    MODIFY COLUMN `change_story` varchar(2000) DEFAULT NULL COMMENT '',
    MODIFY COLUMN `client_ip` varchar(99) DEFAULT NULL COMMENT '',
    MODIFY COLUMN `program_id` varchar(99) DEFAULT NULL COMMENT '',
    MODIFY COLUMN `status_code` varchar(99) NOT NULL DEFAULT 'ACTIVE' COMMENT '',
    COMMENT = '';

/* te_common.cm_common_code_group */
ALTER TABLE `te_common`.`cm_common_code_group`
    MODIFY COLUMN `group_code` varchar(99) NOT NULL COMMENT '',
    MODIFY COLUMN `group_name` varchar(150) NOT NULL COMMENT '',
    MODIFY COLUMN `sort_no` int(11) DEFAULT 0 COMMENT '',
    MODIFY COLUMN `status_code` varchar(99) NOT NULL DEFAULT 'ACTIVE' COMMENT '',
    MODIFY COLUMN `created_dt` datetime NOT NULL DEFAULT current_timestamp() COMMENT '',
    MODIFY COLUMN `created_by` varchar(99) NOT NULL DEFAULT 'SYSTEM' COMMENT '',
    MODIFY COLUMN `updated_dt` datetime NOT NULL DEFAULT current_timestamp() ON UPDATE current_timestamp() COMMENT '',
    MODIFY COLUMN `updated_by` varchar(99) NOT NULL DEFAULT 'SYSTEM' COMMENT '',
    MODIFY COLUMN `client_ip` varchar(99) DEFAULT NULL COMMENT '',
    MODIFY COLUMN `deleted_by` varchar(99) DEFAULT NULL COMMENT '',
    MODIFY COLUMN `deleted_dt` datetime DEFAULT NULL COMMENT '',
    MODIFY COLUMN `program_id` varchar(99) DEFAULT NULL COMMENT '',
    COMMENT = '';

/* te_common.cm_common_code */
ALTER TABLE `te_common`.`cm_common_code`
    MODIFY COLUMN `group_code` varchar(99) NOT NULL COMMENT '',
    MODIFY COLUMN `code` varchar(99) NOT NULL COMMENT '',
    MODIFY COLUMN `code_name` varchar(150) NOT NULL COMMENT '',
    MODIFY COLUMN `sort_no` int(11) NOT NULL DEFAULT 0 COMMENT '',
    MODIFY COLUMN `status_code` varchar(99) NOT NULL DEFAULT 'ACTIVE' COMMENT '',
    MODIFY COLUMN `created_dt` datetime NOT NULL DEFAULT current_timestamp() COMMENT '',
    MODIFY COLUMN `created_by` varchar(99) NOT NULL DEFAULT 'SYSTEM' COMMENT '',
    MODIFY COLUMN `updated_dt` datetime NOT NULL DEFAULT current_timestamp() ON UPDATE current_timestamp() COMMENT '',
    MODIFY COLUMN `updated_by` varchar(99) NOT NULL DEFAULT 'SYSTEM' COMMENT '',
    MODIFY COLUMN `client_ip` varchar(99) DEFAULT NULL COMMENT '',
    MODIFY COLUMN `deleted_by` varchar(99) DEFAULT NULL COMMENT '',
    MODIFY COLUMN `deleted_dt` datetime DEFAULT NULL COMMENT '',
    MODIFY COLUMN `program_id` varchar(99) DEFAULT NULL COMMENT '',
    COMMENT = '';

/* te_common.cm_code_inspection_result */
ALTER TABLE `te_common`.`cm_code_inspection_result`
    MODIFY COLUMN `inspection_id` varchar(99) NOT NULL COMMENT '',
    MODIFY COLUMN `inspection_type` varchar(99) NOT NULL COMMENT '',
    MODIFY COLUMN `group_code` varchar(99) NOT NULL COMMENT '',
    MODIFY COLUMN `code` varchar(99) DEFAULT NULL COMMENT '',
    MODIFY COLUMN `code_name` varchar(150) DEFAULT NULL COMMENT '',
    MODIFY COLUMN `related_codes` varchar(2000) DEFAULT NULL COMMENT '',
    MODIFY COLUMN `message` text NOT NULL COMMENT '',
    MODIFY COLUMN `severity_code` varchar(99) NOT NULL DEFAULT 'WARNING' COMMENT '',
    MODIFY COLUMN `created_dt` datetime NOT NULL DEFAULT current_timestamp() COMMENT '',
    MODIFY COLUMN `updated_dt` datetime NOT NULL DEFAULT current_timestamp() ON UPDATE current_timestamp() COMMENT '',
    MODIFY COLUMN `created_by` varchar(99) NOT NULL DEFAULT 'SYSTEM' COMMENT '',
    MODIFY COLUMN `updated_by` varchar(99) DEFAULT NULL COMMENT '',
    MODIFY COLUMN `deleted_by` varchar(99) DEFAULT NULL COMMENT '',
    MODIFY COLUMN `deleted_dt` datetime DEFAULT NULL COMMENT '',
    MODIFY COLUMN `client_ip` varchar(99) DEFAULT NULL COMMENT '',
    MODIFY COLUMN `program_id` varchar(99) DEFAULT NULL COMMENT '',
    MODIFY COLUMN `status_code` varchar(99) NOT NULL DEFAULT 'ACTIVE' COMMENT '',
    COMMENT = '';

/* te_common.cm_change_history */
ALTER TABLE `te_common`.`cm_change_history`
    MODIFY COLUMN `status_code` varchar(99) NOT NULL DEFAULT 'ACTIVE' COMMENT '',
    COMMENT = '공통 변경 이력';

/* te_common.cm_business_domain */
ALTER TABLE `te_common`.`cm_business_domain`
    MODIFY COLUMN `business_domain_code` varchar(99) NOT NULL COMMENT '업무 도메인 코드',
    MODIFY COLUMN `created_dt` datetime NOT NULL DEFAULT current_timestamp() COMMENT '',
    MODIFY COLUMN `created_by` varchar(99) NOT NULL DEFAULT 'SYSTEM' COMMENT '',
    MODIFY COLUMN `updated_dt` datetime NOT NULL DEFAULT current_timestamp() ON UPDATE current_timestamp() COMMENT '',
    MODIFY COLUMN `updated_by` varchar(99) NOT NULL DEFAULT 'SYSTEM' COMMENT '',
    MODIFY COLUMN `deleted_by` varchar(99) DEFAULT NULL COMMENT '',
    MODIFY COLUMN `deleted_dt` datetime DEFAULT NULL COMMENT '',
    MODIFY COLUMN `program_id` varchar(99) DEFAULT NULL COMMENT '',
    MODIFY COLUMN `client_ip` varchar(99) DEFAULT NULL COMMENT '',
    MODIFY COLUMN `status_code` varchar(99) NOT NULL DEFAULT 'ACTIVE' COMMENT '',
    COMMENT = '업무 도메인';

/* te_common.cm_audit_policy */
ALTER TABLE `te_common`.`cm_audit_policy`
    MODIFY COLUMN `audit_policy_code` varchar(99) NOT NULL COMMENT '감사 정책 코드',
    MODIFY COLUMN `created_dt` datetime NOT NULL DEFAULT current_timestamp() COMMENT '',
    MODIFY COLUMN `created_by` varchar(99) NOT NULL DEFAULT 'SYSTEM' COMMENT '',
    MODIFY COLUMN `updated_dt` datetime NOT NULL DEFAULT current_timestamp() ON UPDATE current_timestamp() COMMENT '',
    MODIFY COLUMN `updated_by` varchar(99) NOT NULL DEFAULT 'SYSTEM' COMMENT '',
    MODIFY COLUMN `deleted_by` varchar(99) DEFAULT NULL COMMENT '',
    MODIFY COLUMN `deleted_dt` datetime DEFAULT NULL COMMENT '',
    MODIFY COLUMN `program_id` varchar(99) DEFAULT NULL COMMENT '',
    MODIFY COLUMN `client_ip` varchar(99) DEFAULT NULL COMMENT '',
    MODIFY COLUMN `status_code` varchar(99) NOT NULL DEFAULT 'ACTIVE' COMMENT '',
    COMMENT = '감사 정책';

/* te_story_platform.sp_work_session */
ALTER TABLE `te_story_platform`.`sp_work_session`
    MODIFY COLUMN `work_type_code` varchar(99) NOT NULL COMMENT 'Work Type Code',
    MODIFY COLUMN `work_status_code` varchar(99) NOT NULL COMMENT 'Work Status Code',
    MODIFY COLUMN `work_result_code` varchar(99) DEFAULT NULL COMMENT 'Work Result Code',
    MODIFY COLUMN `created_by` varchar(99) NOT NULL COMMENT '',
    MODIFY COLUMN `created_dt` datetime NOT NULL DEFAULT current_timestamp() COMMENT '',
    MODIFY COLUMN `updated_by` varchar(99) DEFAULT NULL COMMENT '',
    MODIFY COLUMN `updated_dt` datetime DEFAULT NULL ON UPDATE current_timestamp() COMMENT '',
    MODIFY COLUMN `deleted_by` varchar(99) DEFAULT NULL COMMENT '',
    MODIFY COLUMN `deleted_dt` datetime DEFAULT NULL COMMENT '',
    MODIFY COLUMN `client_ip` varchar(99) DEFAULT NULL COMMENT '',
    MODIFY COLUMN `program_id` varchar(99) DEFAULT NULL COMMENT '',
    COMMENT = 'Work Session Repository. Work의 최상위 실행 단위를 관리한다. Runtime, Generator, AI, Engine이 공통으로 사용하는 작업 세션 Repository.';

/* te_story_platform.sp_work_item */
ALTER TABLE `te_story_platform`.`sp_work_item`
    MODIFY COLUMN `work_status_code` varchar(99) NOT NULL COMMENT 'Work Status Code',
    MODIFY COLUMN `work_result_code` varchar(99) DEFAULT NULL COMMENT 'Work Result Code',
    MODIFY COLUMN `created_by` varchar(99) NOT NULL COMMENT '',
    MODIFY COLUMN `created_dt` datetime NOT NULL DEFAULT current_timestamp() COMMENT '',
    MODIFY COLUMN `updated_by` varchar(99) DEFAULT NULL COMMENT '',
    MODIFY COLUMN `updated_dt` datetime DEFAULT NULL ON UPDATE current_timestamp() COMMENT '',
    MODIFY COLUMN `deleted_by` varchar(99) DEFAULT NULL COMMENT '',
    MODIFY COLUMN `deleted_dt` datetime DEFAULT NULL COMMENT '',
    MODIFY COLUMN `client_ip` varchar(99) DEFAULT NULL COMMENT '',
    MODIFY COLUMN `program_id` varchar(99) DEFAULT NULL COMMENT '',
    COMMENT = 'Work Item Repository. Work Session을 구성하는 개별 작업 단위를 관리한다. Runtime, Generator, AI, Engine이 수행하는 각 단계의 실행 정보를 저장한다.';

/* te_story_platform.sp_work_asset */
ALTER TABLE `te_story_platform`.`sp_work_asset`
    MODIFY COLUMN `asset_type_code` varchar(99) NOT NULL COMMENT 'Work Asset Type Code',
    MODIFY COLUMN `asset_status_code` varchar(99) NOT NULL COMMENT 'Asset Status Code',
    MODIFY COLUMN `created_by` varchar(99) NOT NULL COMMENT '',
    MODIFY COLUMN `created_dt` datetime NOT NULL DEFAULT current_timestamp() COMMENT '',
    MODIFY COLUMN `updated_by` varchar(99) DEFAULT NULL COMMENT '',
    MODIFY COLUMN `updated_dt` datetime DEFAULT NULL ON UPDATE current_timestamp() COMMENT '',
    MODIFY COLUMN `deleted_by` varchar(99) DEFAULT NULL COMMENT '',
    MODIFY COLUMN `deleted_dt` datetime DEFAULT NULL COMMENT '',
    MODIFY COLUMN `client_ip` varchar(99) DEFAULT NULL COMMENT '',
    MODIFY COLUMN `program_id` varchar(99) DEFAULT NULL COMMENT '',
    COMMENT = 'Work Asset Repository. Work Item 수행 과정에서 생성되는 모든 산출물을 관리하는 Repository. Runtime, Generator, AI, Engine이 생성한 SQL, Source, Document, Log, Image, JSON 등 모든 Asset을 관리한다.';

/* te_story_platform.sp_relationship_attribute */
ALTER TABLE `te_story_platform`.`sp_relationship_attribute`
    COMMENT = 'ERD Scope Relationship의 Source Attribute와 Target Attribute 매핑을 관리한다.';

/* te_story_platform.sp_relationship */
ALTER TABLE `te_story_platform`.`sp_relationship`
    MODIFY COLUMN `relationship_scope_code` varchar(99) NOT NULL DEFAULT 'ERD' COMMENT 'Relationship Scope Code. ERD 또는 OBJECT',
    MODIFY COLUMN `source_object_type_code` varchar(99) DEFAULT NULL COMMENT 'Source Object 유형 코드. KNOWLEDGE, LIFECYCLE, RULE, VERIFIED_SQL 등',
    MODIFY COLUMN `target_object_type_code` varchar(99) DEFAULT NULL COMMENT 'Target Object 유형 코드. KNOWLEDGE, LIFECYCLE, RULE, VERIFIED_SQL 등',
    MODIFY COLUMN `relationship_code` varchar(99) NOT NULL COMMENT 'Relationship Code. 사람이 이해하고 Generator가 참조할 수 있는 의미 기반 식별 코드',
    MODIFY COLUMN `relationship_type_code` varchar(99) NOT NULL DEFAULT 'FK' COMMENT 'Relationship Type Code. Engine과 Generator의 처리 방식을 결정한다',
    MODIFY COLUMN `delete_rule_code` varchar(99) DEFAULT NULL COMMENT '삭제 시 Relationship 처리 규칙',
    MODIFY COLUMN `update_rule_code` varchar(99) DEFAULT NULL COMMENT '변경 시 Relationship 처리 규칙',
    COMMENT = 'SPS 범용 Object Relationship Repository. ERD Entity 관계와 Knowledge, Lifecycle, Rule, Verified SQL 등 Object 간 관계를 관리한다.';

/* te_story_platform.sp_object_lifecycle */
ALTER TABLE `te_story_platform`.`sp_object_lifecycle`
    MODIFY COLUMN `object_lifecycle_id` varchar(99) NOT NULL COMMENT '',
    MODIFY COLUMN `object_id` varchar(99) NOT NULL COMMENT '',
    MODIFY COLUMN `lifecycle_status_code` varchar(99) NOT NULL COMMENT '',
    MODIFY COLUMN `lifecycle_event_code` varchar(99) NOT NULL COMMENT '',
    MODIFY COLUMN `lifecycle_reason` varchar(2000) DEFAULT NULL COMMENT '',
    MODIFY COLUMN `lifecycle_note` text DEFAULT NULL COMMENT '',
    MODIFY COLUMN `effective_start_dt` datetime NOT NULL DEFAULT current_timestamp() COMMENT '',
    MODIFY COLUMN `effective_end_dt` datetime DEFAULT NULL COMMENT '',
    MODIFY COLUMN `created_by` varchar(99) NOT NULL DEFAULT 'SYSTEM' COMMENT '',
    MODIFY COLUMN `created_dt` datetime NOT NULL DEFAULT current_timestamp() COMMENT '',
    MODIFY COLUMN `updated_by` varchar(99) DEFAULT NULL COMMENT '',
    MODIFY COLUMN `updated_dt` datetime DEFAULT NULL COMMENT '',
    MODIFY COLUMN `deleted_by` varchar(99) DEFAULT NULL COMMENT '',
    MODIFY COLUMN `deleted_dt` datetime DEFAULT NULL COMMENT '',
    MODIFY COLUMN `client_ip` varchar(99) DEFAULT NULL COMMENT '',
    MODIFY COLUMN `program_id` varchar(99) DEFAULT NULL COMMENT '',
    COMMENT = '';

/* te_story_platform.sp_object_execution_link */
ALTER TABLE `te_story_platform`.`sp_object_execution_link`
    MODIFY COLUMN `execution_link_type_code` varchar(99) NOT NULL DEFAULT 'MONGODB' COMMENT 'Execution Link Type Code. 모든 _code 계열 컬럼은 VARCHAR(99)를 표준으로 한다.',
    MODIFY COLUMN `created_dt` datetime NOT NULL DEFAULT current_timestamp() COMMENT '',
    MODIFY COLUMN `updated_dt` datetime DEFAULT NULL ON UPDATE current_timestamp() COMMENT '',
    MODIFY COLUMN `deleted_dt` datetime DEFAULT NULL COMMENT '',
    COMMENT = 'Object 실행 시도 관리';

/* te_story_platform.sp_object */
ALTER TABLE `te_story_platform`.`sp_object`
    MODIFY COLUMN `object_code` varchar(99) NOT NULL COMMENT 'Object Code. Object의 사람이 읽을 수 있는 코드. 모든 _code 계열 컬럼은 VARCHAR(99)를 표준으로 한다.',
    MODIFY COLUMN `business_code` varchar(99) NOT NULL COMMENT 'Business Code. 모든 _code 계열 컬럼은 VARCHAR(99)를 표준으로 한다.',
    MODIFY COLUMN `domain_code` varchar(99) NOT NULL COMMENT 'Domain Code. 모든 _code 계열 컬럼은 VARCHAR(99)를 표준으로 한다.',
    MODIFY COLUMN `object_type_code` varchar(99) NOT NULL COMMENT 'Object Type Code. 모든 _code 계열 컬럼은 VARCHAR(99)를 표준으로 한다.',
    MODIFY COLUMN `status_code` varchar(99) NOT NULL DEFAULT 'ACTIVE' COMMENT 'Status Code. 모든 _code 계열 컬럼은 VARCHAR(99)를 표준으로 한다.',
    MODIFY COLUMN `version_num` varchar(99) DEFAULT NULL COMMENT '',
    MODIFY COLUMN `sequence_scope_code` varchar(99) DEFAULT NULL COMMENT 'Sequence Scope Code. 모든 _code 계열 컬럼은 VARCHAR(99)를 표준으로 한다.',
    MODIFY COLUMN `identifier_target_code` varchar(99) DEFAULT NULL COMMENT 'Identifier Target Code. SPS_IDENTIFIER_TARGET 공통코드를 참조한다. 모든 _code 계열 컬럼은 VARCHAR(99)를 표준으로 한다.',
    COMMENT = '[Identifier Repository]\r\n\r\n- Identifier Target 정보는 cm_common_code에서 관리한다.\r\n- Group Code : SPS_IDENTIFIER_TARGET\r\n- code_name  : Object Code (예: OBJECT, MEMBER, DATABASE, SCREEN)\r\n- code       : Identifier Object Code (예: OB, MB, DB, SC)\r\n- extension_json : Identifier 확장 정보 및 Blueprint Token 관리\r\n\r\n[Object First]\r\n\r\n- sp_object는 Object를 정의한다.\r\n- Identifier 생성 규칙은 Repository Metadata를 통해 해석한다.\r\n- Engine은 Repository를 해석하며 Identifier를 생성한다.\r\n- Hardcoding을 금지한다.\r\n\r\n[Repository Rule]\r\n\r\n- Object의 의미는 sp_object가 관리한다.\r\n- Identifier의 약어 및 확장 속성은 cm_common_code.extension_json이 관리한다.\r\n- 두 Repository를 함께 해석하여 Identifier를 생성한다.\r\n\r\nPURPOSE: Defines SPS Object Class metadata.\r\nROLE: Central Object Class repository.\r\nSCOPE: Business, Domain, Database, Schema, Table, Entity, Attribute, Relationship, ERD, API, Screen, Workflow, Event, Engine, Generator, Prompt, Template, Document, SQL, Metadata, Member, Role, Permission.\r\nPRINCIPLE: Everything is an Object.\r\nIDENTIFIER: Stores Identifier Blueprint fields for generating object instance identifiers.\r\nREFERENCE: Identifier target mapping and identifier extension metadata are managed in cm_common_code (group_code = SPS_IDENTIFIER_TARGET, extension_json). Do not hardcode identifier object abbreviations.\r\nAI_GUIDE: Treat this table as the canonical Object Class definition table.\r\nREPOSITORY: Identifier target mapping and extension metadata are managed in cm_common_code (group_code=SPS_IDENTIFIER_TARGET, extension_json). Identifier Engines shall resolve Object identifier codes from the Repository. Hardcoding is prohibited.\r\nidentifier_target_code\r\n- 참조 코드그룹: SPS_IDENTIFIER_TARGET\r\n- 역할: Identifier Engine이 이 Object의 ID를 어떤 Target 규칙으로 발급할지 판단하는 기준\r\n- 예: OB, EN, AT, AP, SQ\r\n';

/* te_story_platform.sp_metadata */
ALTER TABLE `te_story_platform`.`sp_metadata`
    MODIFY COLUMN `target_type_code` varchar(99) NOT NULL COMMENT 'Metadata Target Type Code. SPS_METADATA_TARGET 공통코드를 참조한다. 모든 _code 계열 컬럼은 VARCHAR(99)를 표준으로 한다.',
    MODIFY COLUMN `metadata_type_code` varchar(99) NOT NULL COMMENT 'Metadata Type Code. SPS_METADATA_TYPE 공통코드를 참조한다. 모든 _code 계열 컬럼은 VARCHAR(99)를 표준으로 한다.',
    MODIFY COLUMN `metadata_value_type_code` varchar(99) NOT NULL DEFAULT 'STRING' COMMENT 'Metadata Value Type Code. STRING, REGEX, JSON 등의 값 유형을 식별한다. 모든 _code 계열 컬럼은 VARCHAR(99)를 표준으로 한다.',
    COMMENT = 'Story Programming Metadata Repository';

/* te_story_platform.sp_knowledge_type_hold */
ALTER TABLE `te_story_platform`.`sp_knowledge_type_hold`
    MODIFY COLUMN `knowledge_type_id` varchar(99) NOT NULL COMMENT '',
    MODIFY COLUMN `knowledge_type_code` varchar(99) NOT NULL COMMENT '',
    MODIFY COLUMN `knowledge_type_name` varchar(150) NOT NULL COMMENT '',
    MODIFY COLUMN `parent_knowledge_type_id` varchar(99) DEFAULT NULL COMMENT '',
    MODIFY COLUMN `knowledge_type_description` varchar(2000) DEFAULT NULL COMMENT '',
    MODIFY COLUMN `active_yn` char(1) NOT NULL DEFAULT 'Y' COMMENT '',
    MODIFY COLUMN `sort_no` int(11) NOT NULL DEFAULT 0 COMMENT '',
    MODIFY COLUMN `created_by` varchar(99) NOT NULL DEFAULT 'SYSTEM' COMMENT '',
    MODIFY COLUMN `created_dt` datetime NOT NULL DEFAULT current_timestamp() COMMENT '',
    MODIFY COLUMN `updated_by` varchar(99) DEFAULT NULL COMMENT '',
    MODIFY COLUMN `updated_dt` datetime DEFAULT NULL COMMENT '',
    MODIFY COLUMN `deleted_yn` char(1) NOT NULL DEFAULT 'N' COMMENT '',
    MODIFY COLUMN `deleted_by` varchar(99) DEFAULT NULL COMMENT '',
    MODIFY COLUMN `deleted_dt` datetime DEFAULT NULL COMMENT '',
    MODIFY COLUMN `change_reason` varchar(2000) DEFAULT NULL COMMENT '',
    MODIFY COLUMN `client_ip` varchar(99) DEFAULT NULL COMMENT '',
    MODIFY COLUMN `program_id` varchar(99) DEFAULT NULL COMMENT '',
    COMMENT = 'Story를 구조화된 Knowledge로 분류하기 위한 Knowledge Type System을 관리한다.';

/* te_story_platform.sp_knowledge_relationship_hold */
ALTER TABLE `te_story_platform`.`sp_knowledge_relationship_hold`
    MODIFY COLUMN `knowledge_relationship_id` varchar(99) NOT NULL COMMENT '',
    MODIFY COLUMN `source_knowledge_id` varchar(99) NOT NULL COMMENT '',
    MODIFY COLUMN `target_knowledge_id` varchar(99) NOT NULL COMMENT '',
    MODIFY COLUMN `relationship_type_code` varchar(99) NOT NULL COMMENT '',
    MODIFY COLUMN `relationship_description` varchar(2000) DEFAULT NULL COMMENT '',
    MODIFY COLUMN `active_yn` char(1) NOT NULL DEFAULT 'Y' COMMENT '',
    MODIFY COLUMN `created_by` varchar(99) NOT NULL DEFAULT 'SYSTEM' COMMENT '',
    MODIFY COLUMN `created_dt` datetime NOT NULL DEFAULT current_timestamp() COMMENT '',
    MODIFY COLUMN `updated_by` varchar(99) DEFAULT NULL COMMENT '',
    MODIFY COLUMN `updated_dt` datetime DEFAULT NULL COMMENT '',
    MODIFY COLUMN `deleted_yn` char(1) NOT NULL DEFAULT 'N' COMMENT '',
    MODIFY COLUMN `deleted_by` varchar(99) DEFAULT NULL COMMENT '',
    MODIFY COLUMN `deleted_dt` datetime DEFAULT NULL COMMENT '',
    MODIFY COLUMN `change_reason` varchar(2000) DEFAULT NULL COMMENT '',
    MODIFY COLUMN `client_ip` varchar(99) DEFAULT NULL COMMENT '',
    MODIFY COLUMN `program_id` varchar(99) DEFAULT NULL COMMENT '',
    COMMENT = 'Knowledge 사이의 의미 관계를 관리하여 Story Knowledge Graph를 구성한다.';

/* te_story_platform.sp_knowledge_hold */
ALTER TABLE `te_story_platform`.`sp_knowledge_hold`
    MODIFY COLUMN `knowledge_id` varchar(99) NOT NULL COMMENT '',
    MODIFY COLUMN `knowledge_identifier` varchar(99) NOT NULL COMMENT '',
    MODIFY COLUMN `knowledge_type_id` varchar(99) NOT NULL COMMENT '',
    MODIFY COLUMN `knowledge_name` varchar(150) NOT NULL COMMENT '',
    MODIFY COLUMN `knowledge_description` varchar(2000) DEFAULT NULL COMMENT '',
    MODIFY COLUMN `source_story_text` text DEFAULT NULL COMMENT '',
    MODIFY COLUMN `active_yn` char(1) NOT NULL DEFAULT 'Y' COMMENT '',
    MODIFY COLUMN `created_by` varchar(99) NOT NULL DEFAULT 'SYSTEM' COMMENT '',
    MODIFY COLUMN `created_dt` datetime NOT NULL DEFAULT current_timestamp() COMMENT '',
    MODIFY COLUMN `updated_by` varchar(99) DEFAULT NULL COMMENT '',
    MODIFY COLUMN `updated_dt` datetime DEFAULT NULL COMMENT '',
    MODIFY COLUMN `deleted_yn` char(1) NOT NULL DEFAULT 'N' COMMENT '',
    MODIFY COLUMN `deleted_by` varchar(99) DEFAULT NULL COMMENT '',
    MODIFY COLUMN `deleted_dt` datetime DEFAULT NULL COMMENT '',
    MODIFY COLUMN `change_reason` varchar(2000) DEFAULT NULL COMMENT '',
    MODIFY COLUMN `client_ip` varchar(99) DEFAULT NULL COMMENT '',
    MODIFY COLUMN `program_id` varchar(99) DEFAULT NULL COMMENT '',
    COMMENT = 'Story에서 추출된 구조화 Knowledge의 단위를 관리한다.';

/* te_story_platform.sp_impact_analysis_result */
ALTER TABLE `te_story_platform`.`sp_impact_analysis_result`
    MODIFY COLUMN `impact_analysis_id` varchar(99) NOT NULL COMMENT '',
    MODIFY COLUMN `change_target_text` text NOT NULL COMMENT '',
    MODIFY COLUMN `change_type_code` varchar(99) NOT NULL COMMENT '',
    MODIFY COLUMN `affected_object_type_code` varchar(99) NOT NULL COMMENT '',
    MODIFY COLUMN `affected_object_name` varchar(150) NOT NULL COMMENT '',
    MODIFY COLUMN `affected_file_path` varchar(2000) DEFAULT NULL COMMENT '',
    MODIFY COLUMN `affected_line_no` int(11) DEFAULT NULL COMMENT '',
    MODIFY COLUMN `affected_text` text DEFAULT NULL COMMENT '',
    MODIFY COLUMN `risk_level_code` varchar(99) NOT NULL DEFAULT 'MEDIUM' COMMENT '',
    MODIFY COLUMN `analysis_note` text DEFAULT NULL COMMENT '',
    MODIFY COLUMN `created_by` varchar(99) NOT NULL DEFAULT 'SYSTEM' COMMENT '',
    MODIFY COLUMN `created_dt` datetime NOT NULL DEFAULT current_timestamp() COMMENT '',
    MODIFY COLUMN `updated_by` varchar(99) DEFAULT NULL COMMENT '',
    MODIFY COLUMN `updated_dt` datetime DEFAULT NULL COMMENT '',
    MODIFY COLUMN `deleted_by` varchar(99) DEFAULT NULL COMMENT '',
    MODIFY COLUMN `deleted_dt` datetime DEFAULT NULL COMMENT '',
    MODIFY COLUMN `client_ip` varchar(99) DEFAULT NULL COMMENT '',
    MODIFY COLUMN `program_id` varchar(99) DEFAULT NULL COMMENT '',
    COMMENT = '';

/* te_story_platform.sp_identifier_sequence */
ALTER TABLE `te_story_platform`.`sp_identifier_sequence`
    MODIFY COLUMN `identifier_target_code` varchar(99) NOT NULL COMMENT '채번 대상 코드. 예: BUSINESS, DOMAIN, OBJECT, ENTITY, ATTRIBUTE, RELATIONSHIP, METADATA, SQL, DOCUMENT, API, GENERATOR, ENGINE.',
    MODIFY COLUMN `status_code` varchar(99) NOT NULL DEFAULT 'ACTIVE' COMMENT '상태 코드. ACTIVE/INACTIVE.',
    COMMENT = 'SPS Identifier Sequence Repository. Identifier Prefix는 공통코드 code 값을 사용하며 Framework 전체에서 중복될 수 없다. 변경 사유와 상세 이력은 history 테이블에서 관리한다.';

/* te_story_platform.sp_identifier_blueprint */
ALTER TABLE `te_story_platform`.`sp_identifier_blueprint`
    MODIFY COLUMN `blueprint_code` varchar(99) NOT NULL COMMENT 'Identifier Blueprint Code',
    MODIFY COLUMN `sequence_scope_code` varchar(99) NOT NULL COMMENT 'Sequence Scope Code',
    MODIFY COLUMN `status_code` varchar(99) NOT NULL DEFAULT 'ACTIVE' COMMENT 'Status Code',
    COMMENT = '\r\nPurpose:\r\nDefines Identifier Blueprint metadata for Story Programming Framework.\r\n\r\nDescription:\r\nStores identifier generation rules based on Object Level.\r\nDefines identifier pattern, date format, time format, random length and sequence policy.\r\n\r\nUsed By:\r\nDeveloper, Runtime, Identifier Engine, Repository Intelligence, Generator and AI.\r\n\r\nPolicy:\r\nRepository First.\r\nMetadata Driven.\r\nNo Hardcoding.\r\n\r\nOutput:\r\nIdentifier metadata used to generate runtime identifiers.\r\n';

/* te_story_platform.sp_execution_history */
ALTER TABLE `te_story_platform`.`sp_execution_history`
    MODIFY COLUMN `execution_history_id` varchar(99) NOT NULL COMMENT '',
    MODIFY COLUMN `trace_id` varchar(99) NOT NULL COMMENT '',
    MODIFY COLUMN `engine_code` varchar(99) NOT NULL COMMENT '',
    MODIFY COLUMN `object_code` varchar(99) NOT NULL COMMENT '',
    MODIFY COLUMN `object_id` varchar(99) DEFAULT NULL COMMENT '',
    MODIFY COLUMN `generated_identifier` varchar(99) DEFAULT NULL COMMENT '',
    MODIFY COLUMN `repository_status_code` varchar(99) DEFAULT NULL COMMENT '',
    MODIFY COLUMN `mongodb_status_code` varchar(99) DEFAULT NULL COMMENT '',
    MODIFY COLUMN `execution_status_code` varchar(99) NOT NULL COMMENT '',
    MODIFY COLUMN `history_status_code` varchar(99) NOT NULL COMMENT '',
    MODIFY COLUMN `created_dt` datetime NOT NULL DEFAULT current_timestamp() COMMENT '',
    COMMENT = '';

/* te_story_platform.sp_erd */
ALTER TABLE `te_story_platform`.`sp_erd`
    MODIFY COLUMN `erd_code` varchar(99) NOT NULL COMMENT 'ERD Code',
    MODIFY COLUMN `business_code` varchar(99) NOT NULL COMMENT 'Business Code',
    MODIFY COLUMN `domain_code` varchar(99) NOT NULL COMMENT 'Domain Code',
    COMMENT = 'ERD Repository';

/* te_story_platform.sp_entity */
ALTER TABLE `te_story_platform`.`sp_entity`
    MODIFY COLUMN `business_code` varchar(99) NOT NULL COMMENT 'Business Code. Entity가 어느 Business에 속하는지 식별하기 위해 사용한다. 참조: te_story_platform.sp_business.business_code',
    MODIFY COLUMN `domain_code` varchar(99) NOT NULL COMMENT 'Entity가 어느 SPS Domain 공통코드에 속하는지 식별하기 위해 사용한다. (te_common.cm_common_code, group_code=SPS_DOMAIN)',
    MODIFY COLUMN `entity_type_code` varchar(99) NOT NULL DEFAULT 'MASTER' COMMENT 'Entity Type Code. Entity의 성격을 구분하고 Engine과 Generator의 처리 방식을 결정하기 위해 사용한다.',
    COMMENT = 'Story Programming Table Definition Repository';

/* te_story_platform.sp_domain */
ALTER TABLE `te_story_platform`.`sp_domain`
    MODIFY COLUMN `domain_code` varchar(99) NOT NULL COMMENT 'Domain Code',
    MODIFY COLUMN `business_code` varchar(99) NOT NULL COMMENT 'Business Code',
    COMMENT = 'Story Programming Domain Dictionary';

/* te_story_platform.sp_business */
ALTER TABLE `te_story_platform`.`sp_business`
    MODIFY COLUMN `business_code` varchar(99) NOT NULL COMMENT 'Business Code',
    COMMENT = 'Story Platform Business Master';

/* te_story_platform.sp_attribute */
ALTER TABLE `te_story_platform`.`sp_attribute`
    COMMENT = 'Story Programming Column Definition Repository';

/* te_health_companion.fb_feedback */
ALTER TABLE `te_health_companion`.`fb_feedback`
    MODIFY COLUMN `feedback_code` varchar(99) NOT NULL COMMENT '피드백 코드',
    MODIFY COLUMN `feedback_type_code` varchar(99) NOT NULL COMMENT '피드백 유형 코드',
    MODIFY COLUMN `status_code` varchar(99) NOT NULL DEFAULT 'ACTIVE' COMMENT '상태 코드',
    MODIFY COLUMN `created_dt` datetime NOT NULL DEFAULT current_timestamp() COMMENT '',
    MODIFY COLUMN `created_by` varchar(99) NOT NULL DEFAULT 'SYSTEM' COMMENT '',
    MODIFY COLUMN `updated_dt` datetime NOT NULL DEFAULT current_timestamp() ON UPDATE current_timestamp() COMMENT '',
    MODIFY COLUMN `updated_by` varchar(99) NOT NULL DEFAULT 'SYSTEM' COMMENT '',
    MODIFY COLUMN `deleted_by` varchar(99) DEFAULT NULL COMMENT '',
    MODIFY COLUMN `deleted_dt` datetime DEFAULT NULL COMMENT '',
    MODIFY COLUMN `program_id` varchar(99) DEFAULT NULL COMMENT '',
    MODIFY COLUMN `client_ip` varchar(99) DEFAULT NULL COMMENT '',
    COMMENT = '피드백';

/* te_health_companion.dc_decision_detail */
ALTER TABLE `te_health_companion`.`dc_decision_detail`
    MODIFY COLUMN `input_field_code` varchar(99) DEFAULT NULL COMMENT '입력 필드 코드',
    MODIFY COLUMN `condition_result_code` varchar(99) DEFAULT NULL COMMENT '조건 결과 코드',
    MODIFY COLUMN `created_dt` datetime NOT NULL DEFAULT current_timestamp() COMMENT '',
    MODIFY COLUMN `created_by` varchar(99) NOT NULL DEFAULT 'SYSTEM' COMMENT '',
    MODIFY COLUMN `updated_dt` datetime NOT NULL DEFAULT current_timestamp() ON UPDATE current_timestamp() COMMENT '',
    MODIFY COLUMN `updated_by` varchar(99) NOT NULL DEFAULT 'SYSTEM' COMMENT '',
    MODIFY COLUMN `deleted_by` varchar(99) DEFAULT NULL COMMENT '',
    MODIFY COLUMN `deleted_dt` datetime DEFAULT NULL COMMENT '',
    MODIFY COLUMN `program_id` varchar(99) DEFAULT NULL COMMENT '',
    MODIFY COLUMN `client_ip` varchar(99) DEFAULT NULL COMMENT '',
    COMMENT = '판단 상세';

/* te_health_companion.dc_decision */
ALTER TABLE `te_health_companion`.`dc_decision`
    MODIFY COLUMN `decision_code` varchar(99) NOT NULL COMMENT '판단 코드',
    MODIFY COLUMN `decision_type_code` varchar(99) NOT NULL COMMENT '판단 유형 코드',
    MODIFY COLUMN `decision_result_code` varchar(99) NOT NULL COMMENT '판단 결과 코드',
    MODIFY COLUMN `status_code` varchar(99) NOT NULL DEFAULT 'ACTIVE' COMMENT '상태 코드',
    MODIFY COLUMN `created_dt` datetime NOT NULL DEFAULT current_timestamp() COMMENT '',
    MODIFY COLUMN `created_by` varchar(99) NOT NULL DEFAULT 'SYSTEM' COMMENT '',
    MODIFY COLUMN `updated_dt` datetime NOT NULL DEFAULT current_timestamp() ON UPDATE current_timestamp() COMMENT '',
    MODIFY COLUMN `updated_by` varchar(99) NOT NULL DEFAULT 'SYSTEM' COMMENT '',
    MODIFY COLUMN `deleted_by` varchar(99) DEFAULT NULL COMMENT '',
    MODIFY COLUMN `deleted_dt` datetime DEFAULT NULL COMMENT '',
    MODIFY COLUMN `program_id` varchar(99) DEFAULT NULL COMMENT '',
    MODIFY COLUMN `client_ip` varchar(99) DEFAULT NULL COMMENT '',
    COMMENT = '판단';

/* te_health_companion.at_audit */
ALTER TABLE `te_health_companion`.`at_audit`
    MODIFY COLUMN `audit_code` varchar(99) NOT NULL COMMENT '감사 코드',
    MODIFY COLUMN `audit_type_code` varchar(99) NOT NULL COMMENT '감사 유형 코드',
    MODIFY COLUMN `business_domain_code` varchar(99) DEFAULT NULL COMMENT '업무 도메인 코드',
    MODIFY COLUMN `audit_result_code` varchar(99) NOT NULL DEFAULT 'SUCCESS' COMMENT '감사 결과 코드',
    MODIFY COLUMN `ai_provider_code` varchar(99) DEFAULT NULL COMMENT 'AI 제공자 코드',
    MODIFY COLUMN `created_dt` datetime NOT NULL DEFAULT current_timestamp() COMMENT '',
    MODIFY COLUMN `created_by` varchar(99) NOT NULL DEFAULT 'SYSTEM' COMMENT '',
    MODIFY COLUMN `updated_dt` datetime NOT NULL DEFAULT current_timestamp() ON UPDATE current_timestamp() COMMENT '',
    MODIFY COLUMN `updated_by` varchar(99) NOT NULL DEFAULT 'SYSTEM' COMMENT '',
    MODIFY COLUMN `deleted_by` varchar(99) DEFAULT NULL COMMENT '',
    MODIFY COLUMN `deleted_dt` datetime DEFAULT NULL COMMENT '',
    MODIFY COLUMN `program_id` varchar(99) DEFAULT NULL COMMENT '',
    MODIFY COLUMN `client_ip` varchar(99) DEFAULT NULL COMMENT '',
    COMMENT = '감사';

/* te_health_companion.ac_action */
ALTER TABLE `te_health_companion`.`ac_action`
    MODIFY COLUMN `action_code` varchar(99) NOT NULL COMMENT '실행 코드',
    MODIFY COLUMN `action_type_code` varchar(99) NOT NULL COMMENT '실행 유형 코드',
    MODIFY COLUMN `action_status_code` varchar(99) NOT NULL DEFAULT 'READY' COMMENT '실행 상태 코드',
    MODIFY COLUMN `action_target_type_code` varchar(99) DEFAULT NULL COMMENT '실행 대상 유형 코드',
    MODIFY COLUMN `result_code` varchar(99) DEFAULT NULL COMMENT '결과 코드',
    MODIFY COLUMN `created_dt` datetime NOT NULL DEFAULT current_timestamp() COMMENT '',
    MODIFY COLUMN `created_by` varchar(99) NOT NULL DEFAULT 'SYSTEM' COMMENT '',
    MODIFY COLUMN `updated_dt` datetime NOT NULL DEFAULT current_timestamp() ON UPDATE current_timestamp() COMMENT '',
    MODIFY COLUMN `updated_by` varchar(99) NOT NULL DEFAULT 'SYSTEM' COMMENT '',
    MODIFY COLUMN `deleted_by` varchar(99) DEFAULT NULL COMMENT '',
    MODIFY COLUMN `deleted_dt` datetime DEFAULT NULL COMMENT '',
    MODIFY COLUMN `program_id` varchar(99) DEFAULT NULL COMMENT '',
    MODIFY COLUMN `client_ip` varchar(99) DEFAULT NULL COMMENT '',
    COMMENT = '실행';

/* Restore Foreign Keys */
ALTER TABLE `te_common`.`cm_common_code` ADD CONSTRAINT `fk_cm_common_code_group` FOREIGN KEY (`group_code`) REFERENCES `te_common`.`cm_common_code_group` (`group_code`) ON UPDATE RESTRICT ON DELETE RESTRICT;
ALTER TABLE `te_common`.`cm_locale` ADD CONSTRAINT `fk_cm_locale_country` FOREIGN KEY (`country_code`) REFERENCES `te_common`.`cm_country` (`country_code`) ON UPDATE NO ACTION ON DELETE NO ACTION;
ALTER TABLE `te_common`.`cm_locale` ADD CONSTRAINT `fk_cm_locale_language` FOREIGN KEY (`language_code`) REFERENCES `te_common`.`cm_language` (`language_code`) ON UPDATE NO ACTION ON DELETE NO ACTION;
ALTER TABLE `te_common`.`cm_login_history` ADD CONSTRAINT `fk_cm_login_history_member` FOREIGN KEY (`member_id`) REFERENCES `te_common`.`cm_member` (`member_id`) ON UPDATE NO ACTION ON DELETE NO ACTION;
ALTER TABLE `te_common`.`cm_member_private` ADD CONSTRAINT `fk_cm_member_private_member` FOREIGN KEY (`member_id`) REFERENCES `te_common`.`cm_member` (`member_id`) ON UPDATE NO ACTION ON DELETE NO ACTION;
ALTER TABLE `te_common`.`cm_member_role` ADD CONSTRAINT `fk_cm_member_role_member` FOREIGN KEY (`member_id`) REFERENCES `te_common`.`cm_member` (`member_id`) ON UPDATE NO ACTION ON DELETE NO ACTION;
ALTER TABLE `te_common`.`cm_member_role` ADD CONSTRAINT `fk_cm_member_role_role` FOREIGN KEY (`role_id`) REFERENCES `te_common`.`cm_role` (`role_id`) ON UPDATE NO ACTION ON DELETE NO ACTION;
ALTER TABLE `te_common`.`cm_role_rule` ADD CONSTRAINT `fk_cm_role_rule_role` FOREIGN KEY (`role_id`) REFERENCES `te_common`.`cm_role` (`role_id`) ON UPDATE RESTRICT ON DELETE RESTRICT;
ALTER TABLE `te_common`.`cm_sequence_definition` ADD CONSTRAINT `fk_cm_sequence_definition_format` FOREIGN KEY (`format_code`) REFERENCES `te_common`.`cm_sequence_format_definition` (`format_code`) ON UPDATE RESTRICT ON DELETE RESTRICT;
ALTER TABLE `te_common`.`cm_sequence_definition` ADD CONSTRAINT `fk_cm_sequence_definition_policy` FOREIGN KEY (`policy_code`) REFERENCES `te_common`.`cm_sequence_policy_definition` (`policy_code`) ON UPDATE RESTRICT ON DELETE RESTRICT;
ALTER TABLE `te_common`.`cm_sequence_rule` ADD CONSTRAINT `fk_cm_sequence_rule_format` FOREIGN KEY (`format_code`) REFERENCES `te_common`.`cm_sequence_format` (`format_code`) ON UPDATE RESTRICT ON DELETE RESTRICT;
ALTER TABLE `te_common`.`cm_sequence_rule` ADD CONSTRAINT `fk_cm_sequence_rule_policy` FOREIGN KEY (`policy_code`) REFERENCES `te_common`.`cm_sequence_policy` (`policy_code`) ON UPDATE RESTRICT ON DELETE RESTRICT;
ALTER TABLE `te_common`.`md_object` ADD CONSTRAINT `fk_md_object_type` FOREIGN KEY (`object_type_group_code`, `object_type_code`) REFERENCES `te_common`.`cm_common_code` (`group_code`, `code`) ON UPDATE RESTRICT ON DELETE RESTRICT;
ALTER TABLE `te_common`.`md_relation` ADD CONSTRAINT `fk_md_relation_source` FOREIGN KEY (`source_md_object_id`) REFERENCES `te_common`.`md_object` (`md_object_id`) ON UPDATE RESTRICT ON DELETE RESTRICT;
ALTER TABLE `te_common`.`md_relation` ADD CONSTRAINT `fk_md_relation_target` FOREIGN KEY (`target_md_object_id`) REFERENCES `te_common`.`md_object` (`md_object_id`) ON UPDATE RESTRICT ON DELETE RESTRICT;
ALTER TABLE `te_common`.`system_menu_button` ADD CONSTRAINT `fk_system_menu_button_menu` FOREIGN KEY (`menu_code`) REFERENCES `te_common`.`system_menu` (`menu_code`) ON UPDATE RESTRICT ON DELETE RESTRICT;
ALTER TABLE `te_common`.`system_menu_button_crud_permission` ADD CONSTRAINT `fk_button_permission_button` FOREIGN KEY (`button_code`) REFERENCES `te_common`.`system_menu_button` (`button_code`) ON UPDATE RESTRICT ON DELETE RESTRICT;
ALTER TABLE `te_common`.`system_menu_button_crud_permission` ADD CONSTRAINT `fk_button_permission_menu` FOREIGN KEY (`menu_code`) REFERENCES `te_common`.`system_menu` (`menu_code`) ON UPDATE RESTRICT ON DELETE RESTRICT;
ALTER TABLE `te_story_platform`.`sp_knowledge_hold` ADD CONSTRAINT `fk_sp_knowledge_type` FOREIGN KEY (`knowledge_type_id`) REFERENCES `te_story_platform`.`sp_knowledge_type_hold` (`knowledge_type_id`) ON UPDATE RESTRICT ON DELETE RESTRICT;
ALTER TABLE `te_story_platform`.`sp_knowledge_relationship_hold` ADD CONSTRAINT `fk_sp_knowledge_relationship_source` FOREIGN KEY (`source_knowledge_id`) REFERENCES `te_story_platform`.`sp_knowledge_hold` (`knowledge_id`) ON UPDATE RESTRICT ON DELETE RESTRICT;
ALTER TABLE `te_story_platform`.`sp_knowledge_relationship_hold` ADD CONSTRAINT `fk_sp_knowledge_relationship_target` FOREIGN KEY (`target_knowledge_id`) REFERENCES `te_story_platform`.`sp_knowledge_hold` (`knowledge_id`) ON UPDATE RESTRICT ON DELETE RESTRICT;
ALTER TABLE `te_story_platform`.`sp_knowledge_type_hold` ADD CONSTRAINT `fk_sp_knowledge_type_parent` FOREIGN KEY (`parent_knowledge_type_id`) REFERENCES `te_story_platform`.`sp_knowledge_type_hold` (`knowledge_type_id`) ON UPDATE RESTRICT ON DELETE RESTRICT;

SET FOREIGN_KEY_CHECKS = 1;

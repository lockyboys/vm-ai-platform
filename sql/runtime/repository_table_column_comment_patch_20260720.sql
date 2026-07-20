/*
File Name : repository_table_column_comment_patch_20260720.sql
Purpose   : Full live Repository TABLE/COLUMN COMMENT maintenance
Tables    : 75 live / 75 changed
Columns   : 1285 live / 839 changed
FK Rebuild: 22 constraints
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

/* te_health_companion.ac_action */
ALTER TABLE `te_health_companion`.`ac_action`
    MODIFY COLUMN `action_code` varchar(99) NOT NULL COMMENT '실행 코드 REFERENCE: UNRESOLVED. 공통코드 Group 또는 Master Repository 연결을 Metadata에서 확정해야 한다.',
    MODIFY COLUMN `action_type_code` varchar(99) NOT NULL COMMENT '실행 유형 코드 REFERENCE: te_common.cm_common_code의 group_code=CHANGE_HISTORY_ACTION_TYPE. Generator, Engine 및 AI는 해당 Group의 code를 해석한다.',
    MODIFY COLUMN `action_status_code` varchar(99) NOT NULL DEFAULT 'READY' COMMENT '실행 상태 코드 REFERENCE: te_common.cm_common_code의 group_code=STATUS_CODE. Generator, Engine 및 AI는 해당 Group의 code를 해석한다.',
    MODIFY COLUMN `action_target_type_code` varchar(99) DEFAULT NULL COMMENT '실행 대상 유형 코드 REFERENCE: UNRESOLVED. 공통코드 Group 또는 Master Repository 연결을 Metadata에서 확정해야 한다.',
    MODIFY COLUMN `result_code` varchar(99) DEFAULT NULL COMMENT '결과 코드 REFERENCE: UNRESOLVED. 공통코드 Group 또는 Master Repository 연결을 Metadata에서 확정해야 한다.',
    MODIFY COLUMN `created_dt` datetime NOT NULL DEFAULT current_timestamp() COMMENT 'Object 최초 생성 일시.',
    MODIFY COLUMN `created_by` varchar(99) NOT NULL DEFAULT 'SYSTEM' COMMENT 'Object를 최초 생성한 사용자 또는 실행 주체 식별자.',
    MODIFY COLUMN `updated_dt` datetime NOT NULL DEFAULT current_timestamp() ON UPDATE current_timestamp() COMMENT 'Object 최종 수정 일시.',
    MODIFY COLUMN `updated_by` varchar(99) NOT NULL DEFAULT 'SYSTEM' COMMENT 'Object를 최종 수정한 사용자 또는 실행 주체 식별자.',
    MODIFY COLUMN `deleted_by` varchar(99) DEFAULT NULL COMMENT 'Object를 논리 삭제한 사용자 또는 실행 주체 식별자.',
    MODIFY COLUMN `deleted_dt` datetime DEFAULT NULL COMMENT 'Object 논리 삭제 처리 일시.',
    MODIFY COLUMN `program_id` varchar(99) DEFAULT NULL COMMENT 'Object 생성·수정·삭제를 수행한 Program 식별자.',
    MODIFY COLUMN `client_ip` varchar(99) DEFAULT NULL COMMENT 'Object 변경 요청이 발생한 Client IP 주소.',
    COMMENT = 'PURPOSE: 건강동행 판단 결과에 따라 수행되는 Action과 처리 상태를 관리한다. ROLE: HEALTH_COMPANION 공식 Repository. SSOT: 해당 Object 정의와 관계의 단일 원천. ENGINE_GUIDE: Generator, Engine 및 AI는 이 테이블을 Repository First로 해석하며 값과 규칙의 Hardcoding을 금지한다.';

/* te_health_companion.at_audit */
ALTER TABLE `te_health_companion`.`at_audit`
    MODIFY COLUMN `audit_code` varchar(99) NOT NULL COMMENT '감사 코드 REFERENCE: UNRESOLVED. 공통코드 Group 또는 Master Repository 연결을 Metadata에서 확정해야 한다.',
    MODIFY COLUMN `audit_type_code` varchar(99) NOT NULL COMMENT '감사 유형 코드 REFERENCE: te_common.cm_common_code의 group_code=CHANGE_HISTORY_ACTION_TYPE. Generator, Engine 및 AI는 해당 Group의 code를 해석한다.',
    MODIFY COLUMN `business_domain_code` varchar(99) DEFAULT NULL COMMENT '업무 도메인 코드 REFERENCE: COMMON.cm_business_domain(business_domain_code). 해당 Master Repository를 공식 연결 원천으로 사용한다.',
    MODIFY COLUMN `audit_result_code` varchar(99) NOT NULL DEFAULT 'SUCCESS' COMMENT '감사 결과 코드 REFERENCE: UNRESOLVED. 공통코드 Group 또는 Master Repository 연결을 Metadata에서 확정해야 한다.',
    MODIFY COLUMN `ai_provider_code` varchar(99) DEFAULT NULL COMMENT 'AI 제공자 코드 REFERENCE: UNRESOLVED. 공통코드 Group 또는 Master Repository 연결을 Metadata에서 확정해야 한다.',
    MODIFY COLUMN `created_dt` datetime NOT NULL DEFAULT current_timestamp() COMMENT 'Object 최초 생성 일시.',
    MODIFY COLUMN `created_by` varchar(99) NOT NULL DEFAULT 'SYSTEM' COMMENT 'Object를 최초 생성한 사용자 또는 실행 주체 식별자.',
    MODIFY COLUMN `updated_dt` datetime NOT NULL DEFAULT current_timestamp() ON UPDATE current_timestamp() COMMENT 'Object 최종 수정 일시.',
    MODIFY COLUMN `updated_by` varchar(99) NOT NULL DEFAULT 'SYSTEM' COMMENT 'Object를 최종 수정한 사용자 또는 실행 주체 식별자.',
    MODIFY COLUMN `deleted_by` varchar(99) DEFAULT NULL COMMENT 'Object를 논리 삭제한 사용자 또는 실행 주체 식별자.',
    MODIFY COLUMN `deleted_dt` datetime DEFAULT NULL COMMENT 'Object 논리 삭제 처리 일시.',
    MODIFY COLUMN `program_id` varchar(99) DEFAULT NULL COMMENT 'Object 생성·수정·삭제를 수행한 Program 식별자.',
    MODIFY COLUMN `client_ip` varchar(99) DEFAULT NULL COMMENT 'Object 변경 요청이 발생한 Client IP 주소.',
    COMMENT = 'PURPOSE: 건강동행 Engine 판단과 실행 결과의 감사 기록을 관리한다. ROLE: HEALTH_COMPANION 공식 Repository. SSOT: 해당 이력과 실행 결과의 공식 원천. ENGINE_GUIDE: Generator, Engine 및 AI는 이 테이블을 Repository First로 해석하며 값과 규칙의 Hardcoding을 금지한다.';

/* te_health_companion.dc_decision */
ALTER TABLE `te_health_companion`.`dc_decision`
    MODIFY COLUMN `decision_code` varchar(99) NOT NULL COMMENT '판단 코드 REFERENCE: UNRESOLVED. 공통코드 Group 또는 Master Repository 연결을 Metadata에서 확정해야 한다.',
    MODIFY COLUMN `decision_type_code` varchar(99) NOT NULL COMMENT '판단 유형 코드 REFERENCE: UNRESOLVED. 공통코드 Group 또는 Master Repository 연결을 Metadata에서 확정해야 한다.',
    MODIFY COLUMN `decision_result_code` varchar(99) NOT NULL COMMENT '판단 결과 코드 REFERENCE: UNRESOLVED. 공통코드 Group 또는 Master Repository 연결을 Metadata에서 확정해야 한다.',
    MODIFY COLUMN `status_code` varchar(99) NOT NULL DEFAULT 'ACTIVE' COMMENT '상태 코드 REFERENCE: te_common.cm_common_code의 group_code=STATUS_CODE. Generator, Engine 및 AI는 해당 Group의 code를 해석한다.',
    MODIFY COLUMN `created_dt` datetime NOT NULL DEFAULT current_timestamp() COMMENT 'Object 최초 생성 일시.',
    MODIFY COLUMN `created_by` varchar(99) NOT NULL DEFAULT 'SYSTEM' COMMENT 'Object를 최초 생성한 사용자 또는 실행 주체 식별자.',
    MODIFY COLUMN `updated_dt` datetime NOT NULL DEFAULT current_timestamp() ON UPDATE current_timestamp() COMMENT 'Object 최종 수정 일시.',
    MODIFY COLUMN `updated_by` varchar(99) NOT NULL DEFAULT 'SYSTEM' COMMENT 'Object를 최종 수정한 사용자 또는 실행 주체 식별자.',
    MODIFY COLUMN `deleted_by` varchar(99) DEFAULT NULL COMMENT 'Object를 논리 삭제한 사용자 또는 실행 주체 식별자.',
    MODIFY COLUMN `deleted_dt` datetime DEFAULT NULL COMMENT 'Object 논리 삭제 처리 일시.',
    MODIFY COLUMN `program_id` varchar(99) DEFAULT NULL COMMENT 'Object 생성·수정·삭제를 수행한 Program 식별자.',
    MODIFY COLUMN `client_ip` varchar(99) DEFAULT NULL COMMENT 'Object 변경 요청이 발생한 Client IP 주소.',
    COMMENT = 'PURPOSE: 건강동행 Rule과 Evidence 기반 Decision 결과를 관리한다. ROLE: HEALTH_COMPANION 공식 Repository. SSOT: 해당 Object 정의와 관계의 단일 원천. ENGINE_GUIDE: Generator, Engine 및 AI는 이 테이블을 Repository First로 해석하며 값과 규칙의 Hardcoding을 금지한다.';

/* te_health_companion.dc_decision_detail */
ALTER TABLE `te_health_companion`.`dc_decision_detail`
    MODIFY COLUMN `input_field_code` varchar(99) DEFAULT NULL COMMENT '입력 필드 코드 REFERENCE: UNRESOLVED. 공통코드 Group 또는 Master Repository 연결을 Metadata에서 확정해야 한다.',
    MODIFY COLUMN `condition_result_code` varchar(99) DEFAULT NULL COMMENT '조건 결과 코드 REFERENCE: UNRESOLVED. 공통코드 Group 또는 Master Repository 연결을 Metadata에서 확정해야 한다.',
    MODIFY COLUMN `created_dt` datetime NOT NULL DEFAULT current_timestamp() COMMENT 'Object 최초 생성 일시.',
    MODIFY COLUMN `created_by` varchar(99) NOT NULL DEFAULT 'SYSTEM' COMMENT 'Object를 최초 생성한 사용자 또는 실행 주체 식별자.',
    MODIFY COLUMN `updated_dt` datetime NOT NULL DEFAULT current_timestamp() ON UPDATE current_timestamp() COMMENT 'Object 최종 수정 일시.',
    MODIFY COLUMN `updated_by` varchar(99) NOT NULL DEFAULT 'SYSTEM' COMMENT 'Object를 최종 수정한 사용자 또는 실행 주체 식별자.',
    MODIFY COLUMN `deleted_by` varchar(99) DEFAULT NULL COMMENT 'Object를 논리 삭제한 사용자 또는 실행 주체 식별자.',
    MODIFY COLUMN `deleted_dt` datetime DEFAULT NULL COMMENT 'Object 논리 삭제 처리 일시.',
    MODIFY COLUMN `program_id` varchar(99) DEFAULT NULL COMMENT 'Object 생성·수정·삭제를 수행한 Program 식별자.',
    MODIFY COLUMN `client_ip` varchar(99) DEFAULT NULL COMMENT 'Object 변경 요청이 발생한 Client IP 주소.',
    COMMENT = 'PURPOSE: Decision에 사용된 입력 Field와 조건 평가 상세를 관리한다. ROLE: HEALTH_COMPANION 공식 Repository. SSOT: 해당 Object 정의와 관계의 단일 원천. ENGINE_GUIDE: Generator, Engine 및 AI는 이 테이블을 Repository First로 해석하며 값과 규칙의 Hardcoding을 금지한다.';

/* te_health_companion.fb_feedback */
ALTER TABLE `te_health_companion`.`fb_feedback`
    MODIFY COLUMN `feedback_code` varchar(99) NOT NULL COMMENT '피드백 코드 REFERENCE: UNRESOLVED. 공통코드 Group 또는 Master Repository 연결을 Metadata에서 확정해야 한다.',
    MODIFY COLUMN `feedback_type_code` varchar(99) NOT NULL COMMENT '피드백 유형 코드 REFERENCE: UNRESOLVED. 공통코드 Group 또는 Master Repository 연결을 Metadata에서 확정해야 한다.',
    MODIFY COLUMN `status_code` varchar(99) NOT NULL DEFAULT 'ACTIVE' COMMENT '상태 코드 REFERENCE: te_common.cm_common_code의 group_code=STATUS_CODE. Generator, Engine 및 AI는 해당 Group의 code를 해석한다.',
    MODIFY COLUMN `created_dt` datetime NOT NULL DEFAULT current_timestamp() COMMENT 'Object 최초 생성 일시.',
    MODIFY COLUMN `created_by` varchar(99) NOT NULL DEFAULT 'SYSTEM' COMMENT 'Object를 최초 생성한 사용자 또는 실행 주체 식별자.',
    MODIFY COLUMN `updated_dt` datetime NOT NULL DEFAULT current_timestamp() ON UPDATE current_timestamp() COMMENT 'Object 최종 수정 일시.',
    MODIFY COLUMN `updated_by` varchar(99) NOT NULL DEFAULT 'SYSTEM' COMMENT 'Object를 최종 수정한 사용자 또는 실행 주체 식별자.',
    MODIFY COLUMN `deleted_by` varchar(99) DEFAULT NULL COMMENT 'Object를 논리 삭제한 사용자 또는 실행 주체 식별자.',
    MODIFY COLUMN `deleted_dt` datetime DEFAULT NULL COMMENT 'Object 논리 삭제 처리 일시.',
    MODIFY COLUMN `program_id` varchar(99) DEFAULT NULL COMMENT 'Object 생성·수정·삭제를 수행한 Program 식별자.',
    MODIFY COLUMN `client_ip` varchar(99) DEFAULT NULL COMMENT 'Object 변경 요청이 발생한 Client IP 주소.',
    COMMENT = 'PURPOSE: 사용자의 Decision·Action Feedback과 평가 결과를 관리한다. ROLE: HEALTH_COMPANION 공식 Repository. SSOT: 해당 Object 정의와 관계의 단일 원천. ENGINE_GUIDE: Generator, Engine 및 AI는 이 테이블을 Repository First로 해석하며 값과 규칙의 Hardcoding을 금지한다.';

/* te_story_platform.sp_attribute */
ALTER TABLE `te_story_platform`.`sp_attribute`
    COMMENT = 'PURPOSE: Story Programming Entity를 구성하는 Column Attribute 정의를 관리한다. ROLE: STORY_PLATFORM 공식 Repository. SSOT: 해당 Object 정의와 관계의 단일 원천. ENGINE_GUIDE: Generator, Engine 및 AI는 이 테이블을 Repository First로 해석하며 값과 규칙의 Hardcoding을 금지한다.';

/* te_story_platform.sp_business */
ALTER TABLE `te_story_platform`.`sp_business`
    MODIFY COLUMN `business_code` varchar(99) NOT NULL COMMENT 'Business Code REFERENCE: te_common.cm_common_code의 group_code=CM_BUSINESS. Generator, Engine 및 AI는 해당 Group의 code를 해석한다.',
    COMMENT = 'PURPOSE: Story Programming 최상위 Business Classification을 관리한다. ROLE: STORY_PLATFORM 공식 Repository. SSOT: 해당 Object 정의와 관계의 단일 원천. ENGINE_GUIDE: Generator, Engine 및 AI는 이 테이블을 Repository First로 해석하며 값과 규칙의 Hardcoding을 금지한다.';

/* te_story_platform.sp_domain */
ALTER TABLE `te_story_platform`.`sp_domain`
    MODIFY COLUMN `domain_code` varchar(99) NOT NULL COMMENT 'Domain Code REFERENCE: UNRESOLVED. 공통코드 Group 또는 Master Repository 연결을 Metadata에서 확정해야 한다.',
    MODIFY COLUMN `business_code` varchar(99) NOT NULL COMMENT 'Business Code REFERENCE: UNRESOLVED. 공통코드 Group 또는 Master Repository 연결을 Metadata에서 확정해야 한다.',
    COMMENT = 'PURPOSE: Business 하위 Domain의 코드, 명칭 및 분류를 관리한다. ROLE: STORY_PLATFORM 공식 Repository. SSOT: 해당 Object 정의와 관계의 단일 원천. ENGINE_GUIDE: Generator, Engine 및 AI는 이 테이블을 Repository First로 해석하며 값과 규칙의 Hardcoding을 금지한다.';

/* te_story_platform.sp_entity */
ALTER TABLE `te_story_platform`.`sp_entity`
    MODIFY COLUMN `business_code` varchar(99) NOT NULL COMMENT 'Business Code. Entity가 어느 Business에 속하는지 식별하기 위해 사용한다. 참조: te_story_platform.sp_business.business_code REFERENCE: UNRESOLVED. 공통코드 Group 또는 Master Repository 연결을 Metadata에서 확정해야 한다.',
    MODIFY COLUMN `domain_code` varchar(99) NOT NULL COMMENT 'Entity가 어느 SPS Domain 공통코드에 속하는지 식별하기 위해 사용한다. (te_common.cm_common_code, group_code=SPS_DOMAIN) REFERENCE: UNRESOLVED. 공통코드 Group 또는 Master Repository 연결을 Metadata에서 확정해야 한다.',
    MODIFY COLUMN `entity_type_code` varchar(99) NOT NULL DEFAULT 'MASTER' COMMENT 'Entity Type Code. Entity의 성격을 구분하고 Engine과 Generator의 처리 방식을 결정하기 위해 사용한다. REFERENCE: UNRESOLVED. 공통코드 Group 또는 Master Repository 연결을 Metadata에서 확정해야 한다.',
    COMMENT = 'PURPOSE: Repository Table에 대응하는 Entity Object 정의를 관리한다. ROLE: STORY_PLATFORM 공식 Repository. SSOT: 해당 Object 정의와 관계의 단일 원천. ENGINE_GUIDE: Generator, Engine 및 AI는 이 테이블을 Repository First로 해석하며 값과 규칙의 Hardcoding을 금지한다.';

/* te_story_platform.sp_erd */
ALTER TABLE `te_story_platform`.`sp_erd`
    MODIFY COLUMN `erd_code` varchar(99) NOT NULL COMMENT 'ERD Code REFERENCE: UNRESOLVED. 공통코드 Group 또는 Master Repository 연결을 Metadata에서 확정해야 한다.',
    MODIFY COLUMN `business_code` varchar(99) NOT NULL COMMENT 'Business Code REFERENCE: UNRESOLVED. 공통코드 Group 또는 Master Repository 연결을 Metadata에서 확정해야 한다.',
    MODIFY COLUMN `domain_code` varchar(99) NOT NULL COMMENT 'Domain Code REFERENCE: UNRESOLVED. 공통코드 Group 또는 Master Repository 연결을 Metadata에서 확정해야 한다.',
    COMMENT = 'PURPOSE: Business·Domain별 ERD Object와 구조를 관리한다. ROLE: STORY_PLATFORM 공식 Repository. SSOT: 해당 Object 정의와 관계의 단일 원천. ENGINE_GUIDE: Generator, Engine 및 AI는 이 테이블을 Repository First로 해석하며 값과 규칙의 Hardcoding을 금지한다.';

/* te_story_platform.sp_execution_history */
ALTER TABLE `te_story_platform`.`sp_execution_history`
    MODIFY COLUMN `execution_history_id` varchar(99) NOT NULL COMMENT 'Execution History Id 식별자. sp_execution_history Object와 관련 Object를 식별하거나 연결한다.',
    MODIFY COLUMN `trace_id` varchar(99) NOT NULL COMMENT 'Trace Id 식별자. sp_execution_history Object와 관련 Object를 식별하거나 연결한다.',
    MODIFY COLUMN `engine_code` varchar(99) NOT NULL COMMENT 'Engine Code 코드. Repository Metadata가 정의한 코드 체계로 관리한다. REFERENCE: te_common.cm_common_code의 group_code=ENGINE_TYPE. Generator, Engine 및 AI는 해당 Group의 code를 해석한다.',
    MODIFY COLUMN `object_code` varchar(99) NOT NULL COMMENT 'Object Code 코드. Repository Metadata가 정의한 코드 체계로 관리한다. REFERENCE: STORY_PLATFORM.sp_object(object_code). 해당 Master Repository를 공식 연결 원천으로 사용한다.',
    MODIFY COLUMN `object_id` varchar(99) DEFAULT NULL COMMENT 'Object Id 식별자. sp_execution_history Object와 관련 Object를 식별하거나 연결한다.',
    MODIFY COLUMN `generated_identifier` varchar(99) DEFAULT NULL COMMENT 'Generated Identifier 값. sp_execution_history Object의 해당 속성을 관리한다.',
    MODIFY COLUMN `repository_status_code` varchar(99) DEFAULT NULL COMMENT 'Repository Status Code 코드. Repository Metadata가 정의한 코드 체계로 관리한다. REFERENCE: te_common.cm_common_code의 group_code=REPOSITORY_STATUS. Generator, Engine 및 AI는 해당 Group의 code를 해석한다.',
    MODIFY COLUMN `mongodb_status_code` varchar(99) DEFAULT NULL COMMENT 'Mongodb Status Code 코드. Repository Metadata가 정의한 코드 체계로 관리한다. REFERENCE: UNRESOLVED. 공통코드 Group 또는 Master Repository 연결을 Metadata에서 확정해야 한다.',
    MODIFY COLUMN `execution_status_code` varchar(99) NOT NULL COMMENT 'Execution Status Code 코드. Repository Metadata가 정의한 코드 체계로 관리한다. REFERENCE: UNRESOLVED. 공통코드 Group 또는 Master Repository 연결을 Metadata에서 확정해야 한다.',
    MODIFY COLUMN `history_status_code` varchar(99) NOT NULL COMMENT 'History Status Code 코드. Repository Metadata가 정의한 코드 체계로 관리한다. REFERENCE: UNRESOLVED. 공통코드 Group 또는 Master Repository 연결을 Metadata에서 확정해야 한다.',
    MODIFY COLUMN `created_dt` datetime NOT NULL DEFAULT current_timestamp() COMMENT 'Object 최초 생성 일시.',
    COMMENT = 'PURPOSE: Runtime의 Repository·MongoDB·History 처리 결과를 추적한다. ROLE: STORY_PLATFORM 공식 Repository. SSOT: 해당 이력과 실행 결과의 공식 원천. ENGINE_GUIDE: Generator, Engine 및 AI는 이 테이블을 Repository First로 해석하며 값과 규칙의 Hardcoding을 금지한다.';

/* te_story_platform.sp_identifier_blueprint */
ALTER TABLE `te_story_platform`.`sp_identifier_blueprint`
    MODIFY COLUMN `blueprint_code` varchar(99) NOT NULL COMMENT 'Identifier Blueprint Code REFERENCE: te_common.cm_common_code의 group_code=SPS_IDENTIFIER_BLUEPRINT. Generator, Engine 및 AI는 해당 Group의 code를 해석한다.',
    MODIFY COLUMN `sequence_scope_code` varchar(99) NOT NULL COMMENT 'Sequence Scope Code REFERENCE: UNRESOLVED. 공통코드 Group 또는 Master Repository 연결을 Metadata에서 확정해야 한다.',
    MODIFY COLUMN `status_code` varchar(99) NOT NULL DEFAULT 'ACTIVE' COMMENT 'Status Code REFERENCE: te_common.cm_common_code의 group_code=STATUS_CODE. Generator, Engine 및 AI는 해당 Group의 code를 해석한다.',
    COMMENT = 'PURPOSE: Object Level별 Identifier Pattern과 생성 정책을 정의한다. ROLE: STORY_PLATFORM 공식 Repository. SSOT: 해당 Object 정의와 관계의 단일 원천. ENGINE_GUIDE: Generator, Engine 및 AI는 이 테이블을 Repository First로 해석하며 값과 규칙의 Hardcoding을 금지한다.';

/* te_story_platform.sp_identifier_sequence */
ALTER TABLE `te_story_platform`.`sp_identifier_sequence`
    MODIFY COLUMN `identifier_target_code` varchar(99) NOT NULL COMMENT '채번 대상 코드. 예: BUSINESS, DOMAIN, OBJECT, ENTITY, ATTRIBUTE, RELATIONSHIP, METADATA, SQL, DOCUMENT, API, GENERATOR, ENGINE. REFERENCE: te_common.cm_common_code의 group_code=SPS_IDENTIFIER_TARGET. Generator, Engine 및 AI는 해당 Group의 code를 해석한다.',
    MODIFY COLUMN `status_code` varchar(99) NOT NULL DEFAULT 'ACTIVE' COMMENT '상태 코드. ACTIVE/INACTIVE. REFERENCE: te_common.cm_common_code의 group_code=STATUS_CODE. Generator, Engine 및 AI는 해당 Group의 code를 해석한다.',
    COMMENT = 'PURPOSE: Identifier Target·Prefix·기준 일시별 Sequence를 관리한다. ROLE: STORY_PLATFORM 공식 Repository. SSOT: 해당 Object 정의와 관계의 단일 원천. ENGINE_GUIDE: Generator, Engine 및 AI는 이 테이블을 Repository First로 해석하며 값과 규칙의 Hardcoding을 금지한다.';

/* te_story_platform.sp_impact_analysis_result */
ALTER TABLE `te_story_platform`.`sp_impact_analysis_result`
    MODIFY COLUMN `impact_analysis_id` varchar(99) NOT NULL COMMENT 'Impact Analysis Id 식별자. sp_impact_analysis_result Object와 관련 Object를 식별하거나 연결한다.',
    MODIFY COLUMN `change_target_text` text NOT NULL COMMENT 'Change Target Text Text 값.',
    MODIFY COLUMN `change_type_code` varchar(99) NOT NULL COMMENT 'Change Type Code 코드. Repository Metadata가 정의한 코드 체계로 관리한다. REFERENCE: UNRESOLVED. 공통코드 Group 또는 Master Repository 연결을 Metadata에서 확정해야 한다.',
    MODIFY COLUMN `affected_object_type_code` varchar(99) NOT NULL COMMENT 'Affected Object Type Code 코드. Repository Metadata가 정의한 코드 체계로 관리한다. REFERENCE: UNRESOLVED. 공통코드 Group 또는 Master Repository 연결을 Metadata에서 확정해야 한다.',
    MODIFY COLUMN `affected_object_name` varchar(150) NOT NULL COMMENT 'Affected Object Name 명칭. 사람이 이해할 수 있는 표시 이름을 관리한다.',
    MODIFY COLUMN `affected_file_path` varchar(2000) DEFAULT NULL COMMENT 'Affected File Path 값. sp_impact_analysis_result Object의 해당 속성을 관리한다.',
    MODIFY COLUMN `affected_line_no` int(11) DEFAULT NULL COMMENT 'Affected Line No 순번. 정렬 또는 처리 순서를 정수로 관리한다.',
    MODIFY COLUMN `affected_text` text DEFAULT NULL COMMENT 'Affected Text Text 값.',
    MODIFY COLUMN `risk_level_code` varchar(99) NOT NULL DEFAULT 'MEDIUM' COMMENT 'Risk Level Code 코드. Repository Metadata가 정의한 코드 체계로 관리한다. REFERENCE: te_common.cm_common_code의 group_code=HP_RISK_LEVEL. Generator, Engine 및 AI는 해당 Group의 code를 해석한다.',
    MODIFY COLUMN `analysis_note` text DEFAULT NULL COMMENT 'Analysis Note 값. sp_impact_analysis_result Object의 해당 속성을 관리한다.',
    MODIFY COLUMN `created_by` varchar(99) NOT NULL DEFAULT 'SYSTEM' COMMENT 'Object를 최초 생성한 사용자 또는 실행 주체 식별자.',
    MODIFY COLUMN `created_dt` datetime NOT NULL DEFAULT current_timestamp() COMMENT 'Object 최초 생성 일시.',
    MODIFY COLUMN `updated_by` varchar(99) DEFAULT NULL COMMENT 'Object를 최종 수정한 사용자 또는 실행 주체 식별자.',
    MODIFY COLUMN `updated_dt` datetime DEFAULT NULL COMMENT 'Object 최종 수정 일시.',
    MODIFY COLUMN `deleted_by` varchar(99) DEFAULT NULL COMMENT 'Object를 논리 삭제한 사용자 또는 실행 주체 식별자.',
    MODIFY COLUMN `deleted_dt` datetime DEFAULT NULL COMMENT 'Object 논리 삭제 처리 일시.',
    MODIFY COLUMN `client_ip` varchar(99) DEFAULT NULL COMMENT 'Object 변경 요청이 발생한 Client IP 주소.',
    MODIFY COLUMN `program_id` varchar(99) DEFAULT NULL COMMENT 'Object 생성·수정·삭제를 수행한 Program 식별자.',
    COMMENT = 'PURPOSE: Repository 변경의 영향 Object와 Risk 분석 결과를 관리한다. ROLE: STORY_PLATFORM 공식 Repository. SSOT: 해당 Object 정의와 관계의 단일 원천. ENGINE_GUIDE: Generator, Engine 및 AI는 이 테이블을 Repository First로 해석하며 값과 규칙의 Hardcoding을 금지한다.';

/* te_story_platform.sp_knowledge_hold */
ALTER TABLE `te_story_platform`.`sp_knowledge_hold`
    MODIFY COLUMN `knowledge_id` varchar(99) NOT NULL COMMENT 'Knowledge Id 식별자. sp_knowledge_hold Object와 관련 Object를 식별하거나 연결한다.',
    MODIFY COLUMN `knowledge_identifier` varchar(99) NOT NULL COMMENT 'Knowledge Identifier 값. sp_knowledge_hold Object의 해당 속성을 관리한다.',
    MODIFY COLUMN `knowledge_type_id` varchar(99) NOT NULL COMMENT 'Knowledge Type Id 식별자. sp_knowledge_hold Object와 관련 Object를 식별하거나 연결한다.',
    MODIFY COLUMN `knowledge_name` varchar(150) NOT NULL COMMENT 'Knowledge Name 명칭. 사람이 이해할 수 있는 표시 이름을 관리한다.',
    MODIFY COLUMN `knowledge_description` varchar(2000) DEFAULT NULL COMMENT 'Knowledge Description 설명. Object의 목적, 의미 및 적용 범위를 관리한다.',
    MODIFY COLUMN `source_story_text` text DEFAULT NULL COMMENT 'Source Story Text Text 값.',
    MODIFY COLUMN `active_yn` char(1) NOT NULL DEFAULT 'Y' COMMENT 'Object 활성 여부. Y 또는 N으로 관리한다.',
    MODIFY COLUMN `created_by` varchar(99) NOT NULL DEFAULT 'SYSTEM' COMMENT 'Object를 최초 생성한 사용자 또는 실행 주체 식별자.',
    MODIFY COLUMN `created_dt` datetime NOT NULL DEFAULT current_timestamp() COMMENT 'Object 최초 생성 일시.',
    MODIFY COLUMN `updated_by` varchar(99) DEFAULT NULL COMMENT 'Object를 최종 수정한 사용자 또는 실행 주체 식별자.',
    MODIFY COLUMN `updated_dt` datetime DEFAULT NULL COMMENT 'Object 최종 수정 일시.',
    MODIFY COLUMN `deleted_yn` char(1) NOT NULL DEFAULT 'N' COMMENT 'Deleted Yn 여부. Y 또는 N 값으로 관리한다.',
    MODIFY COLUMN `deleted_by` varchar(99) DEFAULT NULL COMMENT 'Object를 논리 삭제한 사용자 또는 실행 주체 식별자.',
    MODIFY COLUMN `deleted_dt` datetime DEFAULT NULL COMMENT 'Object 논리 삭제 처리 일시.',
    MODIFY COLUMN `change_reason` varchar(2000) DEFAULT NULL COMMENT 'Change Reason 값. sp_knowledge_hold Object의 해당 속성을 관리한다.',
    MODIFY COLUMN `client_ip` varchar(99) DEFAULT NULL COMMENT 'Object 변경 요청이 발생한 Client IP 주소.',
    MODIFY COLUMN `program_id` varchar(99) DEFAULT NULL COMMENT 'Object 생성·수정·삭제를 수행한 Program 식별자.',
    COMMENT = 'PURPOSE: 승인 전 구조화 Knowledge Object를 보존하고 검토한다. ROLE: STORY_PLATFORM 공식 Repository. SSOT: 해당 Object 정의와 관계의 단일 원천. ENGINE_GUIDE: Generator, Engine 및 AI는 이 테이블을 Repository First로 해석하며 값과 규칙의 Hardcoding을 금지한다.';

/* te_story_platform.sp_knowledge_relationship_hold */
ALTER TABLE `te_story_platform`.`sp_knowledge_relationship_hold`
    MODIFY COLUMN `knowledge_relationship_id` varchar(99) NOT NULL COMMENT 'Knowledge Relationship Id 식별자. sp_knowledge_relationship_hold Object와 관련 Object를 식별하거나 연결한다.',
    MODIFY COLUMN `source_knowledge_id` varchar(99) NOT NULL COMMENT 'Source Knowledge Id 식별자. sp_knowledge_relationship_hold Object와 관련 Object를 식별하거나 연결한다.',
    MODIFY COLUMN `target_knowledge_id` varchar(99) NOT NULL COMMENT 'Target Knowledge Id 식별자. sp_knowledge_relationship_hold Object와 관련 Object를 식별하거나 연결한다.',
    MODIFY COLUMN `relationship_type_code` varchar(99) NOT NULL COMMENT 'Relationship Type Code 코드. Repository Metadata가 정의한 코드 체계로 관리한다. REFERENCE: UNRESOLVED. 공통코드 Group 또는 Master Repository 연결을 Metadata에서 확정해야 한다.',
    MODIFY COLUMN `relationship_description` varchar(2000) DEFAULT NULL COMMENT 'Relationship Description 설명. Object의 목적, 의미 및 적용 범위를 관리한다.',
    MODIFY COLUMN `active_yn` char(1) NOT NULL DEFAULT 'Y' COMMENT 'Object 활성 여부. Y 또는 N으로 관리한다.',
    MODIFY COLUMN `created_by` varchar(99) NOT NULL DEFAULT 'SYSTEM' COMMENT 'Object를 최초 생성한 사용자 또는 실행 주체 식별자.',
    MODIFY COLUMN `created_dt` datetime NOT NULL DEFAULT current_timestamp() COMMENT 'Object 최초 생성 일시.',
    MODIFY COLUMN `updated_by` varchar(99) DEFAULT NULL COMMENT 'Object를 최종 수정한 사용자 또는 실행 주체 식별자.',
    MODIFY COLUMN `updated_dt` datetime DEFAULT NULL COMMENT 'Object 최종 수정 일시.',
    MODIFY COLUMN `deleted_yn` char(1) NOT NULL DEFAULT 'N' COMMENT 'Deleted Yn 여부. Y 또는 N 값으로 관리한다.',
    MODIFY COLUMN `deleted_by` varchar(99) DEFAULT NULL COMMENT 'Object를 논리 삭제한 사용자 또는 실행 주체 식별자.',
    MODIFY COLUMN `deleted_dt` datetime DEFAULT NULL COMMENT 'Object 논리 삭제 처리 일시.',
    MODIFY COLUMN `change_reason` varchar(2000) DEFAULT NULL COMMENT 'Change Reason 값. sp_knowledge_relationship_hold Object의 해당 속성을 관리한다.',
    MODIFY COLUMN `client_ip` varchar(99) DEFAULT NULL COMMENT 'Object 변경 요청이 발생한 Client IP 주소.',
    MODIFY COLUMN `program_id` varchar(99) DEFAULT NULL COMMENT 'Object 생성·수정·삭제를 수행한 Program 식별자.',
    COMMENT = 'PURPOSE: 승인 전 Knowledge 사이의 의미 관계를 보존하고 검토한다. ROLE: STORY_PLATFORM 공식 Repository. SSOT: 해당 Object 정의와 관계의 단일 원천. ENGINE_GUIDE: Generator, Engine 및 AI는 이 테이블을 Repository First로 해석하며 값과 규칙의 Hardcoding을 금지한다.';

/* te_story_platform.sp_knowledge_type_hold */
ALTER TABLE `te_story_platform`.`sp_knowledge_type_hold`
    MODIFY COLUMN `knowledge_type_id` varchar(99) NOT NULL COMMENT 'Knowledge Type Id 식별자. sp_knowledge_type_hold Object와 관련 Object를 식별하거나 연결한다.',
    MODIFY COLUMN `knowledge_type_code` varchar(99) NOT NULL COMMENT 'Knowledge Type Code 코드. Repository Metadata가 정의한 코드 체계로 관리한다. REFERENCE: STORY_PLATFORM.sp_knowledge_type_hold(knowledge_type_code). 해당 Master Repository를 공식 연결 원천으로 사용한다.',
    MODIFY COLUMN `knowledge_type_name` varchar(150) NOT NULL COMMENT 'Knowledge Type Name 명칭. 사람이 이해할 수 있는 표시 이름을 관리한다.',
    MODIFY COLUMN `parent_knowledge_type_id` varchar(99) DEFAULT NULL COMMENT 'Parent Knowledge Type Id 식별자. sp_knowledge_type_hold Object와 관련 Object를 식별하거나 연결한다.',
    MODIFY COLUMN `knowledge_type_description` varchar(2000) DEFAULT NULL COMMENT 'Knowledge Type Description 설명. Object의 목적, 의미 및 적용 범위를 관리한다.',
    MODIFY COLUMN `active_yn` char(1) NOT NULL DEFAULT 'Y' COMMENT 'Object 활성 여부. Y 또는 N으로 관리한다.',
    MODIFY COLUMN `sort_no` int(11) NOT NULL DEFAULT 0 COMMENT '표시 및 처리 순서를 제어하는 정렬 순번.',
    MODIFY COLUMN `created_by` varchar(99) NOT NULL DEFAULT 'SYSTEM' COMMENT 'Object를 최초 생성한 사용자 또는 실행 주체 식별자.',
    MODIFY COLUMN `created_dt` datetime NOT NULL DEFAULT current_timestamp() COMMENT 'Object 최초 생성 일시.',
    MODIFY COLUMN `updated_by` varchar(99) DEFAULT NULL COMMENT 'Object를 최종 수정한 사용자 또는 실행 주체 식별자.',
    MODIFY COLUMN `updated_dt` datetime DEFAULT NULL COMMENT 'Object 최종 수정 일시.',
    MODIFY COLUMN `deleted_yn` char(1) NOT NULL DEFAULT 'N' COMMENT 'Deleted Yn 여부. Y 또는 N 값으로 관리한다.',
    MODIFY COLUMN `deleted_by` varchar(99) DEFAULT NULL COMMENT 'Object를 논리 삭제한 사용자 또는 실행 주체 식별자.',
    MODIFY COLUMN `deleted_dt` datetime DEFAULT NULL COMMENT 'Object 논리 삭제 처리 일시.',
    MODIFY COLUMN `change_reason` varchar(2000) DEFAULT NULL COMMENT 'Change Reason 값. sp_knowledge_type_hold Object의 해당 속성을 관리한다.',
    MODIFY COLUMN `client_ip` varchar(99) DEFAULT NULL COMMENT 'Object 변경 요청이 발생한 Client IP 주소.',
    MODIFY COLUMN `program_id` varchar(99) DEFAULT NULL COMMENT 'Object 생성·수정·삭제를 수행한 Program 식별자.',
    COMMENT = 'PURPOSE: 승인 전 Knowledge Type 계층과 분류 기준을 보존하고 검토한다. ROLE: STORY_PLATFORM 공식 Repository. SSOT: 해당 Object 정의와 관계의 단일 원천. ENGINE_GUIDE: Generator, Engine 및 AI는 이 테이블을 Repository First로 해석하며 값과 규칙의 Hardcoding을 금지한다.';

/* te_story_platform.sp_metadata */
ALTER TABLE `te_story_platform`.`sp_metadata`
    MODIFY COLUMN `target_type_code` varchar(99) NOT NULL COMMENT 'Metadata Target Type Code. SPS_METADATA_TARGET 공통코드를 참조한다. 모든 _code 계열 컬럼은 VARCHAR(99)를 표준으로 한다. REFERENCE: te_common.cm_common_code의 group_code=SPS_METADATA_TARGET. Generator, Engine 및 AI는 해당 Group의 code를 해석한다.',
    MODIFY COLUMN `metadata_type_code` varchar(99) NOT NULL COMMENT 'Metadata Type Code. SPS_METADATA_TYPE 공통코드를 참조한다. 모든 _code 계열 컬럼은 VARCHAR(99)를 표준으로 한다. REFERENCE: UNRESOLVED. 공통코드 Group 또는 Master Repository 연결을 Metadata에서 확정해야 한다.',
    MODIFY COLUMN `metadata_value_type_code` varchar(99) NOT NULL DEFAULT 'STRING' COMMENT 'Metadata Value Type Code. STRING, REGEX, JSON 등의 값 유형을 식별한다. 모든 _code 계열 컬럼은 VARCHAR(99)를 표준으로 한다. REFERENCE: te_common.cm_common_code의 group_code=METADATA_VALUE_TYPE. Generator, Engine 및 AI는 해당 Group의 code를 해석한다.',
    COMMENT = 'PURPOSE: Generator·Engine·AI가 해석하는 Story Programming Metadata를 관리한다. ROLE: STORY_PLATFORM 공식 Repository. SSOT: 해당 Object 정의와 관계의 단일 원천. ENGINE_GUIDE: Generator, Engine 및 AI는 이 테이블을 Repository First로 해석하며 값과 규칙의 Hardcoding을 금지한다.';

/* te_story_platform.sp_object */
ALTER TABLE `te_story_platform`.`sp_object`
    MODIFY COLUMN `object_code` varchar(99) NOT NULL COMMENT 'Object Code. Object의 사람이 읽을 수 있는 코드. 모든 _code 계열 컬럼은 VARCHAR(99)를 표준으로 한다. REFERENCE: STORY_PLATFORM.sp_object(object_code). 해당 Master Repository를 공식 연결 원천으로 사용한다.',
    MODIFY COLUMN `business_code` varchar(99) NOT NULL COMMENT 'Business Code. 모든 _code 계열 컬럼은 VARCHAR(99)를 표준으로 한다. REFERENCE: UNRESOLVED. 공통코드 Group 또는 Master Repository 연결을 Metadata에서 확정해야 한다.',
    MODIFY COLUMN `domain_code` varchar(99) NOT NULL COMMENT 'Domain Code. 모든 _code 계열 컬럼은 VARCHAR(99)를 표준으로 한다. REFERENCE: UNRESOLVED. 공통코드 Group 또는 Master Repository 연결을 Metadata에서 확정해야 한다.',
    MODIFY COLUMN `object_type_code` varchar(99) NOT NULL COMMENT 'Object Type Code. 모든 _code 계열 컬럼은 VARCHAR(99)를 표준으로 한다. REFERENCE: te_common.cm_common_code의 group_code=OBJECT_TYPE. Generator, Engine 및 AI는 해당 Group의 code를 해석한다.',
    MODIFY COLUMN `status_code` varchar(99) NOT NULL DEFAULT 'ACTIVE' COMMENT 'Status Code. 모든 _code 계열 컬럼은 VARCHAR(99)를 표준으로 한다. REFERENCE: te_common.cm_common_code의 group_code=STATUS_CODE. Generator, Engine 및 AI는 해당 Group의 code를 해석한다.',
    MODIFY COLUMN `version_num` varchar(99) DEFAULT NULL COMMENT 'Object Version을 문자열로 표현한 번호.',
    MODIFY COLUMN `sequence_scope_code` varchar(99) DEFAULT NULL COMMENT 'Sequence Scope Code. 모든 _code 계열 컬럼은 VARCHAR(99)를 표준으로 한다. REFERENCE: UNRESOLVED. 공통코드 Group 또는 Master Repository 연결을 Metadata에서 확정해야 한다.',
    MODIFY COLUMN `identifier_target_code` varchar(99) DEFAULT NULL COMMENT 'Identifier Target Code. SPS_IDENTIFIER_TARGET 공통코드를 참조한다. 모든 _code 계열 컬럼은 VARCHAR(99)를 표준으로 한다. REFERENCE: te_common.cm_common_code의 group_code=SPS_IDENTIFIER_TARGET. Generator, Engine 및 AI는 해당 Group의 code를 해석한다.',
    COMMENT = '[Identifier Repository]\r\n\r\n- Identifier Target 정보는 cm_common_code에서 관리한다.\r\n- Group Code : SPS_IDENTIFIER_TARGET\r\n- code_name  : Object Code (예: OBJECT, MEMBER, DATABASE, SCREEN)\r\n- code       : Identifier Object Code (예: OB, MB, DB, SC)\r\n- extension_json : Identifier 확장 정보 및 Blueprint Token 관리\r\n\r\n[Object First]\r\n\r\n- sp_object는 Object를 정의한다.\r\n- Identifier 생성 규칙은 Repository Metadata를 통해 해석한다.\r\n- Engine은 Repository를 해석하며 Identifier를 생성한다.\r\n- Hardcoding을 금지한다.\r\n\r\n[Repository Rule]\r\n\r\n- Object의 의미는 sp_object가 관리한다.\r\n- Identifier의 약어 및 확장 속성은 cm_common_code.extension_json이 관리한다.\r\n- 두 Repository를 함께 해석하여 Identifier를 생성한다.\r\n\r\nPURPOSE: Defines SPS Object Class metadata.\r\nROLE: Central Object Class repository.\r\nSCOPE: Business, Domain, Database, Schema, Table, Entity, Attribute, Relationship, ERD, API, Screen, Workflow, Event, Engine, Generator, Prompt, Template, Document, SQL, Metadata, Member, Role, Permission.\r\nPRINCIPLE: Everything is an Object.\r\nIDENTIFIER: Stores Identifier Blueprint fields for generating object instance identifiers.\r\nREFERENCE: Identifier target mapping and identifier extension metadata are managed in cm_common_code (group_code = SPS_IDENTIFIER_TARGET, extension_json). Do not hardcode identifier object abbreviations.\r\nAI_GUIDE: Treat this table as the canonical Object Class definition table.\r\nREPOSITORY: Identifier target mapping and extension metadata are managed in cm_common_code (group_code=SPS_IDENTIFIER_TARGET, extension_json). Identifier Engines shall resolve Object identifier codes from the Repository. Hardcoding is prohibited.\r\nidentifier_target_code\r\n- 참조 코드그룹: SPS_IDENTIFIER_TARGET\r\n- 역할: Identifier Engine이 이 Object의 ID를 어떤 Target 규칙으로 발급할지 판단하는 기준\r\n- 예: OB, EN, AT, AP, SQ';

/* te_story_platform.sp_object_execution_link */
ALTER TABLE `te_story_platform`.`sp_object_execution_link`
    MODIFY COLUMN `execution_link_type_code` varchar(99) NOT NULL DEFAULT 'MONGODB' COMMENT 'Execution Link Type Code. 모든 _code 계열 컬럼은 VARCHAR(99)를 표준으로 한다. REFERENCE: UNRESOLVED. 공통코드 Group 또는 Master Repository 연결을 Metadata에서 확정해야 한다.',
    MODIFY COLUMN `created_dt` datetime NOT NULL DEFAULT current_timestamp() COMMENT 'Object 최초 생성 일시.',
    MODIFY COLUMN `updated_dt` datetime DEFAULT NULL ON UPDATE current_timestamp() COMMENT 'Object 최종 수정 일시.',
    MODIFY COLUMN `deleted_dt` datetime DEFAULT NULL COMMENT 'Object 논리 삭제 처리 일시.',
    COMMENT = 'PURPOSE: Object 실행 시도와 Repository·MongoDB 실행 대상을 연결한다. ROLE: STORY_PLATFORM 공식 Repository. SSOT: 해당 Object 정의와 관계의 단일 원천. ENGINE_GUIDE: Generator, Engine 및 AI는 이 테이블을 Repository First로 해석하며 값과 규칙의 Hardcoding을 금지한다.';

/* te_story_platform.sp_object_lifecycle */
ALTER TABLE `te_story_platform`.`sp_object_lifecycle`
    MODIFY COLUMN `object_lifecycle_id` varchar(99) NOT NULL COMMENT 'Object Lifecycle Id 식별자. sp_object_lifecycle Object와 관련 Object를 식별하거나 연결한다.',
    MODIFY COLUMN `object_id` varchar(99) NOT NULL COMMENT 'Object Id 식별자. sp_object_lifecycle Object와 관련 Object를 식별하거나 연결한다.',
    MODIFY COLUMN `lifecycle_status_code` varchar(99) NOT NULL COMMENT 'Lifecycle Status Code 코드. Repository Metadata가 정의한 코드 체계로 관리한다. REFERENCE: te_common.cm_common_code의 group_code=OBJECT_LIFECYCLE_STATUS. Generator, Engine 및 AI는 해당 Group의 code를 해석한다.',
    MODIFY COLUMN `lifecycle_event_code` varchar(99) NOT NULL COMMENT 'Lifecycle Event Code 코드. Repository Metadata가 정의한 코드 체계로 관리한다. REFERENCE: te_common.cm_common_code의 group_code=OBJECT_LIFECYCLE_STATUS. Generator, Engine 및 AI는 해당 Group의 code를 해석한다.',
    MODIFY COLUMN `lifecycle_reason` varchar(2000) DEFAULT NULL COMMENT 'Lifecycle Reason 값. sp_object_lifecycle Object의 해당 속성을 관리한다.',
    MODIFY COLUMN `lifecycle_note` text DEFAULT NULL COMMENT 'Lifecycle Note 값. sp_object_lifecycle Object의 해당 속성을 관리한다.',
    MODIFY COLUMN `effective_start_dt` datetime NOT NULL DEFAULT current_timestamp() COMMENT 'Effective Start Dt 일시. Object의 해당 Event 발생 시점을 관리한다.',
    MODIFY COLUMN `effective_end_dt` datetime DEFAULT NULL COMMENT 'Effective End Dt 일시. Object의 해당 Event 발생 시점을 관리한다.',
    MODIFY COLUMN `created_by` varchar(99) NOT NULL DEFAULT 'SYSTEM' COMMENT 'Object를 최초 생성한 사용자 또는 실행 주체 식별자.',
    MODIFY COLUMN `created_dt` datetime NOT NULL DEFAULT current_timestamp() COMMENT 'Object 최초 생성 일시.',
    MODIFY COLUMN `updated_by` varchar(99) DEFAULT NULL COMMENT 'Object를 최종 수정한 사용자 또는 실행 주체 식별자.',
    MODIFY COLUMN `updated_dt` datetime DEFAULT NULL COMMENT 'Object 최종 수정 일시.',
    MODIFY COLUMN `deleted_by` varchar(99) DEFAULT NULL COMMENT 'Object를 논리 삭제한 사용자 또는 실행 주체 식별자.',
    MODIFY COLUMN `deleted_dt` datetime DEFAULT NULL COMMENT 'Object 논리 삭제 처리 일시.',
    MODIFY COLUMN `client_ip` varchar(99) DEFAULT NULL COMMENT 'Object 변경 요청이 발생한 Client IP 주소.',
    MODIFY COLUMN `program_id` varchar(99) DEFAULT NULL COMMENT 'Object 생성·수정·삭제를 수행한 Program 식별자.',
    COMMENT = 'PURPOSE: Object의 Lifecycle 상태와 Event 발생 이력을 관리한다. ROLE: STORY_PLATFORM 공식 Repository. SSOT: 해당 Object 정의와 관계의 단일 원천. ENGINE_GUIDE: Generator, Engine 및 AI는 이 테이블을 Repository First로 해석하며 값과 규칙의 Hardcoding을 금지한다.';

/* te_story_platform.sp_relationship */
ALTER TABLE `te_story_platform`.`sp_relationship`
    MODIFY COLUMN `relationship_scope_code` varchar(99) NOT NULL DEFAULT 'ERD' COMMENT 'Relationship Scope Code. ERD 또는 OBJECT REFERENCE: te_common.cm_common_code의 group_code=SPS_RELATIONSHIP_SCOPE. Generator, Engine 및 AI는 해당 Group의 code를 해석한다.',
    MODIFY COLUMN `source_object_type_code` varchar(99) DEFAULT NULL COMMENT 'Source Object 유형 코드. KNOWLEDGE, LIFECYCLE, RULE, VERIFIED_SQL 등 REFERENCE: te_common.cm_common_code의 group_code=SPS_RELATIONSHIP_OBJECT_TYPE. Generator, Engine 및 AI는 해당 Group의 code를 해석한다.',
    MODIFY COLUMN `target_object_type_code` varchar(99) DEFAULT NULL COMMENT 'Target Object 유형 코드. KNOWLEDGE, LIFECYCLE, RULE, VERIFIED_SQL 등 REFERENCE: te_common.cm_common_code의 group_code=SPS_RELATIONSHIP_OBJECT_TYPE. Generator, Engine 및 AI는 해당 Group의 code를 해석한다.',
    MODIFY COLUMN `relationship_code` varchar(99) NOT NULL COMMENT 'Relationship Code. 사람이 이해하고 Generator가 참조할 수 있는 의미 기반 식별 코드 REFERENCE: STORY_PLATFORM.sp_relationship(relationship_code). 해당 Master Repository를 공식 연결 원천으로 사용한다.',
    MODIFY COLUMN `relationship_type_code` varchar(99) NOT NULL DEFAULT 'FK' COMMENT 'Relationship Type Code. Engine과 Generator의 처리 방식을 결정한다 REFERENCE: UNRESOLVED. 공통코드 Group 또는 Master Repository 연결을 Metadata에서 확정해야 한다.',
    MODIFY COLUMN `delete_rule_code` varchar(99) DEFAULT NULL COMMENT '삭제 시 Relationship 처리 규칙 REFERENCE: UNRESOLVED. 공통코드 Group 또는 Master Repository 연결을 Metadata에서 확정해야 한다.',
    MODIFY COLUMN `update_rule_code` varchar(99) DEFAULT NULL COMMENT '변경 시 Relationship 처리 규칙 REFERENCE: UNRESOLVED. 공통코드 Group 또는 Master Repository 연결을 Metadata에서 확정해야 한다.',
    COMMENT = 'PURPOSE: ERD와 범용 Object 사이의 의미 Relationship을 관리한다. ROLE: STORY_PLATFORM 공식 Repository. SSOT: 해당 Object 정의와 관계의 단일 원천. ENGINE_GUIDE: Generator, Engine 및 AI는 이 테이블을 Repository First로 해석하며 값과 규칙의 Hardcoding을 금지한다.';

/* te_story_platform.sp_relationship_attribute */
ALTER TABLE `te_story_platform`.`sp_relationship_attribute`
    COMMENT = 'PURPOSE: Relationship의 Source·Target Attribute 매핑을 관리한다. ROLE: STORY_PLATFORM 공식 Repository. SSOT: 해당 Object 정의와 관계의 단일 원천. ENGINE_GUIDE: Generator, Engine 및 AI는 이 테이블을 Repository First로 해석하며 값과 규칙의 Hardcoding을 금지한다.';

/* te_story_platform.sp_work_asset */
ALTER TABLE `te_story_platform`.`sp_work_asset`
    MODIFY COLUMN `asset_type_code` varchar(99) NOT NULL COMMENT 'Work Asset Type Code REFERENCE: UNRESOLVED. 공통코드 Group 또는 Master Repository 연결을 Metadata에서 확정해야 한다.',
    MODIFY COLUMN `asset_status_code` varchar(99) NOT NULL COMMENT 'Asset Status Code REFERENCE: UNRESOLVED. 공통코드 Group 또는 Master Repository 연결을 Metadata에서 확정해야 한다.',
    MODIFY COLUMN `created_by` varchar(99) NOT NULL COMMENT 'Object를 최초 생성한 사용자 또는 실행 주체 식별자.',
    MODIFY COLUMN `created_dt` datetime NOT NULL DEFAULT current_timestamp() COMMENT 'Object 최초 생성 일시.',
    MODIFY COLUMN `updated_by` varchar(99) DEFAULT NULL COMMENT 'Object를 최종 수정한 사용자 또는 실행 주체 식별자.',
    MODIFY COLUMN `updated_dt` datetime DEFAULT NULL ON UPDATE current_timestamp() COMMENT 'Object 최종 수정 일시.',
    MODIFY COLUMN `deleted_by` varchar(99) DEFAULT NULL COMMENT 'Object를 논리 삭제한 사용자 또는 실행 주체 식별자.',
    MODIFY COLUMN `deleted_dt` datetime DEFAULT NULL COMMENT 'Object 논리 삭제 처리 일시.',
    MODIFY COLUMN `client_ip` varchar(99) DEFAULT NULL COMMENT 'Object 변경 요청이 발생한 Client IP 주소.',
    MODIFY COLUMN `program_id` varchar(99) DEFAULT NULL COMMENT 'Object 생성·수정·삭제를 수행한 Program 식별자.',
    COMMENT = 'PURPOSE: Work 수행 중 Generator·Engine·AI가 생성한 Asset을 관리한다. ROLE: STORY_PLATFORM 공식 Repository. SSOT: 해당 Object 정의와 관계의 단일 원천. ENGINE_GUIDE: Generator, Engine 및 AI는 이 테이블을 Repository First로 해석하며 값과 규칙의 Hardcoding을 금지한다.';

/* te_story_platform.sp_work_item */
ALTER TABLE `te_story_platform`.`sp_work_item`
    MODIFY COLUMN `work_status_code` varchar(99) NOT NULL COMMENT 'Work Status Code REFERENCE: UNRESOLVED. 공통코드 Group 또는 Master Repository 연결을 Metadata에서 확정해야 한다.',
    MODIFY COLUMN `work_result_code` varchar(99) DEFAULT NULL COMMENT 'Work Result Code REFERENCE: UNRESOLVED. 공통코드 Group 또는 Master Repository 연결을 Metadata에서 확정해야 한다.',
    MODIFY COLUMN `created_by` varchar(99) NOT NULL COMMENT 'Object를 최초 생성한 사용자 또는 실행 주체 식별자.',
    MODIFY COLUMN `created_dt` datetime NOT NULL DEFAULT current_timestamp() COMMENT 'Object 최초 생성 일시.',
    MODIFY COLUMN `updated_by` varchar(99) DEFAULT NULL COMMENT 'Object를 최종 수정한 사용자 또는 실행 주체 식별자.',
    MODIFY COLUMN `updated_dt` datetime DEFAULT NULL ON UPDATE current_timestamp() COMMENT 'Object 최종 수정 일시.',
    MODIFY COLUMN `deleted_by` varchar(99) DEFAULT NULL COMMENT 'Object를 논리 삭제한 사용자 또는 실행 주체 식별자.',
    MODIFY COLUMN `deleted_dt` datetime DEFAULT NULL COMMENT 'Object 논리 삭제 처리 일시.',
    MODIFY COLUMN `client_ip` varchar(99) DEFAULT NULL COMMENT 'Object 변경 요청이 발생한 Client IP 주소.',
    MODIFY COLUMN `program_id` varchar(99) DEFAULT NULL COMMENT 'Object 생성·수정·삭제를 수행한 Program 식별자.',
    COMMENT = 'PURPOSE: Work Session을 구성하는 개별 실행 단위를 관리한다. ROLE: STORY_PLATFORM 공식 Repository. SSOT: 해당 Object 정의와 관계의 단일 원천. ENGINE_GUIDE: Generator, Engine 및 AI는 이 테이블을 Repository First로 해석하며 값과 규칙의 Hardcoding을 금지한다.';

/* te_story_platform.sp_work_session */
ALTER TABLE `te_story_platform`.`sp_work_session`
    MODIFY COLUMN `work_type_code` varchar(99) NOT NULL COMMENT 'Work Type Code REFERENCE: UNRESOLVED. 공통코드 Group 또는 Master Repository 연결을 Metadata에서 확정해야 한다.',
    MODIFY COLUMN `work_status_code` varchar(99) NOT NULL COMMENT 'Work Status Code REFERENCE: UNRESOLVED. 공통코드 Group 또는 Master Repository 연결을 Metadata에서 확정해야 한다.',
    MODIFY COLUMN `work_result_code` varchar(99) DEFAULT NULL COMMENT 'Work Result Code REFERENCE: UNRESOLVED. 공통코드 Group 또는 Master Repository 연결을 Metadata에서 확정해야 한다.',
    MODIFY COLUMN `created_by` varchar(99) NOT NULL COMMENT 'Object를 최초 생성한 사용자 또는 실행 주체 식별자.',
    MODIFY COLUMN `created_dt` datetime NOT NULL DEFAULT current_timestamp() COMMENT 'Object 최초 생성 일시.',
    MODIFY COLUMN `updated_by` varchar(99) DEFAULT NULL COMMENT 'Object를 최종 수정한 사용자 또는 실행 주체 식별자.',
    MODIFY COLUMN `updated_dt` datetime DEFAULT NULL ON UPDATE current_timestamp() COMMENT 'Object 최종 수정 일시.',
    MODIFY COLUMN `deleted_by` varchar(99) DEFAULT NULL COMMENT 'Object를 논리 삭제한 사용자 또는 실행 주체 식별자.',
    MODIFY COLUMN `deleted_dt` datetime DEFAULT NULL COMMENT 'Object 논리 삭제 처리 일시.',
    MODIFY COLUMN `client_ip` varchar(99) DEFAULT NULL COMMENT 'Object 변경 요청이 발생한 Client IP 주소.',
    MODIFY COLUMN `program_id` varchar(99) DEFAULT NULL COMMENT 'Object 생성·수정·삭제를 수행한 Program 식별자.',
    COMMENT = 'PURPOSE: Runtime·Generator·Engine·AI의 최상위 Work Session을 관리한다. ROLE: STORY_PLATFORM 공식 Repository. SSOT: 해당 Object 정의와 관계의 단일 원천. ENGINE_GUIDE: Generator, Engine 및 AI는 이 테이블을 Repository First로 해석하며 값과 규칙의 Hardcoding을 금지한다.';

/* te_common.cm_audit_policy */
ALTER TABLE `te_common`.`cm_audit_policy`
    MODIFY COLUMN `audit_policy_code` varchar(99) NOT NULL COMMENT '감사 정책 코드 REFERENCE: COMMON.cm_audit_policy(audit_policy_code). 해당 Master Repository를 공식 연결 원천으로 사용한다.',
    MODIFY COLUMN `created_dt` datetime NOT NULL DEFAULT current_timestamp() COMMENT 'Object 최초 생성 일시.',
    MODIFY COLUMN `created_by` varchar(99) NOT NULL DEFAULT 'SYSTEM' COMMENT 'Object를 최초 생성한 사용자 또는 실행 주체 식별자.',
    MODIFY COLUMN `updated_dt` datetime NOT NULL DEFAULT current_timestamp() ON UPDATE current_timestamp() COMMENT 'Object 최종 수정 일시.',
    MODIFY COLUMN `updated_by` varchar(99) NOT NULL DEFAULT 'SYSTEM' COMMENT 'Object를 최종 수정한 사용자 또는 실행 주체 식별자.',
    MODIFY COLUMN `deleted_by` varchar(99) DEFAULT NULL COMMENT 'Object를 논리 삭제한 사용자 또는 실행 주체 식별자.',
    MODIFY COLUMN `deleted_dt` datetime DEFAULT NULL COMMENT 'Object 논리 삭제 처리 일시.',
    MODIFY COLUMN `program_id` varchar(99) DEFAULT NULL COMMENT 'Object 생성·수정·삭제를 수행한 Program 식별자.',
    MODIFY COLUMN `client_ip` varchar(99) DEFAULT NULL COMMENT 'Object 변경 요청이 발생한 Client IP 주소.',
    MODIFY COLUMN `status_code` varchar(99) NOT NULL DEFAULT 'ACTIVE' COMMENT 'Status Code 코드. Repository Metadata가 정의한 코드 체계로 관리한다. REFERENCE: te_common.cm_common_code의 group_code=STATUS_CODE. Generator, Engine 및 AI는 해당 Group의 code를 해석한다.',
    COMMENT = 'PURPOSE: 감사 대상과 기록 범위를 정의하는 공통 감사 정책을 관리한다. ROLE: COMMON 공식 Repository. SSOT: 해당 이력과 실행 결과의 공식 원천. ENGINE_GUIDE: Generator, Engine 및 AI는 이 테이블을 Repository First로 해석하며 값과 규칙의 Hardcoding을 금지한다.';

/* te_common.cm_business_domain */
ALTER TABLE `te_common`.`cm_business_domain`
    MODIFY COLUMN `business_domain_code` varchar(99) NOT NULL COMMENT '업무 도메인 코드 REFERENCE: COMMON.cm_business_domain(business_domain_code). 해당 Master Repository를 공식 연결 원천으로 사용한다.',
    MODIFY COLUMN `created_dt` datetime NOT NULL DEFAULT current_timestamp() COMMENT 'Object 최초 생성 일시.',
    MODIFY COLUMN `created_by` varchar(99) NOT NULL DEFAULT 'SYSTEM' COMMENT 'Object를 최초 생성한 사용자 또는 실행 주체 식별자.',
    MODIFY COLUMN `updated_dt` datetime NOT NULL DEFAULT current_timestamp() ON UPDATE current_timestamp() COMMENT 'Object 최종 수정 일시.',
    MODIFY COLUMN `updated_by` varchar(99) NOT NULL DEFAULT 'SYSTEM' COMMENT 'Object를 최종 수정한 사용자 또는 실행 주체 식별자.',
    MODIFY COLUMN `deleted_by` varchar(99) DEFAULT NULL COMMENT 'Object를 논리 삭제한 사용자 또는 실행 주체 식별자.',
    MODIFY COLUMN `deleted_dt` datetime DEFAULT NULL COMMENT 'Object 논리 삭제 처리 일시.',
    MODIFY COLUMN `program_id` varchar(99) DEFAULT NULL COMMENT 'Object 생성·수정·삭제를 수행한 Program 식별자.',
    MODIFY COLUMN `client_ip` varchar(99) DEFAULT NULL COMMENT 'Object 변경 요청이 발생한 Client IP 주소.',
    MODIFY COLUMN `status_code` varchar(99) NOT NULL DEFAULT 'ACTIVE' COMMENT 'Status Code 코드. Repository Metadata가 정의한 코드 체계로 관리한다. REFERENCE: te_common.cm_common_code의 group_code=STATUS_CODE. Generator, Engine 및 AI는 해당 Group의 code를 해석한다.',
    COMMENT = 'PURPOSE: Business와 Domain의 공식 분류 코드 및 관계를 관리한다. ROLE: COMMON 공식 Repository. SSOT: 해당 Object 정의와 관계의 단일 원천. ENGINE_GUIDE: Generator, Engine 및 AI는 이 테이블을 Repository First로 해석하며 값과 규칙의 Hardcoding을 금지한다.';

/* te_common.cm_change_history */
ALTER TABLE `te_common`.`cm_change_history`
    MODIFY COLUMN `status_code` varchar(99) NOT NULL DEFAULT 'ACTIVE' COMMENT 'Status Code 코드. Repository Metadata가 정의한 코드 체계로 관리한다. REFERENCE: te_common.cm_common_code의 group_code=STATUS_CODE. Generator, Engine 및 AI는 해당 Group의 code를 해석한다.',
    COMMENT = 'PURPOSE: Repository Object와 업무 데이터의 변경 이력을 추적한다. ROLE: COMMON 공식 Repository. SSOT: 해당 이력과 실행 결과의 공식 원천. ENGINE_GUIDE: Generator, Engine 및 AI는 이 테이블을 Repository First로 해석하며 값과 규칙의 Hardcoding을 금지한다.';

/* te_common.cm_code_inspection_result */
ALTER TABLE `te_common`.`cm_code_inspection_result`
    MODIFY COLUMN `inspection_id` varchar(99) NOT NULL COMMENT 'Inspection Id 식별자. cm_code_inspection_result Object와 관련 Object를 식별하거나 연결한다.',
    MODIFY COLUMN `inspection_type` varchar(99) NOT NULL COMMENT 'Inspection Type 값. cm_code_inspection_result Object의 해당 속성을 관리한다.',
    MODIFY COLUMN `group_code` varchar(99) NOT NULL COMMENT 'Group Code 코드. Repository Metadata가 정의한 코드 체계로 관리한다. REFERENCE: UNRESOLVED. 공통코드 Group 또는 Master Repository 연결을 Metadata에서 확정해야 한다.',
    MODIFY COLUMN `code` varchar(99) DEFAULT NULL COMMENT 'Code 값. cm_code_inspection_result Object의 해당 속성을 관리한다.',
    MODIFY COLUMN `code_name` varchar(150) DEFAULT NULL COMMENT 'Code Name 명칭. 사람이 이해할 수 있는 표시 이름을 관리한다.',
    MODIFY COLUMN `related_codes` varchar(2000) DEFAULT NULL COMMENT 'Related Codes 값. cm_code_inspection_result Object의 해당 속성을 관리한다.',
    MODIFY COLUMN `message` text NOT NULL COMMENT 'Message 값. cm_code_inspection_result Object의 해당 속성을 관리한다.',
    MODIFY COLUMN `severity_code` varchar(99) NOT NULL DEFAULT 'WARNING' COMMENT 'Severity Code 코드. Repository Metadata가 정의한 코드 체계로 관리한다. REFERENCE: te_common.cm_common_code의 group_code=CM_SEVERITY. Generator, Engine 및 AI는 해당 Group의 code를 해석한다.',
    MODIFY COLUMN `created_dt` datetime NOT NULL DEFAULT current_timestamp() COMMENT 'Object 최초 생성 일시.',
    MODIFY COLUMN `updated_dt` datetime NOT NULL DEFAULT current_timestamp() ON UPDATE current_timestamp() COMMENT 'Object 최종 수정 일시.',
    MODIFY COLUMN `created_by` varchar(99) NOT NULL DEFAULT 'SYSTEM' COMMENT 'Object를 최초 생성한 사용자 또는 실행 주체 식별자.',
    MODIFY COLUMN `updated_by` varchar(99) DEFAULT NULL COMMENT 'Object를 최종 수정한 사용자 또는 실행 주체 식별자.',
    MODIFY COLUMN `deleted_by` varchar(99) DEFAULT NULL COMMENT 'Object를 논리 삭제한 사용자 또는 실행 주체 식별자.',
    MODIFY COLUMN `deleted_dt` datetime DEFAULT NULL COMMENT 'Object 논리 삭제 처리 일시.',
    MODIFY COLUMN `client_ip` varchar(99) DEFAULT NULL COMMENT 'Object 변경 요청이 발생한 Client IP 주소.',
    MODIFY COLUMN `program_id` varchar(99) DEFAULT NULL COMMENT 'Object 생성·수정·삭제를 수행한 Program 식별자.',
    MODIFY COLUMN `status_code` varchar(99) NOT NULL DEFAULT 'ACTIVE' COMMENT 'Status Code 코드. Repository Metadata가 정의한 코드 체계로 관리한다. REFERENCE: te_common.cm_common_code의 group_code=STATUS_CODE. Generator, Engine 및 AI는 해당 Group의 code를 해석한다.',
    COMMENT = 'PURPOSE: 공통코드 구조와 값의 검사 결과 및 오류를 기록한다. ROLE: COMMON 공식 Repository. SSOT: 해당 Object 정의와 관계의 단일 원천. ENGINE_GUIDE: Generator, Engine 및 AI는 이 테이블을 Repository First로 해석하며 값과 규칙의 Hardcoding을 금지한다.';

/* te_common.cm_common_code */
ALTER TABLE `te_common`.`cm_common_code`
    MODIFY COLUMN `group_code` varchar(99) NOT NULL COMMENT 'Group Code 코드. Repository Metadata가 정의한 코드 체계로 관리한다. REFERENCE: UNRESOLVED. 공통코드 Group 또는 Master Repository 연결을 Metadata에서 확정해야 한다.',
    MODIFY COLUMN `code` varchar(99) NOT NULL COMMENT 'Code 값. cm_common_code Object의 해당 속성을 관리한다.',
    MODIFY COLUMN `code_name` varchar(150) NOT NULL COMMENT 'Code Name 명칭. 사람이 이해할 수 있는 표시 이름을 관리한다.',
    MODIFY COLUMN `sort_no` int(11) NOT NULL DEFAULT 0 COMMENT '표시 및 처리 순서를 제어하는 정렬 순번.',
    MODIFY COLUMN `status_code` varchar(99) NOT NULL DEFAULT 'ACTIVE' COMMENT 'Status Code 코드. Repository Metadata가 정의한 코드 체계로 관리한다. REFERENCE: te_common.cm_common_code의 group_code=STATUS_CODE. Generator, Engine 및 AI는 해당 Group의 code를 해석한다.',
    MODIFY COLUMN `created_dt` datetime NOT NULL DEFAULT current_timestamp() COMMENT 'Object 최초 생성 일시.',
    MODIFY COLUMN `created_by` varchar(99) NOT NULL DEFAULT 'SYSTEM' COMMENT 'Object를 최초 생성한 사용자 또는 실행 주체 식별자.',
    MODIFY COLUMN `updated_dt` datetime NOT NULL DEFAULT current_timestamp() ON UPDATE current_timestamp() COMMENT 'Object 최종 수정 일시.',
    MODIFY COLUMN `updated_by` varchar(99) NOT NULL DEFAULT 'SYSTEM' COMMENT 'Object를 최종 수정한 사용자 또는 실행 주체 식별자.',
    MODIFY COLUMN `client_ip` varchar(99) DEFAULT NULL COMMENT 'Object 변경 요청이 발생한 Client IP 주소.',
    MODIFY COLUMN `deleted_by` varchar(99) DEFAULT NULL COMMENT 'Object를 논리 삭제한 사용자 또는 실행 주체 식별자.',
    MODIFY COLUMN `deleted_dt` datetime DEFAULT NULL COMMENT 'Object 논리 삭제 처리 일시.',
    MODIFY COLUMN `program_id` varchar(99) DEFAULT NULL COMMENT 'Object 생성·수정·삭제를 수행한 Program 식별자.',
    COMMENT = 'PURPOSE: Framework 전체에서 사용하는 공통코드 값과 구조화 지식을 관리한다. ROLE: COMMON 공식 Repository. SSOT: 해당 Object 정의와 관계의 단일 원천. ENGINE_GUIDE: Generator, Engine 및 AI는 이 테이블을 Repository First로 해석하며 값과 규칙의 Hardcoding을 금지한다.';

/* te_common.cm_common_code_group */
ALTER TABLE `te_common`.`cm_common_code_group`
    MODIFY COLUMN `group_code` varchar(99) NOT NULL COMMENT 'Group Code 코드. Repository Metadata가 정의한 코드 체계로 관리한다. REFERENCE: UNRESOLVED. 공통코드 Group 또는 Master Repository 연결을 Metadata에서 확정해야 한다.',
    MODIFY COLUMN `group_name` varchar(150) NOT NULL COMMENT 'Group Name 명칭. 사람이 이해할 수 있는 표시 이름을 관리한다.',
    MODIFY COLUMN `sort_no` int(11) DEFAULT 0 COMMENT '표시 및 처리 순서를 제어하는 정렬 순번.',
    MODIFY COLUMN `status_code` varchar(99) NOT NULL DEFAULT 'ACTIVE' COMMENT 'Status Code 코드. Repository Metadata가 정의한 코드 체계로 관리한다. REFERENCE: te_common.cm_common_code의 group_code=STATUS_CODE. Generator, Engine 및 AI는 해당 Group의 code를 해석한다.',
    MODIFY COLUMN `created_dt` datetime NOT NULL DEFAULT current_timestamp() COMMENT 'Object 최초 생성 일시.',
    MODIFY COLUMN `created_by` varchar(99) NOT NULL DEFAULT 'SYSTEM' COMMENT 'Object를 최초 생성한 사용자 또는 실행 주체 식별자.',
    MODIFY COLUMN `updated_dt` datetime NOT NULL DEFAULT current_timestamp() ON UPDATE current_timestamp() COMMENT 'Object 최종 수정 일시.',
    MODIFY COLUMN `updated_by` varchar(99) NOT NULL DEFAULT 'SYSTEM' COMMENT 'Object를 최종 수정한 사용자 또는 실행 주체 식별자.',
    MODIFY COLUMN `client_ip` varchar(99) DEFAULT NULL COMMENT 'Object 변경 요청이 발생한 Client IP 주소.',
    MODIFY COLUMN `deleted_by` varchar(99) DEFAULT NULL COMMENT 'Object를 논리 삭제한 사용자 또는 실행 주체 식별자.',
    MODIFY COLUMN `deleted_dt` datetime DEFAULT NULL COMMENT 'Object 논리 삭제 처리 일시.',
    MODIFY COLUMN `program_id` varchar(99) DEFAULT NULL COMMENT 'Object 생성·수정·삭제를 수행한 Program 식별자.',
    COMMENT = 'PURPOSE: 공통코드 Group의 의미, 범위 및 운영 정책을 관리한다. ROLE: COMMON 공식 Repository. SSOT: 해당 Object 정의와 관계의 단일 원천. ENGINE_GUIDE: Generator, Engine 및 AI는 이 테이블을 Repository First로 해석하며 값과 규칙의 Hardcoding을 금지한다.';

/* te_common.cm_consent_history */
ALTER TABLE `te_common`.`cm_consent_history`
    MODIFY COLUMN `consent_history_id` varchar(99) NOT NULL COMMENT 'Consent History Id 식별자. cm_consent_history Object와 관련 Object를 식별하거나 연결한다.',
    MODIFY COLUMN `user_id` varchar(99) NOT NULL COMMENT 'User Id 식별자. cm_consent_history Object와 관련 Object를 식별하거나 연결한다.',
    MODIFY COLUMN `consent_type` varchar(99) NOT NULL COMMENT 'Consent Type 값. cm_consent_history Object의 해당 속성을 관리한다.',
    MODIFY COLUMN `consent_yn` char(1) NOT NULL COMMENT 'Consent Yn 여부. Y 또는 N 값으로 관리한다.',
    MODIFY COLUMN `created_by` varchar(99) NOT NULL COMMENT 'Object를 최초 생성한 사용자 또는 실행 주체 식별자.',
    MODIFY COLUMN `created_dt` datetime NOT NULL DEFAULT current_timestamp() COMMENT 'Object 최초 생성 일시.',
    MODIFY COLUMN `updated_by` varchar(99) DEFAULT NULL COMMENT 'Object를 최종 수정한 사용자 또는 실행 주체 식별자.',
    MODIFY COLUMN `updated_dt` datetime DEFAULT NULL COMMENT 'Object 최종 수정 일시.',
    MODIFY COLUMN `deleted_by` varchar(99) DEFAULT NULL COMMENT 'Object를 논리 삭제한 사용자 또는 실행 주체 식별자.',
    MODIFY COLUMN `deleted_dt` datetime DEFAULT NULL COMMENT 'Object 논리 삭제 처리 일시.',
    MODIFY COLUMN `change_story` varchar(2000) DEFAULT NULL COMMENT 'Change Story 값. cm_consent_history Object의 해당 속성을 관리한다.',
    MODIFY COLUMN `client_ip` varchar(99) DEFAULT NULL COMMENT 'Object 변경 요청이 발생한 Client IP 주소.',
    MODIFY COLUMN `program_id` varchar(99) DEFAULT NULL COMMENT 'Object 생성·수정·삭제를 수행한 Program 식별자.',
    MODIFY COLUMN `status_code` varchar(99) NOT NULL DEFAULT 'ACTIVE' COMMENT 'Status Code 코드. Repository Metadata가 정의한 코드 체계로 관리한다. REFERENCE: te_common.cm_common_code의 group_code=STATUS_CODE. Generator, Engine 및 AI는 해당 Group의 code를 해석한다.',
    COMMENT = 'PURPOSE: 사용자의 동의 유형별 획득·변경·철회 이력을 관리한다. ROLE: COMMON 공식 Repository. SSOT: 해당 이력과 실행 결과의 공식 원천. ENGINE_GUIDE: Generator, Engine 및 AI는 이 테이블을 Repository First로 해석하며 값과 규칙의 Hardcoding을 금지한다.';

/* te_common.cm_country */
ALTER TABLE `te_common`.`cm_country`
    MODIFY COLUMN `country_code` varchar(99) NOT NULL COMMENT 'Country Code 코드. Repository Metadata가 정의한 코드 체계로 관리한다. REFERENCE: COMMON.cm_country(country_code). 해당 Master Repository를 공식 연결 원천으로 사용한다.',
    MODIFY COLUMN `country_name` varchar(150) NOT NULL COMMENT 'Country Name 명칭. 사람이 이해할 수 있는 표시 이름을 관리한다.',
    MODIFY COLUMN `native_name` varchar(150) DEFAULT NULL COMMENT 'Native Name 명칭. 사람이 이해할 수 있는 표시 이름을 관리한다.',
    MODIFY COLUMN `sort_no` int(11) NOT NULL DEFAULT 0 COMMENT '표시 및 처리 순서를 제어하는 정렬 순번.',
    MODIFY COLUMN `status_code` varchar(99) NOT NULL DEFAULT 'ACTIVE' COMMENT 'Status Code 코드. Repository Metadata가 정의한 코드 체계로 관리한다. REFERENCE: te_common.cm_common_code의 group_code=STATUS_CODE. Generator, Engine 및 AI는 해당 Group의 code를 해석한다.',
    MODIFY COLUMN `created_dt` datetime NOT NULL DEFAULT current_timestamp() COMMENT 'Object 최초 생성 일시.',
    MODIFY COLUMN `created_by` varchar(99) NOT NULL DEFAULT 'SYSTEM' COMMENT 'Object를 최초 생성한 사용자 또는 실행 주체 식별자.',
    MODIFY COLUMN `updated_dt` datetime NOT NULL DEFAULT current_timestamp() ON UPDATE current_timestamp() COMMENT 'Object 최종 수정 일시.',
    MODIFY COLUMN `updated_by` varchar(99) NOT NULL DEFAULT 'SYSTEM' COMMENT 'Object를 최종 수정한 사용자 또는 실행 주체 식별자.',
    MODIFY COLUMN `client_ip` varchar(99) DEFAULT NULL COMMENT 'Object 변경 요청이 발생한 Client IP 주소.',
    MODIFY COLUMN `deleted_by` varchar(99) DEFAULT NULL COMMENT 'Object를 논리 삭제한 사용자 또는 실행 주체 식별자.',
    MODIFY COLUMN `deleted_dt` datetime DEFAULT NULL COMMENT 'Object 논리 삭제 처리 일시.',
    MODIFY COLUMN `program_id` varchar(99) DEFAULT NULL COMMENT 'Object 생성·수정·삭제를 수행한 Program 식별자.',
    COMMENT = 'PURPOSE: 국가 코드와 국가 명칭의 공식 Master를 관리한다. ROLE: COMMON 공식 Repository. SSOT: 해당 Object 정의와 관계의 단일 원천. ENGINE_GUIDE: Generator, Engine 및 AI는 이 테이블을 Repository First로 해석하며 값과 규칙의 Hardcoding을 금지한다.';

/* te_common.cm_data_classification */
ALTER TABLE `te_common`.`cm_data_classification`
    MODIFY COLUMN `classification_code` varchar(99) NOT NULL COMMENT '데이터 등급 코드 REFERENCE: COMMON.cm_data_classification(classification_code). 해당 Master Repository를 공식 연결 원천으로 사용한다.',
    MODIFY COLUMN `description` varchar(2000) DEFAULT NULL COMMENT 'Description 값. cm_data_classification Object의 해당 속성을 관리한다.',
    MODIFY COLUMN `encryption_required_yn` char(1) DEFAULT 'N' COMMENT 'Encryption Required Yn 여부. Y 또는 N 값으로 관리한다.',
    MODIFY COLUMN `masking_required_yn` char(1) DEFAULT 'N' COMMENT 'Masking Required Yn 여부. Y 또는 N 값으로 관리한다.',
    MODIFY COLUMN `ai_access_allowed_yn` char(1) DEFAULT 'Y' COMMENT 'Ai Access Allowed Yn 여부. Y 또는 N 값으로 관리한다.',
    MODIFY COLUMN `external_transfer_allowed_yn` char(1) DEFAULT 'N' COMMENT 'External Transfer Allowed Yn 여부. Y 또는 N 값으로 관리한다.',
    MODIFY COLUMN `created_by` varchar(99) NOT NULL DEFAULT 'SYSTEM' COMMENT 'Object를 최초 생성한 사용자 또는 실행 주체 식별자.',
    MODIFY COLUMN `created_dt` datetime NOT NULL DEFAULT current_timestamp() COMMENT 'Object 최초 생성 일시.',
    MODIFY COLUMN `updated_by` varchar(99) DEFAULT NULL COMMENT 'Object를 최종 수정한 사용자 또는 실행 주체 식별자.',
    MODIFY COLUMN `updated_dt` datetime DEFAULT NULL COMMENT 'Object 최종 수정 일시.',
    MODIFY COLUMN `deleted_by` varchar(99) DEFAULT NULL COMMENT 'Object를 논리 삭제한 사용자 또는 실행 주체 식별자.',
    MODIFY COLUMN `deleted_dt` datetime DEFAULT NULL COMMENT 'Object 논리 삭제 처리 일시.',
    MODIFY COLUMN `client_ip` varchar(99) DEFAULT NULL COMMENT 'Object 변경 요청이 발생한 Client IP 주소.',
    MODIFY COLUMN `program_id` varchar(99) DEFAULT NULL COMMENT 'Object 생성·수정·삭제를 수행한 Program 식별자.',
    MODIFY COLUMN `status_code` varchar(99) NOT NULL DEFAULT 'ACTIVE' COMMENT 'Status Code 코드. Repository Metadata가 정의한 코드 체계로 관리한다. REFERENCE: te_common.cm_common_code의 group_code=STATUS_CODE. Generator, Engine 및 AI는 해당 Group의 code를 해석한다.',
    COMMENT = 'PURPOSE: 데이터 보안·민감도 분류 기준의 공식 Master를 관리한다. ROLE: COMMON 공식 Repository. SSOT: 해당 Object 정의와 관계의 단일 원천. ENGINE_GUIDE: Generator, Engine 및 AI는 이 테이블을 Repository First로 해석하며 값과 규칙의 Hardcoding을 금지한다.';

/* te_common.cm_data_lifecycle_index */
ALTER TABLE `te_common`.`cm_data_lifecycle_index`
    MODIFY COLUMN `status_code` varchar(99) NOT NULL COMMENT '상태 REFERENCE: te_common.cm_common_code의 group_code=STATUS_CODE. Generator, Engine 및 AI는 해당 Group의 code를 해석한다.',
    MODIFY COLUMN `created_dt` datetime NOT NULL DEFAULT current_timestamp() COMMENT 'Object 최초 생성 일시.',
    MODIFY COLUMN `updated_dt` datetime DEFAULT NULL COMMENT 'Object 최종 수정 일시.',
    MODIFY COLUMN `created_by` varchar(99) NOT NULL DEFAULT 'SYSTEM' COMMENT 'Object를 최초 생성한 사용자 또는 실행 주체 식별자.',
    MODIFY COLUMN `updated_by` varchar(99) DEFAULT NULL COMMENT 'Object를 최종 수정한 사용자 또는 실행 주체 식별자.',
    MODIFY COLUMN `deleted_by` varchar(99) DEFAULT NULL COMMENT 'Object를 논리 삭제한 사용자 또는 실행 주체 식별자.',
    MODIFY COLUMN `deleted_dt` datetime DEFAULT NULL COMMENT 'Object 논리 삭제 처리 일시.',
    MODIFY COLUMN `change_story` varchar(2000) DEFAULT NULL COMMENT 'Change Story 값. cm_data_lifecycle_index Object의 해당 속성을 관리한다.',
    MODIFY COLUMN `client_ip` varchar(99) DEFAULT NULL COMMENT 'Object 변경 요청이 발생한 Client IP 주소.',
    MODIFY COLUMN `program_id` varchar(99) DEFAULT NULL COMMENT 'Object 생성·수정·삭제를 수행한 Program 식별자.',
    COMMENT = 'PURPOSE: Repository와 Storage에 분산된 데이터 자산의 보관·폐기 Lifecycle을 추적한다. ROLE: COMMON 공식 Repository. SSOT: 해당 Object 정의와 관계의 단일 원천. ENGINE_GUIDE: Generator, Engine 및 AI는 이 테이블을 Repository First로 해석하며 값과 규칙의 Hardcoding을 금지한다.';

/* te_common.cm_data_type */
ALTER TABLE `te_common`.`cm_data_type`
    MODIFY COLUMN `data_type_code` varchar(99) NOT NULL COMMENT 'Data Type Code 코드. Repository Metadata가 정의한 코드 체계로 관리한다. REFERENCE: te_common.cm_common_code의 group_code=CM_DATA_TYPE. Generator, Engine 및 AI는 해당 Group의 code를 해석한다.',
    MODIFY COLUMN `data_type_name` varchar(150) DEFAULT NULL COMMENT 'Data Type Name 명칭. 사람이 이해할 수 있는 표시 이름을 관리한다.',
    MODIFY COLUMN `description` varchar(2000) DEFAULT NULL COMMENT 'Description 값. cm_data_type Object의 해당 속성을 관리한다.',
    MODIFY COLUMN `default_classification_code` varchar(99) DEFAULT NULL COMMENT 'Default Classification Code 코드. Repository Metadata가 정의한 코드 체계로 관리한다. REFERENCE: COMMON.cm_data_classification(classification_code). 해당 Master Repository를 공식 연결 원천으로 사용한다.',
    MODIFY COLUMN `default_storage_type` varchar(99) DEFAULT NULL COMMENT 'Default Storage Type 값. cm_data_type Object의 해당 속성을 관리한다.',
    MODIFY COLUMN `default_retention_policy_code` varchar(99) DEFAULT NULL COMMENT 'Default Retention Policy Code 코드. Repository Metadata가 정의한 코드 체계로 관리한다. REFERENCE: UNRESOLVED. 공통코드 Group 또는 Master Repository 연결을 Metadata에서 확정해야 한다.',
    MODIFY COLUMN `ai_analysis_allowed_yn` char(1) DEFAULT 'Y' COMMENT 'Ai Analysis Allowed Yn 여부. Y 또는 N 값으로 관리한다.',
    MODIFY COLUMN `encryption_required_yn` char(1) DEFAULT 'N' COMMENT 'Encryption Required Yn 여부. Y 또는 N 값으로 관리한다.',
    MODIFY COLUMN `created_by` varchar(99) NOT NULL DEFAULT 'SYSTEM' COMMENT 'Object를 최초 생성한 사용자 또는 실행 주체 식별자.',
    MODIFY COLUMN `created_dt` datetime NOT NULL DEFAULT current_timestamp() COMMENT 'Object 최초 생성 일시.',
    MODIFY COLUMN `updated_by` varchar(99) DEFAULT NULL COMMENT 'Object를 최종 수정한 사용자 또는 실행 주체 식별자.',
    MODIFY COLUMN `updated_dt` datetime DEFAULT NULL COMMENT 'Object 최종 수정 일시.',
    MODIFY COLUMN `deleted_by` varchar(99) DEFAULT NULL COMMENT 'Object를 논리 삭제한 사용자 또는 실행 주체 식별자.',
    MODIFY COLUMN `deleted_dt` datetime DEFAULT NULL COMMENT 'Object 논리 삭제 처리 일시.',
    MODIFY COLUMN `client_ip` varchar(99) DEFAULT NULL COMMENT 'Object 변경 요청이 발생한 Client IP 주소.',
    MODIFY COLUMN `program_id` varchar(99) DEFAULT NULL COMMENT 'Object 생성·수정·삭제를 수행한 Program 식별자.',
    MODIFY COLUMN `status_code` varchar(99) NOT NULL DEFAULT 'ACTIVE' COMMENT 'Status Code 코드. Repository Metadata가 정의한 코드 체계로 관리한다. REFERENCE: te_common.cm_common_code의 group_code=STATUS_CODE. Generator, Engine 및 AI는 해당 Group의 code를 해석한다.',
    COMMENT = 'PURPOSE: Repository 자료 유형과 기본 분류·저장·보존 정책을 관리한다. ROLE: COMMON 공식 Repository. SSOT: 해당 Object 정의와 관계의 단일 원천. ENGINE_GUIDE: Generator, Engine 및 AI는 이 테이블을 Repository First로 해석하며 값과 규칙의 Hardcoding을 금지한다.';

/* te_common.cm_language */
ALTER TABLE `te_common`.`cm_language`
    MODIFY COLUMN `language_code` varchar(99) NOT NULL COMMENT 'Language Code 코드. Repository Metadata가 정의한 코드 체계로 관리한다. REFERENCE: COMMON.cm_language(language_code). 해당 Master Repository를 공식 연결 원천으로 사용한다.',
    MODIFY COLUMN `language_name` varchar(150) NOT NULL COMMENT 'Language Name 명칭. 사람이 이해할 수 있는 표시 이름을 관리한다.',
    MODIFY COLUMN `native_name` varchar(150) NOT NULL COMMENT 'Native Name 명칭. 사람이 이해할 수 있는 표시 이름을 관리한다.',
    MODIFY COLUMN `sort_no` int(11) NOT NULL DEFAULT 0 COMMENT '표시 및 처리 순서를 제어하는 정렬 순번.',
    MODIFY COLUMN `status_code` varchar(99) NOT NULL DEFAULT 'ACTIVE' COMMENT 'Status Code 코드. Repository Metadata가 정의한 코드 체계로 관리한다. REFERENCE: te_common.cm_common_code의 group_code=STATUS_CODE. Generator, Engine 및 AI는 해당 Group의 code를 해석한다.',
    MODIFY COLUMN `created_dt` datetime NOT NULL DEFAULT current_timestamp() COMMENT 'Object 최초 생성 일시.',
    MODIFY COLUMN `created_by` varchar(99) NOT NULL DEFAULT 'SYSTEM' COMMENT 'Object를 최초 생성한 사용자 또는 실행 주체 식별자.',
    MODIFY COLUMN `updated_dt` datetime NOT NULL DEFAULT current_timestamp() ON UPDATE current_timestamp() COMMENT 'Object 최종 수정 일시.',
    MODIFY COLUMN `updated_by` varchar(99) NOT NULL DEFAULT 'SYSTEM' COMMENT 'Object를 최종 수정한 사용자 또는 실행 주체 식별자.',
    MODIFY COLUMN `client_ip` varchar(99) DEFAULT NULL COMMENT 'Object 변경 요청이 발생한 Client IP 주소.',
    MODIFY COLUMN `deleted_by` varchar(99) DEFAULT NULL COMMENT 'Object를 논리 삭제한 사용자 또는 실행 주체 식별자.',
    MODIFY COLUMN `deleted_dt` datetime DEFAULT NULL COMMENT 'Object 논리 삭제 처리 일시.',
    MODIFY COLUMN `program_id` varchar(99) DEFAULT NULL COMMENT 'Object 생성·수정·삭제를 수행한 Program 식별자.',
    COMMENT = 'PURPOSE: 지원 언어 코드와 언어 명칭의 공식 Master를 관리한다. ROLE: COMMON 공식 Repository. SSOT: 해당 Object 정의와 관계의 단일 원천. ENGINE_GUIDE: Generator, Engine 및 AI는 이 테이블을 Repository First로 해석하며 값과 규칙의 Hardcoding을 금지한다.';

/* te_common.cm_legal_retention_policy */
ALTER TABLE `te_common`.`cm_legal_retention_policy`
    MODIFY COLUMN `legal_basis_code` varchar(99) NOT NULL COMMENT '법적 근거 코드 REFERENCE: UNRESOLVED. 공통코드 Group 또는 Master Repository 연결을 Metadata에서 확정해야 한다.',
    MODIFY COLUMN `disposal_action_code` varchar(99) NOT NULL COMMENT '보존기간 만료 후 처리 방식 REFERENCE: UNRESOLVED. 공통코드 Group 또는 Master Repository 연결을 Metadata에서 확정해야 한다.',
    MODIFY COLUMN `created_by` varchar(99) NOT NULL DEFAULT 'SYSTEM' COMMENT 'Object를 최초 생성한 사용자 또는 실행 주체 식별자.',
    MODIFY COLUMN `created_dt` datetime NOT NULL DEFAULT current_timestamp() COMMENT 'Object 최초 생성 일시.',
    MODIFY COLUMN `updated_by` varchar(99) DEFAULT NULL COMMENT 'Object를 최종 수정한 사용자 또는 실행 주체 식별자.',
    MODIFY COLUMN `updated_dt` datetime DEFAULT NULL COMMENT 'Object 최종 수정 일시.',
    MODIFY COLUMN `deleted_by` varchar(99) DEFAULT NULL COMMENT 'Object를 논리 삭제한 사용자 또는 실행 주체 식별자.',
    MODIFY COLUMN `deleted_dt` datetime DEFAULT NULL COMMENT 'Object 논리 삭제 처리 일시.',
    MODIFY COLUMN `client_ip` varchar(99) DEFAULT NULL COMMENT 'Object 변경 요청이 발생한 Client IP 주소.',
    MODIFY COLUMN `program_id` varchar(99) DEFAULT NULL COMMENT 'Object 생성·수정·삭제를 수행한 Program 식별자.',
    MODIFY COLUMN `status_code` varchar(99) NOT NULL DEFAULT 'ACTIVE' COMMENT 'Status Code 코드. Repository Metadata가 정의한 코드 체계로 관리한다. REFERENCE: te_common.cm_common_code의 group_code=STATUS_CODE. Generator, Engine 및 AI는 해당 Group의 code를 해석한다.',
    COMMENT = 'PURPOSE: 법적 근거에 따른 데이터 보존 기간과 폐기 조치를 관리한다. ROLE: COMMON 공식 Repository. SSOT: 해당 Object 정의와 관계의 단일 원천. ENGINE_GUIDE: Generator, Engine 및 AI는 이 테이블을 Repository First로 해석하며 값과 규칙의 Hardcoding을 금지한다.';

/* te_common.cm_locale */
ALTER TABLE `te_common`.`cm_locale`
    MODIFY COLUMN `locale_code` varchar(99) NOT NULL COMMENT 'Locale Code 코드. Repository Metadata가 정의한 코드 체계로 관리한다. REFERENCE: COMMON.cm_locale(locale_code). 해당 Master Repository를 공식 연결 원천으로 사용한다.',
    MODIFY COLUMN `language_code` varchar(99) NOT NULL COMMENT 'Language Code 코드. Repository Metadata가 정의한 코드 체계로 관리한다. REFERENCE: COMMON.cm_language(language_code). 해당 Master Repository를 공식 연결 원천으로 사용한다.',
    MODIFY COLUMN `country_code` varchar(99) NOT NULL COMMENT 'Country Code 코드. Repository Metadata가 정의한 코드 체계로 관리한다. REFERENCE: COMMON.cm_country(country_code). 해당 Master Repository를 공식 연결 원천으로 사용한다.',
    MODIFY COLUMN `locale_name` varchar(150) NOT NULL COMMENT 'Locale Name 명칭. 사람이 이해할 수 있는 표시 이름을 관리한다.',
    MODIFY COLUMN `native_name` varchar(150) NOT NULL COMMENT 'Native Name 명칭. 사람이 이해할 수 있는 표시 이름을 관리한다.',
    MODIFY COLUMN `date_format` varchar(99) DEFAULT NULL COMMENT 'Date Format 값. cm_locale Object의 해당 속성을 관리한다.',
    MODIFY COLUMN `time_format` varchar(99) DEFAULT NULL COMMENT 'Time Format 값. cm_locale Object의 해당 속성을 관리한다.',
    MODIFY COLUMN `datetime_format` varchar(99) DEFAULT NULL COMMENT 'Datetime Format 값. cm_locale Object의 해당 속성을 관리한다.',
    MODIFY COLUMN `number_format` varchar(99) DEFAULT NULL COMMENT 'Number Format 값. cm_locale Object의 해당 속성을 관리한다.',
    MODIFY COLUMN `timezone_id` varchar(99) DEFAULT NULL COMMENT 'Timezone Id 식별자. cm_locale Object와 관련 Object를 식별하거나 연결한다.',
    MODIFY COLUMN `sort_no` int(11) NOT NULL DEFAULT 0 COMMENT '표시 및 처리 순서를 제어하는 정렬 순번.',
    MODIFY COLUMN `status_code` varchar(99) NOT NULL DEFAULT 'ACTIVE' COMMENT 'Status Code 코드. Repository Metadata가 정의한 코드 체계로 관리한다. REFERENCE: te_common.cm_common_code의 group_code=STATUS_CODE. Generator, Engine 및 AI는 해당 Group의 code를 해석한다.',
    MODIFY COLUMN `created_dt` datetime NOT NULL DEFAULT current_timestamp() COMMENT 'Object 최초 생성 일시.',
    MODIFY COLUMN `created_by` varchar(99) NOT NULL DEFAULT 'SYSTEM' COMMENT 'Object를 최초 생성한 사용자 또는 실행 주체 식별자.',
    MODIFY COLUMN `updated_dt` datetime NOT NULL DEFAULT current_timestamp() ON UPDATE current_timestamp() COMMENT 'Object 최종 수정 일시.',
    MODIFY COLUMN `updated_by` varchar(99) NOT NULL DEFAULT 'SYSTEM' COMMENT 'Object를 최종 수정한 사용자 또는 실행 주체 식별자.',
    MODIFY COLUMN `deleted_by` varchar(99) DEFAULT NULL COMMENT 'Object를 논리 삭제한 사용자 또는 실행 주체 식별자.',
    MODIFY COLUMN `deleted_dt` datetime DEFAULT NULL COMMENT 'Object 논리 삭제 처리 일시.',
    MODIFY COLUMN `client_ip` varchar(99) DEFAULT NULL COMMENT 'Object 변경 요청이 발생한 Client IP 주소.',
    MODIFY COLUMN `program_id` varchar(99) DEFAULT NULL COMMENT 'Object 생성·수정·삭제를 수행한 Program 식별자.',
    COMMENT = 'PURPOSE: 언어·국가 조합별 Locale과 표시 형식을 관리한다. ROLE: COMMON 공식 Repository. SSOT: 해당 Object 정의와 관계의 단일 원천. ENGINE_GUIDE: Generator, Engine 및 AI는 이 테이블을 Repository First로 해석하며 값과 규칙의 Hardcoding을 금지한다.';

/* te_common.cm_login_history */
ALTER TABLE `te_common`.`cm_login_history`
    MODIFY COLUMN `login_history_id` varchar(99) NOT NULL COMMENT 'Login History Id 식별자. cm_login_history Object와 관련 Object를 식별하거나 연결한다.',
    MODIFY COLUMN `member_id` varchar(99) DEFAULT NULL COMMENT 'Member Id 식별자. cm_login_history Object와 관련 Object를 식별하거나 연결한다.',
    MODIFY COLUMN `login_id` varchar(99) NOT NULL COMMENT 'Login Id 식별자. cm_login_history Object와 관련 Object를 식별하거나 연결한다.',
    MODIFY COLUMN `login_status_code` varchar(99) NOT NULL COMMENT 'Login Status Code 코드. Repository Metadata가 정의한 코드 체계로 관리한다. REFERENCE: te_common.cm_common_code의 group_code=AU_LOGIN_STATUS. Generator, Engine 및 AI는 해당 Group의 code를 해석한다.',
    MODIFY COLUMN `client_ip` varchar(99) DEFAULT NULL COMMENT 'Object 변경 요청이 발생한 Client IP 주소.',
    MODIFY COLUMN `user_agent` varchar(500) DEFAULT NULL COMMENT 'User Agent 값. cm_login_history Object의 해당 속성을 관리한다.',
    MODIFY COLUMN `login_dt` datetime NOT NULL DEFAULT current_timestamp() COMMENT 'Login Dt 일시. Object의 해당 Event 발생 시점을 관리한다.',
    MODIFY COLUMN `status_code` varchar(99) NOT NULL DEFAULT 'ACTIVE' COMMENT 'Status Code 코드. Repository Metadata가 정의한 코드 체계로 관리한다. REFERENCE: te_common.cm_common_code의 group_code=STATUS_CODE. Generator, Engine 및 AI는 해당 Group의 code를 해석한다.',
    COMMENT = 'PURPOSE: 회원 로그인 시도 결과와 접속 정보를 추적한다. ROLE: COMMON 공식 Repository. SSOT: 해당 이력과 실행 결과의 공식 원천. ENGINE_GUIDE: Generator, Engine 및 AI는 이 테이블을 Repository First로 해석하며 값과 규칙의 Hardcoding을 금지한다.';

/* te_common.cm_member */
ALTER TABLE `te_common`.`cm_member`
    MODIFY COLUMN `member_id` varchar(99) NOT NULL COMMENT 'Member Id 식별자. cm_member Object와 관련 Object를 식별하거나 연결한다.',
    MODIFY COLUMN `email` varchar(500) NOT NULL COMMENT 'Email 값. cm_member Object의 해당 속성을 관리한다.',
    MODIFY COLUMN `password_hash` varchar(128) NOT NULL COMMENT 'Password Hash 값. cm_member Object의 해당 속성을 관리한다.',
    MODIFY COLUMN `member_name` varchar(150) NOT NULL COMMENT 'Member Name 명칭. 사람이 이해할 수 있는 표시 이름을 관리한다.',
    MODIFY COLUMN `member_type_code` varchar(99) NOT NULL COMMENT 'Member Type Code 코드. Repository Metadata가 정의한 코드 체계로 관리한다. REFERENCE: te_common.cm_common_code의 group_code=MB_MEMBER_TYPE. Generator, Engine 및 AI는 해당 Group의 code를 해석한다.',
    MODIFY COLUMN `created_dt` datetime NOT NULL DEFAULT current_timestamp() COMMENT 'Object 최초 생성 일시.',
    MODIFY COLUMN `created_by` varchar(99) NOT NULL DEFAULT 'SYSTEM' COMMENT 'Object를 최초 생성한 사용자 또는 실행 주체 식별자.',
    MODIFY COLUMN `updated_dt` datetime NOT NULL DEFAULT current_timestamp() ON UPDATE current_timestamp() COMMENT 'Object 최종 수정 일시.',
    MODIFY COLUMN `updated_by` varchar(99) NOT NULL DEFAULT 'SYSTEM' COMMENT 'Object를 최종 수정한 사용자 또는 실행 주체 식별자.',
    MODIFY COLUMN `client_ip` varchar(99) DEFAULT NULL COMMENT 'Object 변경 요청이 발생한 Client IP 주소.',
    MODIFY COLUMN `deleted_by` varchar(99) DEFAULT NULL COMMENT 'Object를 논리 삭제한 사용자 또는 실행 주체 식별자.',
    MODIFY COLUMN `deleted_dt` datetime DEFAULT NULL COMMENT 'Object 논리 삭제 처리 일시.',
    MODIFY COLUMN `program_id` varchar(99) DEFAULT NULL COMMENT 'Object 생성·수정·삭제를 수행한 Program 식별자.',
    MODIFY COLUMN `status_code` varchar(99) NOT NULL DEFAULT 'ACTIVE' COMMENT 'Status Code 코드. Repository Metadata가 정의한 코드 체계로 관리한다. REFERENCE: te_common.cm_common_code의 group_code=STATUS_CODE. Generator, Engine 및 AI는 해당 Group의 code를 해석한다.',
    COMMENT = 'PURPOSE: Framework 회원의 인증·식별·상태 정보를 관리한다. ROLE: COMMON 공식 Repository. SSOT: 해당 Object 정의와 관계의 단일 원천. ENGINE_GUIDE: Generator, Engine 및 AI는 이 테이블을 Repository First로 해석하며 값과 규칙의 Hardcoding을 금지한다.';

/* te_common.cm_member_private */
ALTER TABLE `te_common`.`cm_member_private`
    MODIFY COLUMN `member_id` varchar(99) NOT NULL COMMENT 'Member Id 식별자. cm_member_private Object와 관련 Object를 식별하거나 연결한다.',
    MODIFY COLUMN `birth_dt` datetime DEFAULT NULL COMMENT 'Birth Dt 일시. Object의 해당 Event 발생 시점을 관리한다.',
    MODIFY COLUMN `phone` varchar(50) DEFAULT NULL COMMENT 'Phone 값. cm_member_private Object의 해당 속성을 관리한다.',
    MODIFY COLUMN `email` varchar(500) DEFAULT NULL COMMENT 'Email 값. cm_member_private Object의 해당 속성을 관리한다.',
    MODIFY COLUMN `address` varchar(500) DEFAULT NULL COMMENT 'Address 값. cm_member_private Object의 해당 속성을 관리한다.',
    MODIFY COLUMN `created_dt` datetime NOT NULL DEFAULT current_timestamp() COMMENT 'Object 최초 생성 일시.',
    MODIFY COLUMN `created_by` varchar(99) NOT NULL DEFAULT 'SYSTEM' COMMENT 'Object를 최초 생성한 사용자 또는 실행 주체 식별자.',
    MODIFY COLUMN `updated_dt` datetime NOT NULL DEFAULT current_timestamp() ON UPDATE current_timestamp() COMMENT 'Object 최종 수정 일시.',
    MODIFY COLUMN `updated_by` varchar(99) NOT NULL DEFAULT 'SYSTEM' COMMENT 'Object를 최종 수정한 사용자 또는 실행 주체 식별자.',
    MODIFY COLUMN `client_ip` varchar(99) DEFAULT NULL COMMENT 'Object 변경 요청이 발생한 Client IP 주소.',
    MODIFY COLUMN `deleted_by` varchar(99) DEFAULT NULL COMMENT 'Object를 논리 삭제한 사용자 또는 실행 주체 식별자.',
    MODIFY COLUMN `deleted_dt` datetime DEFAULT NULL COMMENT 'Object 논리 삭제 처리 일시.',
    MODIFY COLUMN `program_id` varchar(99) DEFAULT NULL COMMENT 'Object 생성·수정·삭제를 수행한 Program 식별자.',
    MODIFY COLUMN `status_code` varchar(99) NOT NULL DEFAULT 'ACTIVE' COMMENT 'Status Code 코드. Repository Metadata가 정의한 코드 체계로 관리한다. REFERENCE: te_common.cm_common_code의 group_code=STATUS_CODE. Generator, Engine 및 AI는 해당 Group의 code를 해석한다.',
    COMMENT = 'PURPOSE: 회원의 민감 개인정보를 일반 회원 정보와 분리하여 관리한다. ROLE: COMMON 공식 Repository. SSOT: 해당 Object 정의와 관계의 단일 원천. ENGINE_GUIDE: Generator, Engine 및 AI는 이 테이블을 Repository First로 해석하며 값과 규칙의 Hardcoding을 금지한다.';

/* te_common.cm_member_role */
ALTER TABLE `te_common`.`cm_member_role`
    MODIFY COLUMN `member_role_id` varchar(99) NOT NULL COMMENT 'Member Role Id 식별자. cm_member_role Object와 관련 Object를 식별하거나 연결한다.',
    MODIFY COLUMN `member_id` varchar(99) NOT NULL COMMENT 'Member Id 식별자. cm_member_role Object와 관련 Object를 식별하거나 연결한다.',
    MODIFY COLUMN `role_id` varchar(99) NOT NULL COMMENT 'Role Id 식별자. cm_member_role Object와 관련 Object를 식별하거나 연결한다.',
    MODIFY COLUMN `created_dt` datetime NOT NULL DEFAULT current_timestamp() COMMENT 'Object 최초 생성 일시.',
    MODIFY COLUMN `created_by` varchar(99) NOT NULL DEFAULT 'SYSTEM' COMMENT 'Object를 최초 생성한 사용자 또는 실행 주체 식별자.',
    MODIFY COLUMN `updated_dt` datetime NOT NULL DEFAULT current_timestamp() ON UPDATE current_timestamp() COMMENT 'Object 최종 수정 일시.',
    MODIFY COLUMN `updated_by` varchar(99) NOT NULL DEFAULT 'SYSTEM' COMMENT 'Object를 최종 수정한 사용자 또는 실행 주체 식별자.',
    MODIFY COLUMN `client_ip` varchar(99) DEFAULT NULL COMMENT 'Object 변경 요청이 발생한 Client IP 주소.',
    MODIFY COLUMN `deleted_by` varchar(99) DEFAULT NULL COMMENT 'Object를 논리 삭제한 사용자 또는 실행 주체 식별자.',
    MODIFY COLUMN `deleted_dt` datetime DEFAULT NULL COMMENT 'Object 논리 삭제 처리 일시.',
    MODIFY COLUMN `program_id` varchar(99) DEFAULT NULL COMMENT 'Object 생성·수정·삭제를 수행한 Program 식별자.',
    MODIFY COLUMN `status_code` varchar(99) NOT NULL DEFAULT 'ACTIVE' COMMENT 'Status Code 코드. Repository Metadata가 정의한 코드 체계로 관리한다. REFERENCE: te_common.cm_common_code의 group_code=STATUS_CODE. Generator, Engine 및 AI는 해당 Group의 code를 해석한다.',
    COMMENT = 'PURPOSE: 회원과 Role 사이의 권한 부여 관계를 관리한다. ROLE: COMMON 공식 Repository. SSOT: 해당 Object 정의와 관계의 단일 원천. ENGINE_GUIDE: Generator, Engine 및 AI는 이 테이블을 Repository First로 해석하며 값과 규칙의 Hardcoding을 금지한다.';

/* te_common.cm_repository */
ALTER TABLE `te_common`.`cm_repository`
    MODIFY COLUMN `book_code` varchar(99) DEFAULT NULL COMMENT 'Story Book 코드 REFERENCE: UNRESOLVED. 공통코드 Group 또는 Master Repository 연결을 Metadata에서 확정해야 한다.',
    MODIFY COLUMN `chapter_code` varchar(99) DEFAULT NULL COMMENT 'Chapter 코드 REFERENCE: UNRESOLVED. 공통코드 Group 또는 Master Repository 연결을 Metadata에서 확정해야 한다.',
    MODIFY COLUMN `section_code` varchar(99) DEFAULT NULL COMMENT 'Section 코드 REFERENCE: UNRESOLVED. 공통코드 Group 또는 Master Repository 연결을 Metadata에서 확정해야 한다.',
    MODIFY COLUMN `business_code` varchar(99) NOT NULL COMMENT '업무분류 코드 REFERENCE: UNRESOLVED. 공통코드 Group 또는 Master Repository 연결을 Metadata에서 확정해야 한다.',
    MODIFY COLUMN `domain_code` varchar(99) NOT NULL COMMENT '도메인 코드 REFERENCE: UNRESOLVED. 공통코드 Group 또는 Master Repository 연결을 Metadata에서 확정해야 한다.',
    MODIFY COLUMN `data_type_code` varchar(99) NOT NULL COMMENT '자료구분 코드 REFERENCE: te_common.cm_common_code의 group_code=CM_DATA_TYPE. Generator, Engine 및 AI는 해당 Group의 code를 해석한다.',
    MODIFY COLUMN `data_code` varchar(99) NOT NULL COMMENT '자료 코드 REFERENCE: UNRESOLVED. 공통코드 Group 또는 Master Repository 연결을 Metadata에서 확정해야 한다.',
    MODIFY COLUMN `sort_no` int(11) NOT NULL DEFAULT 0 COMMENT '표시 및 처리 순서를 제어하는 정렬 순번.',
    MODIFY COLUMN `status_code` varchar(99) NOT NULL DEFAULT 'ACTIVE' COMMENT 'Status Code 코드. Repository Metadata가 정의한 코드 체계로 관리한다. REFERENCE: te_common.cm_common_code의 group_code=STATUS_CODE. Generator, Engine 및 AI는 해당 Group의 code를 해석한다.',
    MODIFY COLUMN `created_dt` datetime NOT NULL DEFAULT current_timestamp() COMMENT 'Object 최초 생성 일시.',
    MODIFY COLUMN `created_by` varchar(99) NOT NULL DEFAULT 'SYSTEM' COMMENT 'Object를 최초 생성한 사용자 또는 실행 주체 식별자.',
    MODIFY COLUMN `updated_dt` datetime NOT NULL DEFAULT current_timestamp() ON UPDATE current_timestamp() COMMENT 'Object 최종 수정 일시.',
    MODIFY COLUMN `updated_by` varchar(99) NOT NULL DEFAULT 'SYSTEM' COMMENT 'Object를 최종 수정한 사용자 또는 실행 주체 식별자.',
    MODIFY COLUMN `client_ip` varchar(99) DEFAULT NULL COMMENT 'Object 변경 요청이 발생한 Client IP 주소.',
    MODIFY COLUMN `deleted_by` varchar(99) DEFAULT NULL COMMENT 'Object를 논리 삭제한 사용자 또는 실행 주체 식별자.',
    MODIFY COLUMN `deleted_dt` datetime DEFAULT NULL COMMENT 'Object 논리 삭제 처리 일시.',
    MODIFY COLUMN `program_id` varchar(99) DEFAULT NULL COMMENT 'Object 생성·수정·삭제를 수행한 Program 식별자.',
    COMMENT = 'PURPOSE: Book·Chapter·Section 계층의 Repository Data Object를 관리한다. ROLE: COMMON 공식 Repository. SSOT: 해당 Object 정의와 관계의 단일 원천. ENGINE_GUIDE: Generator, Engine 및 AI는 이 테이블을 Repository First로 해석하며 값과 규칙의 Hardcoding을 금지한다.';

/* te_common.cm_role */
ALTER TABLE `te_common`.`cm_role`
    MODIFY COLUMN `role_id` varchar(99) NOT NULL COMMENT 'Role Id 식별자. cm_role Object와 관련 Object를 식별하거나 연결한다.',
    MODIFY COLUMN `role_code` varchar(99) NOT NULL COMMENT 'Role Code 코드. Repository Metadata가 정의한 코드 체계로 관리한다. REFERENCE: te_common.cm_common_code의 group_code=RL_ROLE. Generator, Engine 및 AI는 해당 Group의 code를 해석한다.',
    MODIFY COLUMN `role_name` varchar(150) NOT NULL COMMENT 'Role Name 명칭. 사람이 이해할 수 있는 표시 이름을 관리한다.',
    MODIFY COLUMN `created_dt` datetime NOT NULL DEFAULT current_timestamp() COMMENT 'Object 최초 생성 일시.',
    MODIFY COLUMN `created_by` varchar(99) NOT NULL DEFAULT 'SYSTEM' COMMENT 'Object를 최초 생성한 사용자 또는 실행 주체 식별자.',
    MODIFY COLUMN `updated_dt` datetime NOT NULL DEFAULT current_timestamp() ON UPDATE current_timestamp() COMMENT 'Object 최종 수정 일시.',
    MODIFY COLUMN `updated_by` varchar(99) NOT NULL DEFAULT 'SYSTEM' COMMENT 'Object를 최종 수정한 사용자 또는 실행 주체 식별자.',
    MODIFY COLUMN `client_ip` varchar(99) DEFAULT NULL COMMENT 'Object 변경 요청이 발생한 Client IP 주소.',
    MODIFY COLUMN `deleted_by` varchar(99) DEFAULT NULL COMMENT 'Object를 논리 삭제한 사용자 또는 실행 주체 식별자.',
    MODIFY COLUMN `deleted_dt` datetime DEFAULT NULL COMMENT 'Object 논리 삭제 처리 일시.',
    MODIFY COLUMN `program_id` varchar(99) DEFAULT NULL COMMENT 'Object 생성·수정·삭제를 수행한 Program 식별자.',
    MODIFY COLUMN `status_code` varchar(99) NOT NULL DEFAULT 'ACTIVE' COMMENT 'Status Code 코드. Repository Metadata가 정의한 코드 체계로 관리한다. REFERENCE: te_common.cm_common_code의 group_code=STATUS_CODE. Generator, Engine 및 AI는 해당 Group의 code를 해석한다.',
    COMMENT = 'PURPOSE: Framework 권한 Role의 코드, 명칭 및 상태를 관리한다. ROLE: COMMON 공식 Repository. SSOT: 해당 Object 정의와 관계의 단일 원천. ENGINE_GUIDE: Generator, Engine 및 AI는 이 테이블을 Repository First로 해석하며 값과 규칙의 Hardcoding을 금지한다.';

/* te_common.cm_role_rule */
ALTER TABLE `te_common`.`cm_role_rule`
    COMMENT = 'PURPOSE: Role과 Rule의 N:N 관계를 해소하는 최소 매핑을 관리한다. ROLE: COMMON 공식 Repository. SSOT: 해당 Object 정의와 관계의 단일 원천. ENGINE_GUIDE: Generator, Engine 및 AI는 이 테이블을 Repository First로 해석하며 값과 규칙의 Hardcoding을 금지한다.';

/* te_common.cm_sequence */
ALTER TABLE `te_common`.`cm_sequence`
    MODIFY COLUMN `sequence_code` varchar(99) NOT NULL COMMENT 'Sequence Code 코드. Repository Metadata가 정의한 코드 체계로 관리한다. REFERENCE: COMMON.cm_sequence_definition(sequence_code). 해당 Master Repository를 공식 연결 원천으로 사용한다.',
    MODIFY COLUMN `sequence_dt` datetime NOT NULL COMMENT 'Sequence Dt 일시. Object의 해당 Event 발생 시점을 관리한다.',
    MODIFY COLUMN `current_value` varchar(2000) NOT NULL DEFAULT '0' COMMENT 'Current Value 값. 해당 Object 속성의 실제 값을 관리한다.',
    MODIFY COLUMN `created_dt` datetime NOT NULL DEFAULT current_timestamp() COMMENT 'Object 최초 생성 일시.',
    MODIFY COLUMN `updated_dt` datetime NOT NULL DEFAULT current_timestamp() ON UPDATE current_timestamp() COMMENT 'Object 최종 수정 일시.',
    MODIFY COLUMN `created_by` varchar(99) NOT NULL DEFAULT 'SYSTEM' COMMENT 'Object를 최초 생성한 사용자 또는 실행 주체 식별자.',
    MODIFY COLUMN `updated_by` varchar(99) DEFAULT NULL COMMENT 'Object를 최종 수정한 사용자 또는 실행 주체 식별자.',
    MODIFY COLUMN `deleted_by` varchar(99) DEFAULT NULL COMMENT 'Object를 논리 삭제한 사용자 또는 실행 주체 식별자.',
    MODIFY COLUMN `deleted_dt` datetime DEFAULT NULL COMMENT 'Object 논리 삭제 처리 일시.',
    MODIFY COLUMN `client_ip` varchar(99) DEFAULT NULL COMMENT 'Object 변경 요청이 발생한 Client IP 주소.',
    MODIFY COLUMN `program_id` varchar(99) DEFAULT NULL COMMENT 'Object 생성·수정·삭제를 수행한 Program 식별자.',
    MODIFY COLUMN `status_code` varchar(99) NOT NULL DEFAULT 'ACTIVE' COMMENT 'Status Code 코드. Repository Metadata가 정의한 코드 체계로 관리한다. REFERENCE: te_common.cm_common_code의 group_code=STATUS_CODE. Generator, Engine 및 AI는 해당 Group의 code를 해석한다.',
    COMMENT = 'PURPOSE: 공통 Sequence의 코드·기준 일시별 현재 값을 관리한다. ROLE: COMMON 공식 Repository. SSOT: 해당 Object 정의와 관계의 단일 원천. ENGINE_GUIDE: Generator, Engine 및 AI는 이 테이블을 Repository First로 해석하며 값과 규칙의 Hardcoding을 금지한다.';

/* te_common.cm_sequence_definition */
ALTER TABLE `te_common`.`cm_sequence_definition`
    MODIFY COLUMN `sequence_code` varchar(99) NOT NULL COMMENT '시퀀스 코드 REFERENCE: COMMON.cm_sequence_definition(sequence_code). 해당 Master Repository를 공식 연결 원천으로 사용한다.',
    MODIFY COLUMN `function_code` varchar(99) NOT NULL COMMENT '기능 코드 REFERENCE: te_common.cm_common_code의 group_code=SPS_FUNCTION. Generator, Engine 및 AI는 해당 Group의 code를 해석한다.',
    MODIFY COLUMN `domain_code` varchar(99) NOT NULL COMMENT '도메인 코드 REFERENCE: UNRESOLVED. 공통코드 Group 또는 Master Repository 연결을 Metadata에서 확정해야 한다.',
    MODIFY COLUMN `policy_code` varchar(99) NOT NULL COMMENT '시퀀스 정책 코드 REFERENCE: COMMON.cm_sequence_policy(policy_code). 해당 Master Repository를 공식 연결 원천으로 사용한다.',
    MODIFY COLUMN `format_code` varchar(99) NOT NULL COMMENT '시퀀스 포맷 코드 REFERENCE: COMMON.cm_sequence_format(format_code). 해당 Master Repository를 공식 연결 원천으로 사용한다.',
    MODIFY COLUMN `prefix_code` varchar(99) DEFAULT NULL COMMENT 'Prefix 코드 REFERENCE: UNRESOLVED. 공통코드 Group 또는 Master Repository 연결을 Metadata에서 확정해야 한다.',
    MODIFY COLUMN `sort_no` int(11) NOT NULL DEFAULT 0 COMMENT '표시 및 처리 순서를 제어하는 정렬 순번.',
    MODIFY COLUMN `status_code` varchar(99) NOT NULL DEFAULT 'ACTIVE' COMMENT 'Status Code 코드. Repository Metadata가 정의한 코드 체계로 관리한다. REFERENCE: te_common.cm_common_code의 group_code=STATUS_CODE. Generator, Engine 및 AI는 해당 Group의 code를 해석한다.',
    MODIFY COLUMN `created_dt` datetime NOT NULL DEFAULT current_timestamp() COMMENT 'Object 최초 생성 일시.',
    MODIFY COLUMN `created_by` varchar(99) NOT NULL DEFAULT 'SYSTEM' COMMENT 'Object를 최초 생성한 사용자 또는 실행 주체 식별자.',
    MODIFY COLUMN `updated_dt` datetime NOT NULL DEFAULT current_timestamp() ON UPDATE current_timestamp() COMMENT 'Object 최종 수정 일시.',
    MODIFY COLUMN `updated_by` varchar(99) NOT NULL DEFAULT 'SYSTEM' COMMENT 'Object를 최종 수정한 사용자 또는 실행 주체 식별자.',
    MODIFY COLUMN `client_ip` varchar(99) DEFAULT NULL COMMENT 'Object 변경 요청이 발생한 Client IP 주소.',
    MODIFY COLUMN `deleted_by` varchar(99) DEFAULT NULL COMMENT 'Object를 논리 삭제한 사용자 또는 실행 주체 식별자.',
    MODIFY COLUMN `deleted_dt` datetime DEFAULT NULL COMMENT 'Object 논리 삭제 처리 일시.',
    MODIFY COLUMN `program_id` varchar(99) DEFAULT NULL COMMENT 'Object 생성·수정·삭제를 수행한 Program 식별자.',
    COMMENT = 'PURPOSE: Sequence의 기능·Domain·정책·포맷·Prefix 구성을 정의한다. ROLE: COMMON 공식 Repository. SSOT: 해당 Object 정의와 관계의 단일 원천. ENGINE_GUIDE: Generator, Engine 및 AI는 이 테이블을 Repository First로 해석하며 값과 규칙의 Hardcoding을 금지한다.';

/* te_common.cm_sequence_format */
ALTER TABLE `te_common`.`cm_sequence_format`
    MODIFY COLUMN `format_code` varchar(99) NOT NULL COMMENT '시퀀스 포맷 코드 REFERENCE: COMMON.cm_sequence_format(format_code). 해당 Master Repository를 공식 연결 원천으로 사용한다.',
    MODIFY COLUMN `created_dt` datetime NOT NULL DEFAULT current_timestamp() COMMENT 'Object 최초 생성 일시.',
    MODIFY COLUMN `updated_dt` datetime NOT NULL DEFAULT current_timestamp() ON UPDATE current_timestamp() COMMENT 'Object 최종 수정 일시.',
    MODIFY COLUMN `created_by` varchar(99) NOT NULL DEFAULT 'SYSTEM' COMMENT 'Object를 최초 생성한 사용자 또는 실행 주체 식별자.',
    MODIFY COLUMN `updated_by` varchar(99) DEFAULT NULL COMMENT 'Object를 최종 수정한 사용자 또는 실행 주체 식별자.',
    MODIFY COLUMN `deleted_by` varchar(99) DEFAULT NULL COMMENT 'Object를 논리 삭제한 사용자 또는 실행 주체 식별자.',
    MODIFY COLUMN `deleted_dt` datetime DEFAULT NULL COMMENT 'Object 논리 삭제 처리 일시.',
    MODIFY COLUMN `client_ip` varchar(99) DEFAULT NULL COMMENT 'Object 변경 요청이 발생한 Client IP 주소.',
    MODIFY COLUMN `program_id` varchar(99) DEFAULT NULL COMMENT 'Object 생성·수정·삭제를 수행한 Program 식별자.',
    MODIFY COLUMN `status_code` varchar(99) NOT NULL DEFAULT 'ACTIVE' COMMENT 'Status Code 코드. Repository Metadata가 정의한 코드 체계로 관리한다. REFERENCE: te_common.cm_common_code의 group_code=STATUS_CODE. Generator, Engine 및 AI는 해당 Group의 code를 해석한다.',
    COMMENT = 'PURPOSE: 식별자와 Sequence 출력 포맷의 공식 Master를 관리한다. ROLE: COMMON 공식 Repository. SSOT: 해당 Object 정의와 관계의 단일 원천. ENGINE_GUIDE: Generator, Engine 및 AI는 이 테이블을 Repository First로 해석하며 값과 규칙의 Hardcoding을 금지한다.';

/* te_common.cm_sequence_format_definition */
ALTER TABLE `te_common`.`cm_sequence_format_definition`
    MODIFY COLUMN `format_code` varchar(99) NOT NULL COMMENT '시퀀스 포맷 코드 REFERENCE: COMMON.cm_sequence_format(format_code). 해당 Master Repository를 공식 연결 원천으로 사용한다.',
    MODIFY COLUMN `sort_no` int(11) NOT NULL DEFAULT 0 COMMENT '표시 및 처리 순서를 제어하는 정렬 순번.',
    MODIFY COLUMN `status_code` varchar(99) NOT NULL DEFAULT 'ACTIVE' COMMENT 'Status Code 코드. Repository Metadata가 정의한 코드 체계로 관리한다. REFERENCE: te_common.cm_common_code의 group_code=STATUS_CODE. Generator, Engine 및 AI는 해당 Group의 code를 해석한다.',
    MODIFY COLUMN `created_dt` datetime NOT NULL DEFAULT current_timestamp() COMMENT 'Object 최초 생성 일시.',
    MODIFY COLUMN `created_by` varchar(99) NOT NULL DEFAULT 'SYSTEM' COMMENT 'Object를 최초 생성한 사용자 또는 실행 주체 식별자.',
    MODIFY COLUMN `updated_dt` datetime NOT NULL DEFAULT current_timestamp() ON UPDATE current_timestamp() COMMENT 'Object 최종 수정 일시.',
    MODIFY COLUMN `updated_by` varchar(99) NOT NULL DEFAULT 'SYSTEM' COMMENT 'Object를 최종 수정한 사용자 또는 실행 주체 식별자.',
    MODIFY COLUMN `client_ip` varchar(99) DEFAULT NULL COMMENT 'Object 변경 요청이 발생한 Client IP 주소.',
    MODIFY COLUMN `deleted_by` varchar(99) DEFAULT NULL COMMENT 'Object를 논리 삭제한 사용자 또는 실행 주체 식별자.',
    MODIFY COLUMN `deleted_dt` datetime DEFAULT NULL COMMENT 'Object 논리 삭제 처리 일시.',
    MODIFY COLUMN `program_id` varchar(99) DEFAULT NULL COMMENT 'Object 생성·수정·삭제를 수행한 Program 식별자.',
    COMMENT = 'PURPOSE: Sequence Format Pattern과 설명을 정의한다. ROLE: COMMON 공식 Repository. SSOT: 해당 Object 정의와 관계의 단일 원천. ENGINE_GUIDE: Generator, Engine 및 AI는 이 테이블을 Repository First로 해석하며 값과 규칙의 Hardcoding을 금지한다.';

/* te_common.cm_sequence_policy */
ALTER TABLE `te_common`.`cm_sequence_policy`
    MODIFY COLUMN `policy_code` varchar(99) NOT NULL COMMENT '시퀀스 초기화 정책 코드 REFERENCE: COMMON.cm_sequence_policy(policy_code). 해당 Master Repository를 공식 연결 원천으로 사용한다.',
    MODIFY COLUMN `created_dt` datetime NOT NULL DEFAULT current_timestamp() COMMENT 'Object 최초 생성 일시.',
    MODIFY COLUMN `updated_dt` datetime NOT NULL DEFAULT current_timestamp() ON UPDATE current_timestamp() COMMENT 'Object 최종 수정 일시.',
    MODIFY COLUMN `created_by` varchar(99) NOT NULL DEFAULT 'SYSTEM' COMMENT 'Object를 최초 생성한 사용자 또는 실행 주체 식별자.',
    MODIFY COLUMN `updated_by` varchar(99) DEFAULT NULL COMMENT 'Object를 최종 수정한 사용자 또는 실행 주체 식별자.',
    MODIFY COLUMN `deleted_by` varchar(99) DEFAULT NULL COMMENT 'Object를 논리 삭제한 사용자 또는 실행 주체 식별자.',
    MODIFY COLUMN `deleted_dt` datetime DEFAULT NULL COMMENT 'Object 논리 삭제 처리 일시.',
    MODIFY COLUMN `client_ip` varchar(99) DEFAULT NULL COMMENT 'Object 변경 요청이 발생한 Client IP 주소.',
    MODIFY COLUMN `program_id` varchar(99) DEFAULT NULL COMMENT 'Object 생성·수정·삭제를 수행한 Program 식별자.',
    MODIFY COLUMN `status_code` varchar(99) NOT NULL DEFAULT 'ACTIVE' COMMENT 'Status Code 코드. Repository Metadata가 정의한 코드 체계로 관리한다. REFERENCE: te_common.cm_common_code의 group_code=STATUS_CODE. Generator, Engine 및 AI는 해당 Group의 code를 해석한다.',
    COMMENT = 'PURPOSE: Sequence 초기화 주기와 날짜 형식 정책을 관리한다. ROLE: COMMON 공식 Repository. SSOT: 해당 Object 정의와 관계의 단일 원천. ENGINE_GUIDE: Generator, Engine 및 AI는 이 테이블을 Repository First로 해석하며 값과 규칙의 Hardcoding을 금지한다.';

/* te_common.cm_sequence_policy_definition */
ALTER TABLE `te_common`.`cm_sequence_policy_definition`
    MODIFY COLUMN `policy_code` varchar(99) NOT NULL COMMENT '시퀀스 정책 코드 REFERENCE: COMMON.cm_sequence_policy(policy_code). 해당 Master Repository를 공식 연결 원천으로 사용한다.',
    MODIFY COLUMN `sequence_date_rule_code` varchar(99) NOT NULL COMMENT '00000000/YYYY0000/YYYYMM00/YYYYMMDD REFERENCE: UNRESOLVED. 공통코드 Group 또는 Master Repository 연결을 Metadata에서 확정해야 한다.',
    MODIFY COLUMN `sort_no` int(11) NOT NULL DEFAULT 0 COMMENT '표시 및 처리 순서를 제어하는 정렬 순번.',
    MODIFY COLUMN `status_code` varchar(99) NOT NULL DEFAULT 'ACTIVE' COMMENT 'Status Code 코드. Repository Metadata가 정의한 코드 체계로 관리한다. REFERENCE: te_common.cm_common_code의 group_code=STATUS_CODE. Generator, Engine 및 AI는 해당 Group의 code를 해석한다.',
    MODIFY COLUMN `created_dt` datetime NOT NULL DEFAULT current_timestamp() COMMENT 'Object 최초 생성 일시.',
    MODIFY COLUMN `created_by` varchar(99) NOT NULL DEFAULT 'SYSTEM' COMMENT 'Object를 최초 생성한 사용자 또는 실행 주체 식별자.',
    MODIFY COLUMN `updated_dt` datetime NOT NULL DEFAULT current_timestamp() ON UPDATE current_timestamp() COMMENT 'Object 최종 수정 일시.',
    MODIFY COLUMN `updated_by` varchar(99) NOT NULL DEFAULT 'SYSTEM' COMMENT 'Object를 최종 수정한 사용자 또는 실행 주체 식별자.',
    MODIFY COLUMN `client_ip` varchar(99) DEFAULT NULL COMMENT 'Object 변경 요청이 발생한 Client IP 주소.',
    MODIFY COLUMN `deleted_by` varchar(99) DEFAULT NULL COMMENT 'Object를 논리 삭제한 사용자 또는 실행 주체 식별자.',
    MODIFY COLUMN `deleted_dt` datetime DEFAULT NULL COMMENT 'Object 논리 삭제 처리 일시.',
    MODIFY COLUMN `program_id` varchar(99) DEFAULT NULL COMMENT 'Object 생성·수정·삭제를 수행한 Program 식별자.',
    COMMENT = 'PURPOSE: Sequence 기준 일시 유형과 생성 규칙을 정의한다. ROLE: COMMON 공식 Repository. SSOT: 해당 Object 정의와 관계의 단일 원천. ENGINE_GUIDE: Generator, Engine 및 AI는 이 테이블을 Repository First로 해석하며 값과 규칙의 Hardcoding을 금지한다.';

/* te_common.cm_sequence_rule */
ALTER TABLE `te_common`.`cm_sequence_rule`
    MODIFY COLUMN `sequence_code` varchar(99) NOT NULL COMMENT '시퀀스 코드 REFERENCE: COMMON.cm_sequence_definition(sequence_code). 해당 Master Repository를 공식 연결 원천으로 사용한다.',
    MODIFY COLUMN `classification_code` varchar(99) DEFAULT NULL COMMENT '분류 코드 REFERENCE: COMMON.cm_data_classification(classification_code). 해당 Master Repository를 공식 연결 원천으로 사용한다.',
    MODIFY COLUMN `domain_code` varchar(99) DEFAULT NULL COMMENT '도메인 코드 REFERENCE: UNRESOLVED. 공통코드 Group 또는 Master Repository 연결을 Metadata에서 확정해야 한다.',
    MODIFY COLUMN `work_type_code` varchar(99) DEFAULT NULL COMMENT '업무유형 코드 REFERENCE: UNRESOLVED. 공통코드 Group 또는 Master Repository 연결을 Metadata에서 확정해야 한다.',
    MODIFY COLUMN `policy_code` varchar(99) NOT NULL COMMENT '초기화 정책 코드 REFERENCE: COMMON.cm_sequence_policy(policy_code). 해당 Master Repository를 공식 연결 원천으로 사용한다.',
    MODIFY COLUMN `format_code` varchar(99) NOT NULL COMMENT '포맷 코드 REFERENCE: COMMON.cm_sequence_format(format_code). 해당 Master Repository를 공식 연결 원천으로 사용한다.',
    MODIFY COLUMN `prefix_code` varchar(99) DEFAULT NULL COMMENT 'Prefix 코드 REFERENCE: UNRESOLVED. 공통코드 Group 또는 Master Repository 연결을 Metadata에서 확정해야 한다.',
    MODIFY COLUMN `created_dt` datetime NOT NULL DEFAULT current_timestamp() COMMENT 'Object 최초 생성 일시.',
    MODIFY COLUMN `updated_dt` datetime NOT NULL DEFAULT current_timestamp() ON UPDATE current_timestamp() COMMENT 'Object 최종 수정 일시.',
    MODIFY COLUMN `created_by` varchar(99) NOT NULL DEFAULT 'SYSTEM' COMMENT 'Object를 최초 생성한 사용자 또는 실행 주체 식별자.',
    MODIFY COLUMN `updated_by` varchar(99) DEFAULT NULL COMMENT 'Object를 최종 수정한 사용자 또는 실행 주체 식별자.',
    MODIFY COLUMN `deleted_by` varchar(99) DEFAULT NULL COMMENT 'Object를 논리 삭제한 사용자 또는 실행 주체 식별자.',
    MODIFY COLUMN `deleted_dt` datetime DEFAULT NULL COMMENT 'Object 논리 삭제 처리 일시.',
    MODIFY COLUMN `client_ip` varchar(99) DEFAULT NULL COMMENT 'Object 변경 요청이 발생한 Client IP 주소.',
    MODIFY COLUMN `program_id` varchar(99) DEFAULT NULL COMMENT 'Object 생성·수정·삭제를 수행한 Program 식별자.',
    MODIFY COLUMN `status_code` varchar(99) NOT NULL DEFAULT 'ACTIVE' COMMENT 'Status Code 코드. Repository Metadata가 정의한 코드 체계로 관리한다. REFERENCE: te_common.cm_common_code의 group_code=STATUS_CODE. Generator, Engine 및 AI는 해당 Group의 code를 해석한다.',
    COMMENT = 'PURPOSE: 분류·Domain·업무 유형별 Sequence 생성 규칙을 관리한다. ROLE: COMMON 공식 Repository. SSOT: 해당 Object 정의와 관계의 단일 원천. ENGINE_GUIDE: Generator, Engine 및 AI는 이 테이블을 Repository First로 해석하며 값과 규칙의 Hardcoding을 금지한다.';

/* te_common.cm_storage_policy */
ALTER TABLE `te_common`.`cm_storage_policy`
    MODIFY COLUMN `policy_id` varchar(99) NOT NULL COMMENT 'Policy Id 식별자. cm_storage_policy Object와 관련 Object를 식별하거나 연결한다.',
    MODIFY COLUMN `created_dt` datetime DEFAULT current_timestamp() COMMENT 'Object 최초 생성 일시.',
    MODIFY COLUMN `updated_dt` datetime DEFAULT current_timestamp() ON UPDATE current_timestamp() COMMENT 'Object 최종 수정 일시.',
    MODIFY COLUMN `created_by` varchar(99) NOT NULL DEFAULT 'SYSTEM' COMMENT 'Object를 최초 생성한 사용자 또는 실행 주체 식별자.',
    MODIFY COLUMN `updated_by` varchar(99) DEFAULT NULL COMMENT 'Object를 최종 수정한 사용자 또는 실행 주체 식별자.',
    MODIFY COLUMN `deleted_by` varchar(99) DEFAULT NULL COMMENT 'Object를 논리 삭제한 사용자 또는 실행 주체 식별자.',
    MODIFY COLUMN `deleted_dt` datetime DEFAULT NULL COMMENT 'Object 논리 삭제 처리 일시.',
    MODIFY COLUMN `change_story` varchar(2000) DEFAULT NULL COMMENT 'Change Story 값. cm_storage_policy Object의 해당 속성을 관리한다.',
    MODIFY COLUMN `client_ip` varchar(99) DEFAULT NULL COMMENT 'Object 변경 요청이 발생한 Client IP 주소.',
    MODIFY COLUMN `program_id` varchar(99) DEFAULT NULL COMMENT 'Object 생성·수정·삭제를 수행한 Program 식별자.',
    MODIFY COLUMN `status_code` varchar(99) NOT NULL DEFAULT 'ACTIVE' COMMENT 'Status Code 코드. Repository Metadata가 정의한 코드 체계로 관리한다. REFERENCE: te_common.cm_common_code의 group_code=STATUS_CODE. Generator, Engine 및 AI는 해당 Group의 code를 해석한다.',
    COMMENT = 'PURPOSE: 데이터 유형별 저장소와 보존 정책 연결을 관리한다. ROLE: COMMON 공식 Repository. SSOT: 해당 Object 정의와 관계의 단일 원천. ENGINE_GUIDE: Generator, Engine 및 AI는 이 테이블을 Repository First로 해석하며 값과 규칙의 Hardcoding을 금지한다.';

/* te_common.cm_storage_repository */
ALTER TABLE `te_common`.`cm_storage_repository`
    MODIFY COLUMN `created_dt` datetime DEFAULT current_timestamp() COMMENT 'Object 최초 생성 일시.',
    MODIFY COLUMN `updated_dt` datetime DEFAULT current_timestamp() ON UPDATE current_timestamp() COMMENT 'Object 최종 수정 일시.',
    MODIFY COLUMN `created_by` varchar(99) NOT NULL DEFAULT 'SYSTEM' COMMENT 'Object를 최초 생성한 사용자 또는 실행 주체 식별자.',
    MODIFY COLUMN `updated_by` varchar(99) DEFAULT NULL COMMENT 'Object를 최종 수정한 사용자 또는 실행 주체 식별자.',
    MODIFY COLUMN `deleted_by` varchar(99) DEFAULT NULL COMMENT 'Object를 논리 삭제한 사용자 또는 실행 주체 식별자.',
    MODIFY COLUMN `deleted_dt` datetime DEFAULT NULL COMMENT 'Object 논리 삭제 처리 일시.',
    MODIFY COLUMN `change_story` varchar(2000) DEFAULT NULL COMMENT 'Change Story 값. cm_storage_repository Object의 해당 속성을 관리한다.',
    MODIFY COLUMN `client_ip` varchar(99) DEFAULT NULL COMMENT 'Object 변경 요청이 발생한 Client IP 주소.',
    MODIFY COLUMN `program_id` varchar(99) DEFAULT NULL COMMENT 'Object 생성·수정·삭제를 수행한 Program 식별자.',
    MODIFY COLUMN `status_code` varchar(99) NOT NULL DEFAULT 'ACTIVE' COMMENT 'Status Code 코드. Repository Metadata가 정의한 코드 체계로 관리한다. REFERENCE: te_common.cm_common_code의 group_code=STATUS_CODE. Generator, Engine 및 AI는 해당 Group의 code를 해석한다.',
    COMMENT = 'PURPOSE: 물리·논리 Storage Repository의 연결 정보를 관리한다. ROLE: COMMON 공식 Repository. SSOT: 해당 Object 정의와 관계의 단일 원천. ENGINE_GUIDE: Generator, Engine 및 AI는 이 테이블을 Repository First로 해석하며 값과 규칙의 Hardcoding을 금지한다.';

/* te_common.cm_verified_sql_query */
ALTER TABLE `te_common`.`cm_verified_sql_query`
    MODIFY COLUMN `query_id` varchar(99) NOT NULL COMMENT 'Query Id 식별자. cm_verified_sql_query Object와 관련 Object를 식별하거나 연결한다.',
    MODIFY COLUMN `query_name` varchar(150) NOT NULL COMMENT 'Query Name 명칭. 사람이 이해할 수 있는 표시 이름을 관리한다.',
    MODIFY COLUMN `crud_type` varchar(99) NOT NULL COMMENT 'Crud Type 값. cm_verified_sql_query Object의 해당 속성을 관리한다.',
    MODIFY COLUMN `sql_text` text NOT NULL COMMENT 'Sql Text Text 값.',
    MODIFY COLUMN `verified_yn` char(1) NOT NULL DEFAULT 'N' COMMENT 'Verified Yn 여부. Y 또는 N 값으로 관리한다.',
    MODIFY COLUMN `certified_level_code` varchar(99) DEFAULT NULL COMMENT '검증 인증 수준 코드 REFERENCE: te_common.cm_common_code의 group_code=CM_LOG_LEVEL. Generator, Engine 및 AI는 해당 Group의 code를 해석한다.',
    MODIFY COLUMN `created_by` varchar(99) DEFAULT NULL COMMENT 'Object를 최초 생성한 사용자 또는 실행 주체 식별자.',
    MODIFY COLUMN `created_dt` datetime NOT NULL DEFAULT current_timestamp() COMMENT 'Object 최초 생성 일시.',
    MODIFY COLUMN `verified_by` varchar(99) DEFAULT NULL COMMENT 'Verified By 처리 주체 식별자.',
    MODIFY COLUMN `updated_dt` datetime DEFAULT NULL COMMENT 'Object 최종 수정 일시.',
    MODIFY COLUMN `deleted_dt` datetime DEFAULT NULL COMMENT 'Object 논리 삭제 처리 일시.',
    MODIFY COLUMN `status_code` varchar(99) NOT NULL DEFAULT 'ACTIVE' COMMENT 'Status Code 코드. Repository Metadata가 정의한 코드 체계로 관리한다. REFERENCE: te_common.cm_common_code의 group_code=STATUS_CODE. Generator, Engine 및 AI는 해당 Group의 code를 해석한다.',
    COMMENT = 'PURPOSE: 검증 완료 SQL Query와 실행 통제 정보를 관리한다. ROLE: COMMON 공식 Repository. SSOT: 해당 Object 정의와 관계의 단일 원천. ENGINE_GUIDE: Generator, Engine 및 AI는 이 테이블을 Repository First로 해석하며 값과 규칙의 Hardcoding을 금지한다.';

/* te_common.ev_evidence */
ALTER TABLE `te_common`.`ev_evidence`
    MODIFY COLUMN `evidence_code` varchar(99) NOT NULL COMMENT '근거 코드 REFERENCE: COMMON.ev_evidence(evidence_code). 해당 Master Repository를 공식 연결 원천으로 사용한다.',
    MODIFY COLUMN `evidence_level_code` varchar(99) NOT NULL COMMENT '근거수준 A/B/C/D REFERENCE: te_common.cm_common_code의 group_code=CM_LOG_LEVEL. Generator, Engine 및 AI는 해당 Group의 code를 해석한다.',
    MODIFY COLUMN `evidence_category_code` varchar(99) NOT NULL COMMENT '근거 분류 코드 REFERENCE: UNRESOLVED. 공통코드 Group 또는 Master Repository 연결을 Metadata에서 확정해야 한다.',
    MODIFY COLUMN `version_num` varchar(99) DEFAULT NULL COMMENT 'Object Version을 문자열로 표현한 번호.',
    MODIFY COLUMN `status_code` varchar(99) NOT NULL DEFAULT 'ACTIVE' COMMENT '상태 코드 REFERENCE: te_common.cm_common_code의 group_code=STATUS_CODE. Generator, Engine 및 AI는 해당 Group의 code를 해석한다.',
    MODIFY COLUMN `created_dt` datetime NOT NULL DEFAULT current_timestamp() COMMENT 'Object 최초 생성 일시.',
    MODIFY COLUMN `created_by` varchar(99) NOT NULL DEFAULT 'SYSTEM' COMMENT 'Object를 최초 생성한 사용자 또는 실행 주체 식별자.',
    MODIFY COLUMN `updated_dt` datetime NOT NULL DEFAULT current_timestamp() ON UPDATE current_timestamp() COMMENT 'Object 최종 수정 일시.',
    MODIFY COLUMN `updated_by` varchar(99) NOT NULL DEFAULT 'SYSTEM' COMMENT 'Object를 최종 수정한 사용자 또는 실행 주체 식별자.',
    MODIFY COLUMN `deleted_by` varchar(99) DEFAULT NULL COMMENT 'Object를 논리 삭제한 사용자 또는 실행 주체 식별자.',
    MODIFY COLUMN `deleted_dt` datetime DEFAULT NULL COMMENT 'Object 논리 삭제 처리 일시.',
    MODIFY COLUMN `program_id` varchar(99) DEFAULT NULL COMMENT 'Object 생성·수정·삭제를 수행한 Program 식별자.',
    MODIFY COLUMN `client_ip` varchar(99) DEFAULT NULL COMMENT 'Object 변경 요청이 발생한 Client IP 주소.',
    COMMENT = 'PURPOSE: Rule과 판단에서 사용하는 근거의 공식 정의를 관리한다. ROLE: COMMON 공식 Repository. SSOT: 해당 Object 정의와 관계의 단일 원천. ENGINE_GUIDE: Generator, Engine 및 AI는 이 테이블을 Repository First로 해석하며 값과 규칙의 Hardcoding을 금지한다.';

/* te_common.ev_evidence_reference */
ALTER TABLE `te_common`.`ev_evidence_reference`
    MODIFY COLUMN `reference_type_code` varchar(99) NOT NULL COMMENT '참조 유형 코드 REFERENCE: te_common.cm_common_code의 group_code=CHANGE_HISTORY_ACTION_TYPE. Generator, Engine 및 AI는 해당 Group의 code를 해석한다.',
    MODIFY COLUMN `created_dt` datetime NOT NULL DEFAULT current_timestamp() COMMENT 'Object 최초 생성 일시.',
    MODIFY COLUMN `created_by` varchar(99) NOT NULL DEFAULT 'SYSTEM' COMMENT 'Object를 최초 생성한 사용자 또는 실행 주체 식별자.',
    MODIFY COLUMN `updated_dt` datetime NOT NULL DEFAULT current_timestamp() ON UPDATE current_timestamp() COMMENT 'Object 최종 수정 일시.',
    MODIFY COLUMN `updated_by` varchar(99) NOT NULL DEFAULT 'SYSTEM' COMMENT 'Object를 최종 수정한 사용자 또는 실행 주체 식별자.',
    MODIFY COLUMN `deleted_by` varchar(99) DEFAULT NULL COMMENT 'Object를 논리 삭제한 사용자 또는 실행 주체 식별자.',
    MODIFY COLUMN `deleted_dt` datetime DEFAULT NULL COMMENT 'Object 논리 삭제 처리 일시.',
    MODIFY COLUMN `program_id` varchar(99) DEFAULT NULL COMMENT 'Object 생성·수정·삭제를 수행한 Program 식별자.',
    MODIFY COLUMN `client_ip` varchar(99) DEFAULT NULL COMMENT 'Object 변경 요청이 발생한 Client IP 주소.',
    MODIFY COLUMN `status_code` varchar(99) NOT NULL DEFAULT 'ACTIVE' COMMENT 'Status Code 코드. Repository Metadata가 정의한 코드 체계로 관리한다. REFERENCE: te_common.cm_common_code의 group_code=STATUS_CODE. Generator, Engine 및 AI는 해당 Group의 code를 해석한다.',
    COMMENT = 'PURPOSE: 근거가 참조하는 문서·논문·URL 출처를 관리한다. ROLE: COMMON 공식 Repository. SSOT: 해당 Object 정의와 관계의 단일 원천. ENGINE_GUIDE: Generator, Engine 및 AI는 이 테이블을 Repository First로 해석하며 값과 규칙의 Hardcoding을 금지한다.';

/* te_common.ev_evidence_version */
ALTER TABLE `te_common`.`ev_evidence_version`
    MODIFY COLUMN `version_num` varchar(99) DEFAULT NULL COMMENT 'Object Version을 문자열로 표현한 번호.',
    MODIFY COLUMN `created_dt` datetime NOT NULL DEFAULT current_timestamp() COMMENT 'Object 최초 생성 일시.',
    MODIFY COLUMN `created_by` varchar(99) NOT NULL DEFAULT 'SYSTEM' COMMENT 'Object를 최초 생성한 사용자 또는 실행 주체 식별자.',
    MODIFY COLUMN `updated_dt` datetime NOT NULL DEFAULT current_timestamp() ON UPDATE current_timestamp() COMMENT 'Object 최종 수정 일시.',
    MODIFY COLUMN `updated_by` varchar(99) NOT NULL DEFAULT 'SYSTEM' COMMENT 'Object를 최종 수정한 사용자 또는 실행 주체 식별자.',
    MODIFY COLUMN `deleted_by` varchar(99) DEFAULT NULL COMMENT 'Object를 논리 삭제한 사용자 또는 실행 주체 식별자.',
    MODIFY COLUMN `deleted_dt` datetime DEFAULT NULL COMMENT 'Object 논리 삭제 처리 일시.',
    MODIFY COLUMN `program_id` varchar(99) DEFAULT NULL COMMENT 'Object 생성·수정·삭제를 수행한 Program 식별자.',
    MODIFY COLUMN `client_ip` varchar(99) DEFAULT NULL COMMENT 'Object 변경 요청이 발생한 Client IP 주소.',
    MODIFY COLUMN `status_code` varchar(99) NOT NULL DEFAULT 'ACTIVE' COMMENT 'Status Code 코드. Repository Metadata가 정의한 코드 체계로 관리한다. REFERENCE: te_common.cm_common_code의 group_code=STATUS_CODE. Generator, Engine 및 AI는 해당 Group의 code를 해석한다.',
    COMMENT = 'PURPOSE: 근거의 적용 기간과 Version 변경 이력을 관리한다. ROLE: COMMON 공식 Repository. SSOT: 해당 Object 정의와 관계의 단일 원천. ENGINE_GUIDE: Generator, Engine 및 AI는 이 테이블을 Repository First로 해석하며 값과 규칙의 Hardcoding을 금지한다.';

/* te_common.health_report */
ALTER TABLE `te_common`.`health_report`
    MODIFY COLUMN `health_report_id` varchar(99) NOT NULL COMMENT 'Health Report Id 식별자. health_report Object와 관련 Object를 식별하거나 연결한다.',
    MODIFY COLUMN `patient_id` varchar(99) NOT NULL COMMENT 'Patient Id 식별자. health_report Object와 관련 Object를 식별하거나 연결한다.',
    MODIFY COLUMN `report_title` varchar(500) NOT NULL COMMENT 'Report Title 값. health_report Object의 해당 속성을 관리한다.',
    MODIFY COLUMN `report_content` text DEFAULT NULL COMMENT 'Report Content 값. health_report Object의 해당 속성을 관리한다.',
    MODIFY COLUMN `created_dt` datetime NOT NULL DEFAULT current_timestamp() COMMENT 'Object 최초 생성 일시.',
    MODIFY COLUMN `updated_dt` datetime DEFAULT NULL COMMENT 'Object 최종 수정 일시.',
    MODIFY COLUMN `created_by` varchar(99) NOT NULL DEFAULT 'SYSTEM' COMMENT 'Object를 최초 생성한 사용자 또는 실행 주체 식별자.',
    MODIFY COLUMN `updated_by` varchar(99) DEFAULT NULL COMMENT 'Object를 최종 수정한 사용자 또는 실행 주체 식별자.',
    MODIFY COLUMN `deleted_by` varchar(99) DEFAULT NULL COMMENT 'Object를 논리 삭제한 사용자 또는 실행 주체 식별자.',
    MODIFY COLUMN `deleted_dt` datetime DEFAULT NULL COMMENT 'Object 논리 삭제 처리 일시.',
    MODIFY COLUMN `change_story` varchar(2000) DEFAULT NULL COMMENT 'Change Story 값. health_report Object의 해당 속성을 관리한다.',
    MODIFY COLUMN `client_ip` varchar(99) DEFAULT NULL COMMENT 'Object 변경 요청이 발생한 Client IP 주소.',
    MODIFY COLUMN `program_id` varchar(99) DEFAULT NULL COMMENT 'Object 생성·수정·삭제를 수행한 Program 식별자.',
    MODIFY COLUMN `status_code` varchar(99) NOT NULL DEFAULT 'ACTIVE' COMMENT 'Status Code 코드. Repository Metadata가 정의한 코드 체계로 관리한다. REFERENCE: te_common.cm_common_code의 group_code=STATUS_CODE. Generator, Engine 및 AI는 해당 Group의 code를 해석한다.',
    COMMENT = 'PURPOSE: 회원 건강 Report의 생성 결과와 주요 건강 지표를 관리한다. ROLE: COMMON 공식 Repository. SSOT: 해당 Object 정의와 관계의 단일 원천. ENGINE_GUIDE: Generator, Engine 및 AI는 이 테이블을 Repository First로 해석하며 값과 규칙의 Hardcoding을 금지한다.';

/* te_common.md_object */
ALTER TABLE `te_common`.`md_object`
    MODIFY COLUMN `md_object_id` varchar(99) NOT NULL COMMENT 'Md Object Id 식별자. md_object Object와 관련 Object를 식별하거나 연결한다.',
    MODIFY COLUMN `object_type_group_code` varchar(99) NOT NULL DEFAULT 'OBJECT_TYPE' COMMENT 'Object Type Group Code 코드. Repository Metadata가 정의한 코드 체계로 관리한다. REFERENCE: UNRESOLVED. 공통코드 Group 또는 Master Repository 연결을 Metadata에서 확정해야 한다.',
    MODIFY COLUMN `object_type_code` varchar(99) NOT NULL COMMENT 'Object Type Code 코드. Repository Metadata가 정의한 코드 체계로 관리한다. REFERENCE: te_common.cm_common_code의 group_code=OBJECT_TYPE. Generator, Engine 및 AI는 해당 Group의 code를 해석한다.',
    MODIFY COLUMN `object_code` varchar(99) NOT NULL COMMENT 'Object Code 코드. Repository Metadata가 정의한 코드 체계로 관리한다. REFERENCE: STORY_PLATFORM.sp_object(object_code). 해당 Master Repository를 공식 연결 원천으로 사용한다.',
    MODIFY COLUMN `object_name` varchar(150) NOT NULL COMMENT 'Object Name 명칭. 사람이 이해할 수 있는 표시 이름을 관리한다.',
    MODIFY COLUMN `description` varchar(2000) DEFAULT NULL COMMENT 'Description 값. md_object Object의 해당 속성을 관리한다.',
    MODIFY COLUMN `attribute_json` longtext CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT 'Attribute Json 구조화 JSON. Generator, Engine 및 AI가 해석하는 확장 Metadata를 관리한다.' CHECK (json_valid(`attribute_json`)),
    MODIFY COLUMN `sort_no` int(11) NOT NULL DEFAULT 0 COMMENT '표시 및 처리 순서를 제어하는 정렬 순번.',
    MODIFY COLUMN `status_code` varchar(99) NOT NULL DEFAULT 'ACTIVE' COMMENT 'Status Code 코드. Repository Metadata가 정의한 코드 체계로 관리한다. REFERENCE: te_common.cm_common_code의 group_code=STATUS_CODE. Generator, Engine 및 AI는 해당 Group의 code를 해석한다.',
    MODIFY COLUMN `created_dt` datetime NOT NULL DEFAULT current_timestamp() COMMENT 'Object 최초 생성 일시.',
    MODIFY COLUMN `created_by` varchar(99) NOT NULL DEFAULT 'SYSTEM' COMMENT 'Object를 최초 생성한 사용자 또는 실행 주체 식별자.',
    MODIFY COLUMN `updated_dt` datetime NOT NULL DEFAULT current_timestamp() ON UPDATE current_timestamp() COMMENT 'Object 최종 수정 일시.',
    MODIFY COLUMN `updated_by` varchar(99) NOT NULL DEFAULT 'SYSTEM' COMMENT 'Object를 최종 수정한 사용자 또는 실행 주체 식별자.',
    MODIFY COLUMN `deleted_by` varchar(99) DEFAULT NULL COMMENT 'Object를 논리 삭제한 사용자 또는 실행 주체 식별자.',
    MODIFY COLUMN `deleted_dt` datetime DEFAULT NULL COMMENT 'Object 논리 삭제 처리 일시.',
    MODIFY COLUMN `client_ip` varchar(99) DEFAULT NULL COMMENT 'Object 변경 요청이 발생한 Client IP 주소.',
    MODIFY COLUMN `program_id` varchar(99) DEFAULT NULL COMMENT 'Object 생성·수정·삭제를 수행한 Program 식별자.',
    COMMENT = 'PURPOSE: Metadata Object의 유형, 코드, 명칭 및 구조화 정의를 관리한다. ROLE: COMMON 공식 Repository. SSOT: 해당 Object 정의와 관계의 단일 원천. ENGINE_GUIDE: Generator, Engine 및 AI는 이 테이블을 Repository First로 해석하며 값과 규칙의 Hardcoding을 금지한다.';

/* te_common.md_relation */
ALTER TABLE `te_common`.`md_relation`
    MODIFY COLUMN `md_relation_id` varchar(99) NOT NULL COMMENT 'Md Relation Id 식별자. md_relation Object와 관련 Object를 식별하거나 연결한다.',
    MODIFY COLUMN `source_md_object_id` varchar(99) NOT NULL COMMENT 'Source Md Object Id 식별자. md_relation Object와 관련 Object를 식별하거나 연결한다.',
    MODIFY COLUMN `target_md_object_id` varchar(99) NOT NULL COMMENT 'Target Md Object Id 식별자. md_relation Object와 관련 Object를 식별하거나 연결한다.',
    MODIFY COLUMN `relation_type_code` varchar(99) NOT NULL COMMENT 'Relation Type Code 코드. Repository Metadata가 정의한 코드 체계로 관리한다. REFERENCE: UNRESOLVED. 공통코드 Group 또는 Master Repository 연결을 Metadata에서 확정해야 한다.',
    MODIFY COLUMN `direction_code` varchar(99) NOT NULL DEFAULT 'UNI' COMMENT 'Direction Code 코드. Repository Metadata가 정의한 코드 체계로 관리한다. REFERENCE: UNRESOLVED. 공통코드 Group 또는 Master Repository 연결을 Metadata에서 확정해야 한다.',
    MODIFY COLUMN `cardinality_code` varchar(99) NOT NULL DEFAULT 'N:N' COMMENT 'Cardinality Code 코드. Repository Metadata가 정의한 코드 체계로 관리한다. REFERENCE: UNRESOLVED. 공통코드 Group 또는 Master Repository 연결을 Metadata에서 확정해야 한다.',
    MODIFY COLUMN `description` varchar(2000) DEFAULT NULL COMMENT 'Description 값. md_relation Object의 해당 속성을 관리한다.',
    MODIFY COLUMN `sort_no` int(11) NOT NULL DEFAULT 0 COMMENT '표시 및 처리 순서를 제어하는 정렬 순번.',
    MODIFY COLUMN `status_code` varchar(99) NOT NULL DEFAULT 'ACTIVE' COMMENT 'Status Code 코드. Repository Metadata가 정의한 코드 체계로 관리한다. REFERENCE: te_common.cm_common_code의 group_code=STATUS_CODE. Generator, Engine 및 AI는 해당 Group의 code를 해석한다.',
    MODIFY COLUMN `created_dt` datetime NOT NULL DEFAULT current_timestamp() COMMENT 'Object 최초 생성 일시.',
    MODIFY COLUMN `created_by` varchar(99) NOT NULL DEFAULT 'SYSTEM' COMMENT 'Object를 최초 생성한 사용자 또는 실행 주체 식별자.',
    MODIFY COLUMN `updated_dt` datetime NOT NULL DEFAULT current_timestamp() ON UPDATE current_timestamp() COMMENT 'Object 최종 수정 일시.',
    MODIFY COLUMN `updated_by` varchar(99) NOT NULL DEFAULT 'SYSTEM' COMMENT 'Object를 최종 수정한 사용자 또는 실행 주체 식별자.',
    MODIFY COLUMN `deleted_by` varchar(99) DEFAULT NULL COMMENT 'Object를 논리 삭제한 사용자 또는 실행 주체 식별자.',
    MODIFY COLUMN `deleted_dt` datetime DEFAULT NULL COMMENT 'Object 논리 삭제 처리 일시.',
    MODIFY COLUMN `client_ip` varchar(99) DEFAULT NULL COMMENT 'Object 변경 요청이 발생한 Client IP 주소.',
    MODIFY COLUMN `program_id` varchar(99) DEFAULT NULL COMMENT 'Object 생성·수정·삭제를 수행한 Program 식별자.',
    COMMENT = 'PURPOSE: Metadata Object 사이의 방향·Cardinality·관계 유형을 관리한다. ROLE: COMMON 공식 Repository. SSOT: 해당 Object 정의와 관계의 단일 원천. ENGINE_GUIDE: Generator, Engine 및 AI는 이 테이블을 Repository First로 해석하며 값과 규칙의 Hardcoding을 금지한다.';

/* te_common.rl_rule */
ALTER TABLE `te_common`.`rl_rule`
    MODIFY COLUMN `rule_code` varchar(99) NOT NULL COMMENT '규칙 코드 REFERENCE: COMMON.rl_rule(rule_code). 해당 Master Repository를 공식 연결 원천으로 사용한다.',
    MODIFY COLUMN `rule_type_code` varchar(99) NOT NULL COMMENT '규칙 유형 코드 REFERENCE: te_common.cm_common_code의 group_code=CHANGE_HISTORY_ACTION_TYPE. Generator, Engine 및 AI는 해당 Group의 code를 해석한다.',
    MODIFY COLUMN `rule_group_code` varchar(99) DEFAULT NULL COMMENT '규칙 그룹 코드 REFERENCE: UNRESOLVED. 공통코드 Group 또는 Master Repository 연결을 Metadata에서 확정해야 한다.',
    MODIFY COLUMN `status_code` varchar(99) NOT NULL DEFAULT 'ACTIVE' COMMENT '상태 코드 REFERENCE: te_common.cm_common_code의 group_code=STATUS_CODE. Generator, Engine 및 AI는 해당 Group의 code를 해석한다.',
    MODIFY COLUMN `version_num` varchar(99) DEFAULT NULL COMMENT 'Object Version을 문자열로 표현한 번호.',
    MODIFY COLUMN `created_dt` datetime NOT NULL DEFAULT current_timestamp() COMMENT 'Object 최초 생성 일시.',
    MODIFY COLUMN `created_by` varchar(99) NOT NULL DEFAULT 'SYSTEM' COMMENT 'Object를 최초 생성한 사용자 또는 실행 주체 식별자.',
    MODIFY COLUMN `updated_dt` datetime NOT NULL DEFAULT current_timestamp() ON UPDATE current_timestamp() COMMENT 'Object 최종 수정 일시.',
    MODIFY COLUMN `updated_by` varchar(99) NOT NULL DEFAULT 'SYSTEM' COMMENT 'Object를 최종 수정한 사용자 또는 실행 주체 식별자.',
    MODIFY COLUMN `deleted_by` varchar(99) DEFAULT NULL COMMENT 'Object를 논리 삭제한 사용자 또는 실행 주체 식별자.',
    MODIFY COLUMN `deleted_dt` datetime DEFAULT NULL COMMENT 'Object 논리 삭제 처리 일시.',
    MODIFY COLUMN `program_id` varchar(99) DEFAULT NULL COMMENT 'Object 생성·수정·삭제를 수행한 Program 식별자.',
    MODIFY COLUMN `client_ip` varchar(99) DEFAULT NULL COMMENT 'Object 변경 요청이 발생한 Client IP 주소.',
    COMMENT = 'PURPOSE: 업무 Rule의 유형, 우선순위, Version 및 상태를 관리한다. ROLE: COMMON 공식 Repository. SSOT: 해당 Object 정의와 관계의 단일 원천. ENGINE_GUIDE: Generator, Engine 및 AI는 이 테이블을 Repository First로 해석하며 값과 규칙의 Hardcoding을 금지한다.';

/* te_common.rl_rule_action */
ALTER TABLE `te_common`.`rl_rule_action`
    MODIFY COLUMN `action_type_code` varchar(99) NOT NULL COMMENT '실행 유형 코드 REFERENCE: te_common.cm_common_code의 group_code=CHANGE_HISTORY_ACTION_TYPE. Generator, Engine 및 AI는 해당 Group의 code를 해석한다.',
    MODIFY COLUMN `created_dt` datetime NOT NULL DEFAULT current_timestamp() COMMENT 'Object 최초 생성 일시.',
    MODIFY COLUMN `created_by` varchar(99) NOT NULL DEFAULT 'SYSTEM' COMMENT 'Object를 최초 생성한 사용자 또는 실행 주체 식별자.',
    MODIFY COLUMN `updated_dt` datetime NOT NULL DEFAULT current_timestamp() ON UPDATE current_timestamp() COMMENT 'Object 최종 수정 일시.',
    MODIFY COLUMN `updated_by` varchar(99) NOT NULL DEFAULT 'SYSTEM' COMMENT 'Object를 최종 수정한 사용자 또는 실행 주체 식별자.',
    MODIFY COLUMN `deleted_by` varchar(99) DEFAULT NULL COMMENT 'Object를 논리 삭제한 사용자 또는 실행 주체 식별자.',
    MODIFY COLUMN `deleted_dt` datetime DEFAULT NULL COMMENT 'Object 논리 삭제 처리 일시.',
    MODIFY COLUMN `program_id` varchar(99) DEFAULT NULL COMMENT 'Object 생성·수정·삭제를 수행한 Program 식별자.',
    MODIFY COLUMN `client_ip` varchar(99) DEFAULT NULL COMMENT 'Object 변경 요청이 발생한 Client IP 주소.',
    MODIFY COLUMN `status_code` varchar(99) NOT NULL DEFAULT 'ACTIVE' COMMENT 'Status Code 코드. Repository Metadata가 정의한 코드 체계로 관리한다. REFERENCE: te_common.cm_common_code의 group_code=STATUS_CODE. Generator, Engine 및 AI는 해당 Group의 code를 해석한다.',
    COMMENT = 'PURPOSE: Rule 조건 충족 시 수행할 Action을 관리한다. ROLE: COMMON 공식 Repository. SSOT: 해당 Object 정의와 관계의 단일 원천. ENGINE_GUIDE: Generator, Engine 및 AI는 이 테이블을 Repository First로 해석하며 값과 규칙의 Hardcoding을 금지한다.';

/* te_common.rl_rule_condition */
ALTER TABLE `te_common`.`rl_rule_condition`
    MODIFY COLUMN `field_code` varchar(99) NOT NULL COMMENT '대상 필드 코드 REFERENCE: UNRESOLVED. 공통코드 Group 또는 Master Repository 연결을 Metadata에서 확정해야 한다.',
    MODIFY COLUMN `operator_code` varchar(99) NOT NULL COMMENT '연산자 코드 REFERENCE: UNRESOLVED. 공통코드 Group 또는 Master Repository 연결을 Metadata에서 확정해야 한다.',
    MODIFY COLUMN `logical_operator_code` varchar(99) DEFAULT NULL COMMENT '논리 연산자 코드 REFERENCE: UNRESOLVED. 공통코드 Group 또는 Master Repository 연결을 Metadata에서 확정해야 한다.',
    MODIFY COLUMN `created_dt` datetime NOT NULL DEFAULT current_timestamp() COMMENT 'Object 최초 생성 일시.',
    MODIFY COLUMN `created_by` varchar(99) NOT NULL DEFAULT 'SYSTEM' COMMENT 'Object를 최초 생성한 사용자 또는 실행 주체 식별자.',
    MODIFY COLUMN `updated_dt` datetime NOT NULL DEFAULT current_timestamp() ON UPDATE current_timestamp() COMMENT 'Object 최종 수정 일시.',
    MODIFY COLUMN `updated_by` varchar(99) NOT NULL DEFAULT 'SYSTEM' COMMENT 'Object를 최종 수정한 사용자 또는 실행 주체 식별자.',
    MODIFY COLUMN `deleted_by` varchar(99) DEFAULT NULL COMMENT 'Object를 논리 삭제한 사용자 또는 실행 주체 식별자.',
    MODIFY COLUMN `deleted_dt` datetime DEFAULT NULL COMMENT 'Object 논리 삭제 처리 일시.',
    MODIFY COLUMN `program_id` varchar(99) DEFAULT NULL COMMENT 'Object 생성·수정·삭제를 수행한 Program 식별자.',
    MODIFY COLUMN `client_ip` varchar(99) DEFAULT NULL COMMENT 'Object 변경 요청이 발생한 Client IP 주소.',
    MODIFY COLUMN `status_code` varchar(99) NOT NULL DEFAULT 'ACTIVE' COMMENT 'Status Code 코드. Repository Metadata가 정의한 코드 체계로 관리한다. REFERENCE: te_common.cm_common_code의 group_code=STATUS_CODE. Generator, Engine 및 AI는 해당 Group의 code를 해석한다.',
    COMMENT = 'PURPOSE: Rule 평가 Field, Operator 및 조건 값을 관리한다. ROLE: COMMON 공식 Repository. SSOT: 해당 Object 정의와 관계의 단일 원천. ENGINE_GUIDE: Generator, Engine 및 AI는 이 테이블을 Repository First로 해석하며 값과 규칙의 Hardcoding을 금지한다.';

/* te_common.rl_rule_evidence */
ALTER TABLE `te_common`.`rl_rule_evidence`
    MODIFY COLUMN `created_dt` datetime NOT NULL DEFAULT current_timestamp() COMMENT 'Object 최초 생성 일시.',
    MODIFY COLUMN `created_by` varchar(99) NOT NULL DEFAULT 'SYSTEM' COMMENT 'Object를 최초 생성한 사용자 또는 실행 주체 식별자.',
    MODIFY COLUMN `updated_dt` datetime NOT NULL DEFAULT current_timestamp() ON UPDATE current_timestamp() COMMENT 'Object 최종 수정 일시.',
    MODIFY COLUMN `updated_by` varchar(99) NOT NULL DEFAULT 'SYSTEM' COMMENT 'Object를 최종 수정한 사용자 또는 실행 주체 식별자.',
    MODIFY COLUMN `deleted_by` varchar(99) DEFAULT NULL COMMENT 'Object를 논리 삭제한 사용자 또는 실행 주체 식별자.',
    MODIFY COLUMN `deleted_dt` datetime DEFAULT NULL COMMENT 'Object 논리 삭제 처리 일시.',
    MODIFY COLUMN `program_id` varchar(99) DEFAULT NULL COMMENT 'Object 생성·수정·삭제를 수행한 Program 식별자.',
    MODIFY COLUMN `client_ip` varchar(99) DEFAULT NULL COMMENT 'Object 변경 요청이 발생한 Client IP 주소.',
    MODIFY COLUMN `status_code` varchar(99) NOT NULL DEFAULT 'ACTIVE' COMMENT 'Status Code 코드. Repository Metadata가 정의한 코드 체계로 관리한다. REFERENCE: te_common.cm_common_code의 group_code=STATUS_CODE. Generator, Engine 및 AI는 해당 Group의 code를 해석한다.',
    COMMENT = 'PURPOSE: Rule과 Evidence 사이의 근거 연결을 관리한다. ROLE: COMMON 공식 Repository. SSOT: 해당 Object 정의와 관계의 단일 원천. ENGINE_GUIDE: Generator, Engine 및 AI는 이 테이블을 Repository First로 해석하며 값과 규칙의 Hardcoding을 금지한다.';

/* te_common.sp_policy_rule_candidate */
ALTER TABLE `te_common`.`sp_policy_rule_candidate`
    MODIFY COLUMN `rule_candidate_id` varchar(99) NOT NULL COMMENT 'Rule Candidate Id 식별자. sp_policy_rule_candidate Object와 관련 Object를 식별하거나 연결한다.',
    MODIFY COLUMN `policy_id` varchar(99) DEFAULT NULL COMMENT 'Policy Id 식별자. sp_policy_rule_candidate Object와 관련 Object를 식별하거나 연결한다.',
    MODIFY COLUMN `source_document_name` varchar(150) DEFAULT NULL COMMENT 'Source Document Name 명칭. 사람이 이해할 수 있는 표시 이름을 관리한다.',
    MODIFY COLUMN `source_page_no` int(11) DEFAULT NULL COMMENT 'Source Page No 순번. 정렬 또는 처리 순서를 정수로 관리한다.',
    MODIFY COLUMN `source_sentence_text` text NOT NULL COMMENT 'Source Sentence Text Text 값.',
    MODIFY COLUMN `matched_keyword_text` text DEFAULT NULL COMMENT 'Matched Keyword Text Text 값.',
    MODIFY COLUMN `rule_candidate_category_code` varchar(99) DEFAULT NULL COMMENT 'Rule Candidate Category Code 코드. Repository Metadata가 정의한 코드 체계로 관리한다. REFERENCE: UNRESOLVED. 공통코드 Group 또는 Master Repository 연결을 Metadata에서 확정해야 한다.',
    MODIFY COLUMN `confidence_score` decimal(10,4) DEFAULT 0.0000 COMMENT 'Confidence Score 점수. 평가 또는 판단의 수치 결과를 관리한다.',
    MODIFY COLUMN `confirm_yn` char(1) NOT NULL DEFAULT 'N' COMMENT 'Confirm Yn 여부. Y 또는 N 값으로 관리한다.',
    MODIFY COLUMN `use_yn` char(1) NOT NULL DEFAULT 'Y' COMMENT 'Use Yn 여부. Y 또는 N 값으로 관리한다.',
    MODIFY COLUMN `created_by` varchar(99) NOT NULL DEFAULT 'SYSTEM' COMMENT 'Object를 최초 생성한 사용자 또는 실행 주체 식별자.',
    MODIFY COLUMN `created_dt` datetime NOT NULL DEFAULT current_timestamp() COMMENT 'Object 최초 생성 일시.',
    MODIFY COLUMN `updated_by` varchar(99) DEFAULT NULL COMMENT 'Object를 최종 수정한 사용자 또는 실행 주체 식별자.',
    MODIFY COLUMN `updated_dt` datetime DEFAULT NULL COMMENT 'Object 최종 수정 일시.',
    MODIFY COLUMN `deleted_yn` char(1) NOT NULL DEFAULT 'N' COMMENT 'Deleted Yn 여부. Y 또는 N 값으로 관리한다.',
    MODIFY COLUMN `deleted_by` varchar(99) DEFAULT NULL COMMENT 'Object를 논리 삭제한 사용자 또는 실행 주체 식별자.',
    MODIFY COLUMN `deleted_dt` datetime DEFAULT NULL COMMENT 'Object 논리 삭제 처리 일시.',
    MODIFY COLUMN `change_reason` varchar(2000) DEFAULT NULL COMMENT 'Change Reason 값. sp_policy_rule_candidate Object의 해당 속성을 관리한다.',
    MODIFY COLUMN `client_ip` varchar(99) DEFAULT NULL COMMENT 'Object 변경 요청이 발생한 Client IP 주소.',
    MODIFY COLUMN `program_id` varchar(99) DEFAULT NULL COMMENT 'Object 생성·수정·삭제를 수행한 Program 식별자.',
    COMMENT = 'PURPOSE: 정책 문서에서 추출된 Rule 후보와 신뢰도를 관리한다. ROLE: COMMON 공식 Repository. SSOT: 해당 Object 정의와 관계의 단일 원천. ENGINE_GUIDE: Generator, Engine 및 AI는 이 테이블을 Repository First로 해석하며 값과 규칙의 Hardcoding을 금지한다.';

/* te_common.sp_policy_rule_keyword */
ALTER TABLE `te_common`.`sp_policy_rule_keyword`
    MODIFY COLUMN `rule_keyword_id` varchar(99) NOT NULL COMMENT 'Rule Keyword Id 식별자. sp_policy_rule_keyword Object와 관련 Object를 식별하거나 연결한다.',
    MODIFY COLUMN `rule_keyword_text` text NOT NULL COMMENT 'Rule Keyword Text Text 값.',
    MODIFY COLUMN `rule_keyword_category_code` varchar(99) NOT NULL COMMENT 'Rule Keyword Category Code 코드. Repository Metadata가 정의한 코드 체계로 관리한다. REFERENCE: UNRESOLVED. 공통코드 Group 또는 Master Repository 연결을 Metadata에서 확정해야 한다.',
    MODIFY COLUMN `rule_keyword_description` varchar(2000) DEFAULT NULL COMMENT 'Rule Keyword Description 설명. Object의 목적, 의미 및 적용 범위를 관리한다.',
    MODIFY COLUMN `use_yn` char(1) NOT NULL DEFAULT 'Y' COMMENT 'Use Yn 여부. Y 또는 N 값으로 관리한다.',
    MODIFY COLUMN `created_by` varchar(99) NOT NULL DEFAULT 'SYSTEM' COMMENT 'Object를 최초 생성한 사용자 또는 실행 주체 식별자.',
    MODIFY COLUMN `created_dt` datetime NOT NULL DEFAULT current_timestamp() COMMENT 'Object 최초 생성 일시.',
    MODIFY COLUMN `updated_by` varchar(99) DEFAULT NULL COMMENT 'Object를 최종 수정한 사용자 또는 실행 주체 식별자.',
    MODIFY COLUMN `updated_dt` datetime DEFAULT NULL COMMENT 'Object 최종 수정 일시.',
    MODIFY COLUMN `deleted_yn` char(1) NOT NULL DEFAULT 'N' COMMENT 'Deleted Yn 여부. Y 또는 N 값으로 관리한다.',
    MODIFY COLUMN `deleted_by` varchar(99) DEFAULT NULL COMMENT 'Object를 논리 삭제한 사용자 또는 실행 주체 식별자.',
    MODIFY COLUMN `deleted_dt` datetime DEFAULT NULL COMMENT 'Object 논리 삭제 처리 일시.',
    MODIFY COLUMN `change_reason` varchar(2000) DEFAULT NULL COMMENT 'Change Reason 값. sp_policy_rule_keyword Object의 해당 속성을 관리한다.',
    MODIFY COLUMN `client_ip` varchar(99) DEFAULT NULL COMMENT 'Object 변경 요청이 발생한 Client IP 주소.',
    MODIFY COLUMN `program_id` varchar(99) DEFAULT NULL COMMENT 'Object 생성·수정·삭제를 수행한 Program 식별자.',
    COMMENT = 'PURPOSE: 정책·Rule 탐색에 사용하는 Keyword와 Category를 관리한다. ROLE: COMMON 공식 Repository. SSOT: 해당 Object 정의와 관계의 단일 원천. ENGINE_GUIDE: Generator, Engine 및 AI는 이 테이블을 Repository First로 해석하며 값과 규칙의 Hardcoding을 금지한다.';

/* te_common.sql_guard_execution_log */
ALTER TABLE `te_common`.`sql_guard_execution_log`
    MODIFY COLUMN `execution_id` varchar(99) NOT NULL COMMENT 'Execution Id 식별자. sql_guard_execution_log Object와 관련 Object를 식별하거나 연결한다.',
    MODIFY COLUMN `user_id` varchar(99) NOT NULL COMMENT 'User Id 식별자. sql_guard_execution_log Object와 관련 Object를 식별하거나 연결한다.',
    MODIFY COLUMN `menu_code` varchar(99) NOT NULL COMMENT 'Menu Code 코드. Repository Metadata가 정의한 코드 체계로 관리한다. REFERENCE: COMMON.system_menu(menu_code). 해당 Master Repository를 공식 연결 원천으로 사용한다.',
    MODIFY COLUMN `button_code` varchar(99) NOT NULL COMMENT 'Button Code 코드. Repository Metadata가 정의한 코드 체계로 관리한다. REFERENCE: COMMON.system_menu_button(button_code). 해당 Master Repository를 공식 연결 원천으로 사용한다.',
    MODIFY COLUMN `query_id` varchar(99) NOT NULL COMMENT 'Query Id 식별자. sql_guard_execution_log Object와 관련 Object를 식별하거나 연결한다.',
    MODIFY COLUMN `crud_type` varchar(99) NOT NULL COMMENT 'Crud Type 값. sql_guard_execution_log Object의 해당 속성을 관리한다.',
    MODIFY COLUMN `success_yn` char(1) NOT NULL COMMENT 'Success Yn 여부. Y 또는 N 값으로 관리한다.',
    MODIFY COLUMN `row_count` int(11) DEFAULT NULL COMMENT 'Row Count 건수.',
    MODIFY COLUMN `error_message` text DEFAULT NULL COMMENT 'Error Message 값. sql_guard_execution_log Object의 해당 속성을 관리한다.',
    MODIFY COLUMN `executed_dt` datetime NOT NULL DEFAULT current_timestamp() COMMENT 'Executed Dt 일시. Object의 해당 Event 발생 시점을 관리한다.',
    MODIFY COLUMN `status_code` varchar(99) NOT NULL DEFAULT 'ACTIVE' COMMENT 'Status Code 코드. Repository Metadata가 정의한 코드 체계로 관리한다. REFERENCE: te_common.cm_common_code의 group_code=STATUS_CODE. Generator, Engine 및 AI는 해당 Group의 code를 해석한다.',
    COMMENT = 'PURPOSE: SQL Guard의 사용자·화면·Query별 실행 결과를 추적한다. ROLE: COMMON 공식 Repository. SSOT: 해당 이력과 실행 결과의 공식 원천. ENGINE_GUIDE: Generator, Engine 및 AI는 이 테이블을 Repository First로 해석하며 값과 규칙의 Hardcoding을 금지한다.';

/* te_common.sql_guard_verification_log */
ALTER TABLE `te_common`.`sql_guard_verification_log`
    MODIFY COLUMN `log_id` varchar(99) NOT NULL COMMENT 'Log Id 식별자. sql_guard_verification_log Object와 관련 Object를 식별하거나 연결한다.',
    MODIFY COLUMN `query_id` varchar(99) DEFAULT NULL COMMENT 'Query Id 식별자. sql_guard_verification_log Object와 관련 Object를 식별하거나 연결한다.',
    MODIFY COLUMN `check_step` varchar(99) NOT NULL COMMENT 'Check Step 값. sql_guard_verification_log Object의 해당 속성을 관리한다.',
    MODIFY COLUMN `pass_yn` char(1) NOT NULL COMMENT 'Pass Yn 여부. Y 또는 N 값으로 관리한다.',
    MODIFY COLUMN `message` text DEFAULT NULL COMMENT 'Message 값. sql_guard_verification_log Object의 해당 속성을 관리한다.',
    MODIFY COLUMN `created_dt` datetime NOT NULL DEFAULT current_timestamp() COMMENT 'Object 최초 생성 일시.',
    MODIFY COLUMN `created_by` varchar(99) NOT NULL DEFAULT 'SYSTEM' COMMENT 'Object를 최초 생성한 사용자 또는 실행 주체 식별자.',
    MODIFY COLUMN `updated_by` varchar(99) DEFAULT NULL COMMENT 'Object를 최종 수정한 사용자 또는 실행 주체 식별자.',
    MODIFY COLUMN `updated_dt` datetime DEFAULT NULL COMMENT 'Object 최종 수정 일시.',
    MODIFY COLUMN `deleted_by` varchar(99) DEFAULT NULL COMMENT 'Object를 논리 삭제한 사용자 또는 실행 주체 식별자.',
    MODIFY COLUMN `deleted_dt` datetime DEFAULT NULL COMMENT 'Object 논리 삭제 처리 일시.',
    MODIFY COLUMN `change_story` varchar(2000) DEFAULT NULL COMMENT 'Change Story 값. sql_guard_verification_log Object의 해당 속성을 관리한다.',
    MODIFY COLUMN `client_ip` varchar(99) DEFAULT NULL COMMENT 'Object 변경 요청이 발생한 Client IP 주소.',
    MODIFY COLUMN `program_id` varchar(99) DEFAULT NULL COMMENT 'Object 생성·수정·삭제를 수행한 Program 식별자.',
    MODIFY COLUMN `status_code` varchar(99) NOT NULL DEFAULT 'ACTIVE' COMMENT 'Status Code 코드. Repository Metadata가 정의한 코드 체계로 관리한다. REFERENCE: te_common.cm_common_code의 group_code=STATUS_CODE. Generator, Engine 및 AI는 해당 Group의 code를 해석한다.',
    COMMENT = 'PURPOSE: SQL Query 검증 단계별 판정과 오류를 추적한다. ROLE: COMMON 공식 Repository. SSOT: 해당 이력과 실행 결과의 공식 원천. ENGINE_GUIDE: Generator, Engine 및 AI는 이 테이블을 Repository First로 해석하며 값과 규칙의 Hardcoding을 금지한다.';

/* te_common.system_menu */
ALTER TABLE `te_common`.`system_menu`
    MODIFY COLUMN `menu_code` varchar(99) NOT NULL COMMENT 'Menu Code 코드. Repository Metadata가 정의한 코드 체계로 관리한다. REFERENCE: COMMON.system_menu(menu_code). 해당 Master Repository를 공식 연결 원천으로 사용한다.',
    MODIFY COLUMN `menu_name` varchar(150) NOT NULL COMMENT 'Menu Name 명칭. 사람이 이해할 수 있는 표시 이름을 관리한다.',
    MODIFY COLUMN `menu_url` varchar(2000) DEFAULT NULL COMMENT 'Menu Url URL 주소.',
    MODIFY COLUMN `menu_sort_no` int(11) NOT NULL DEFAULT 0 COMMENT 'Menu Sort No 순번. 정렬 또는 처리 순서를 정수로 관리한다.',
    MODIFY COLUMN `created_dt` datetime NOT NULL DEFAULT current_timestamp() COMMENT 'Object 최초 생성 일시.',
    MODIFY COLUMN `updated_dt` datetime DEFAULT NULL COMMENT 'Object 최종 수정 일시.',
    MODIFY COLUMN `created_by` varchar(99) NOT NULL DEFAULT 'SYSTEM' COMMENT 'Object를 최초 생성한 사용자 또는 실행 주체 식별자.',
    MODIFY COLUMN `updated_by` varchar(99) DEFAULT NULL COMMENT 'Object를 최종 수정한 사용자 또는 실행 주체 식별자.',
    MODIFY COLUMN `deleted_by` varchar(99) DEFAULT NULL COMMENT 'Object를 논리 삭제한 사용자 또는 실행 주체 식별자.',
    MODIFY COLUMN `deleted_dt` datetime DEFAULT NULL COMMENT 'Object 논리 삭제 처리 일시.',
    MODIFY COLUMN `client_ip` varchar(99) DEFAULT NULL COMMENT 'Object 변경 요청이 발생한 Client IP 주소.',
    MODIFY COLUMN `program_id` varchar(99) DEFAULT NULL COMMENT 'Object 생성·수정·삭제를 수행한 Program 식별자.',
    MODIFY COLUMN `status_code` varchar(99) NOT NULL DEFAULT 'ACTIVE' COMMENT 'Status Code 코드. Repository Metadata가 정의한 코드 체계로 관리한다. REFERENCE: te_common.cm_common_code의 group_code=STATUS_CODE. Generator, Engine 및 AI는 해당 Group의 code를 해석한다.',
    COMMENT = 'PURPOSE: System Menu의 코드, 명칭, URL 및 표시 순서를 관리한다. ROLE: COMMON 공식 Repository. SSOT: 해당 Object 정의와 관계의 단일 원천. ENGINE_GUIDE: Generator, Engine 및 AI는 이 테이블을 Repository First로 해석하며 값과 규칙의 Hardcoding을 금지한다.';

/* te_common.system_menu_button */
ALTER TABLE `te_common`.`system_menu_button`
    MODIFY COLUMN `button_code` varchar(99) NOT NULL COMMENT 'Button Code 코드. Repository Metadata가 정의한 코드 체계로 관리한다. REFERENCE: COMMON.system_menu_button(button_code). 해당 Master Repository를 공식 연결 원천으로 사용한다.',
    MODIFY COLUMN `menu_code` varchar(99) NOT NULL COMMENT 'Menu Code 코드. Repository Metadata가 정의한 코드 체계로 관리한다. REFERENCE: COMMON.system_menu(menu_code). 해당 Master Repository를 공식 연결 원천으로 사용한다.',
    MODIFY COLUMN `button_name` varchar(150) NOT NULL COMMENT 'Button Name 명칭. 사람이 이해할 수 있는 표시 이름을 관리한다.',
    MODIFY COLUMN `crud_type` varchar(99) NOT NULL COMMENT 'Crud Type 값. system_menu_button Object의 해당 속성을 관리한다.',
    MODIFY COLUMN `query_id` varchar(99) NOT NULL COMMENT 'Query Id 식별자. system_menu_button Object와 관련 Object를 식별하거나 연결한다.',
    MODIFY COLUMN `button_sort_no` int(11) NOT NULL DEFAULT 0 COMMENT 'Button Sort No 순번. 정렬 또는 처리 순서를 정수로 관리한다.',
    MODIFY COLUMN `created_dt` datetime NOT NULL DEFAULT current_timestamp() COMMENT 'Object 최초 생성 일시.',
    MODIFY COLUMN `updated_dt` datetime DEFAULT NULL COMMENT 'Object 최종 수정 일시.',
    MODIFY COLUMN `created_by` varchar(99) NOT NULL DEFAULT 'SYSTEM' COMMENT 'Object를 최초 생성한 사용자 또는 실행 주체 식별자.',
    MODIFY COLUMN `updated_by` varchar(99) DEFAULT NULL COMMENT 'Object를 최종 수정한 사용자 또는 실행 주체 식별자.',
    MODIFY COLUMN `deleted_by` varchar(99) DEFAULT NULL COMMENT 'Object를 논리 삭제한 사용자 또는 실행 주체 식별자.',
    MODIFY COLUMN `deleted_dt` datetime DEFAULT NULL COMMENT 'Object 논리 삭제 처리 일시.',
    MODIFY COLUMN `client_ip` varchar(99) DEFAULT NULL COMMENT 'Object 변경 요청이 발생한 Client IP 주소.',
    MODIFY COLUMN `program_id` varchar(99) DEFAULT NULL COMMENT 'Object 생성·수정·삭제를 수행한 Program 식별자.',
    MODIFY COLUMN `status_code` varchar(99) NOT NULL DEFAULT 'ACTIVE' COMMENT 'Status Code 코드. Repository Metadata가 정의한 코드 체계로 관리한다. REFERENCE: te_common.cm_common_code의 group_code=STATUS_CODE. Generator, Engine 및 AI는 해당 Group의 code를 해석한다.',
    COMMENT = 'PURPOSE: Menu 하위 Button과 CRUD·Verified Query 연결을 관리한다. ROLE: COMMON 공식 Repository. SSOT: 해당 Object 정의와 관계의 단일 원천. ENGINE_GUIDE: Generator, Engine 및 AI는 이 테이블을 Repository First로 해석하며 값과 규칙의 Hardcoding을 금지한다.';

/* te_common.system_menu_button_crud_permission */
ALTER TABLE `te_common`.`system_menu_button_crud_permission`
    MODIFY COLUMN `permission_id` varchar(99) NOT NULL COMMENT 'Permission Id 식별자. system_menu_button_crud_permission Object와 관련 Object를 식별하거나 연결한다.',
    MODIFY COLUMN `menu_code` varchar(99) NOT NULL COMMENT 'Menu Code 코드. Repository Metadata가 정의한 코드 체계로 관리한다. REFERENCE: COMMON.system_menu(menu_code). 해당 Master Repository를 공식 연결 원천으로 사용한다.',
    MODIFY COLUMN `button_code` varchar(99) NOT NULL COMMENT 'Button Code 코드. Repository Metadata가 정의한 코드 체계로 관리한다. REFERENCE: COMMON.system_menu_button(button_code). 해당 Master Repository를 공식 연결 원천으로 사용한다.',
    MODIFY COLUMN `user_role_code` varchar(99) NOT NULL COMMENT 'User Role Code 코드. Repository Metadata가 정의한 코드 체계로 관리한다. REFERENCE: te_common.cm_common_code의 group_code=RL_ROLE. Generator, Engine 및 AI는 해당 Group의 code를 해석한다.',
    MODIFY COLUMN `can_create_yn` char(1) NOT NULL DEFAULT 'N' COMMENT 'Can Create Yn 여부. Y 또는 N 값으로 관리한다.',
    MODIFY COLUMN `can_read_yn` char(1) NOT NULL DEFAULT 'N' COMMENT 'Can Read Yn 여부. Y 또는 N 값으로 관리한다.',
    MODIFY COLUMN `can_update_yn` char(1) NOT NULL DEFAULT 'N' COMMENT 'Can Update Yn 여부. Y 또는 N 값으로 관리한다.',
    MODIFY COLUMN `can_delete_yn` char(1) NOT NULL DEFAULT 'N' COMMENT 'Can Delete Yn 여부. Y 또는 N 값으로 관리한다.',
    MODIFY COLUMN `can_alter_yn` char(1) NOT NULL DEFAULT 'N' COMMENT 'Can Alter Yn 여부. Y 또는 N 값으로 관리한다.',
    MODIFY COLUMN `created_dt` datetime NOT NULL DEFAULT current_timestamp() COMMENT 'Object 최초 생성 일시.',
    MODIFY COLUMN `updated_dt` datetime DEFAULT NULL COMMENT 'Object 최종 수정 일시.',
    MODIFY COLUMN `created_by` varchar(99) NOT NULL DEFAULT 'SYSTEM' COMMENT 'Object를 최초 생성한 사용자 또는 실행 주체 식별자.',
    MODIFY COLUMN `updated_by` varchar(99) DEFAULT NULL COMMENT 'Object를 최종 수정한 사용자 또는 실행 주체 식별자.',
    MODIFY COLUMN `deleted_by` varchar(99) DEFAULT NULL COMMENT 'Object를 논리 삭제한 사용자 또는 실행 주체 식별자.',
    MODIFY COLUMN `deleted_dt` datetime DEFAULT NULL COMMENT 'Object 논리 삭제 처리 일시.',
    MODIFY COLUMN `client_ip` varchar(99) DEFAULT NULL COMMENT 'Object 변경 요청이 발생한 Client IP 주소.',
    MODIFY COLUMN `program_id` varchar(99) DEFAULT NULL COMMENT 'Object 생성·수정·삭제를 수행한 Program 식별자.',
    MODIFY COLUMN `status_code` varchar(99) NOT NULL DEFAULT 'ACTIVE' COMMENT 'Status Code 코드. Repository Metadata가 정의한 코드 체계로 관리한다. REFERENCE: te_common.cm_common_code의 group_code=STATUS_CODE. Generator, Engine 및 AI는 해당 Group의 code를 해석한다.',
    COMMENT = 'PURPOSE: 사용자 Role별 Menu·Button CRUD 권한을 관리한다. ROLE: COMMON 공식 Repository. SSOT: 해당 Object 정의와 관계의 단일 원천. ENGINE_GUIDE: Generator, Engine 및 AI는 이 테이블을 Repository First로 해석하며 값과 규칙의 Hardcoding을 금지한다.';

/* te_common.system_user */
ALTER TABLE `te_common`.`system_user`
    MODIFY COLUMN `user_id` varchar(99) NOT NULL COMMENT 'User Id 식별자. system_user Object와 관련 Object를 식별하거나 연결한다.',
    MODIFY COLUMN `user_login_id` varchar(99) NOT NULL COMMENT 'User Login Id 식별자. system_user Object와 관련 Object를 식별하거나 연결한다.',
    MODIFY COLUMN `user_name` varchar(150) NOT NULL COMMENT 'User Name 명칭. 사람이 이해할 수 있는 표시 이름을 관리한다.',
    MODIFY COLUMN `user_role_code` varchar(99) NOT NULL COMMENT 'User Role Code 코드. Repository Metadata가 정의한 코드 체계로 관리한다. REFERENCE: te_common.cm_common_code의 group_code=RL_ROLE. Generator, Engine 및 AI는 해당 Group의 code를 해석한다.',
    MODIFY COLUMN `created_dt` datetime NOT NULL DEFAULT current_timestamp() COMMENT 'Object 최초 생성 일시.',
    MODIFY COLUMN `updated_dt` datetime DEFAULT NULL COMMENT 'Object 최종 수정 일시.',
    MODIFY COLUMN `created_by` varchar(99) NOT NULL DEFAULT 'SYSTEM' COMMENT 'Object를 최초 생성한 사용자 또는 실행 주체 식별자.',
    MODIFY COLUMN `updated_by` varchar(99) DEFAULT NULL COMMENT 'Object를 최종 수정한 사용자 또는 실행 주체 식별자.',
    MODIFY COLUMN `deleted_by` varchar(99) DEFAULT NULL COMMENT 'Object를 논리 삭제한 사용자 또는 실행 주체 식별자.',
    MODIFY COLUMN `deleted_dt` datetime DEFAULT NULL COMMENT 'Object 논리 삭제 처리 일시.',
    MODIFY COLUMN `client_ip` varchar(99) DEFAULT NULL COMMENT 'Object 변경 요청이 발생한 Client IP 주소.',
    MODIFY COLUMN `program_id` varchar(99) DEFAULT NULL COMMENT 'Object 생성·수정·삭제를 수행한 Program 식별자.',
    MODIFY COLUMN `status_code` varchar(99) NOT NULL DEFAULT 'ACTIVE' COMMENT 'Status Code 코드. Repository Metadata가 정의한 코드 체계로 관리한다. REFERENCE: te_common.cm_common_code의 group_code=STATUS_CODE. Generator, Engine 및 AI는 해당 Group의 code를 해석한다.',
    COMMENT = 'PURPOSE: System 사용자 계정과 Role 및 운영 상태를 관리한다. ROLE: COMMON 공식 Repository. SSOT: 해당 Object 정의와 관계의 단일 원천. ENGINE_GUIDE: Generator, Engine 및 AI는 이 테이블을 Repository First로 해석하며 값과 규칙의 Hardcoding을 금지한다.';

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

/* Verification */
SELECT table_schema, COUNT(*) AS table_count,
       SUM(CASE WHEN table_comment = '' THEN 1 ELSE 0 END) AS empty_table_comment_count
FROM information_schema.tables
WHERE table_schema IN ('te_health_companion', 'te_story_platform', 'te_common')
  AND table_type = 'BASE TABLE'
  AND table_name NOT REGEXP '_backup_'
GROUP BY table_schema
ORDER BY table_schema;

SELECT table_schema, COUNT(*) AS column_count,
       SUM(CASE WHEN column_comment = '' THEN 1 ELSE 0 END) AS empty_column_comment_count
FROM information_schema.columns
WHERE table_schema IN ('te_health_companion', 'te_story_platform', 'te_common')
  AND table_name NOT REGEXP '_backup_'
GROUP BY table_schema
ORDER BY table_schema;

SELECT COUNT(*) AS unresolved_code_comment_count
FROM information_schema.columns
WHERE table_schema IN ('te_health_companion', 'te_story_platform', 'te_common')
  AND table_name NOT REGEXP '_backup_'
  AND column_name LIKE '%\_code'
  AND column_comment LIKE '%REFERENCE: UNRESOLVED%';

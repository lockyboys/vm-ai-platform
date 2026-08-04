-- SPS storage separation pilot backup
-- Source: te_story_platform.sp_impact_analysis_result
-- Backup date: 2026-08-05 KST
-- Row count: 5
-- Restore into a controlled schema only after review.

SET NAMES utf8mb4;

CREATE TABLE `sp_impact_analysis_result_backup_20260805_pilot` (
  `impact_analysis_id` varchar(99) NOT NULL COMMENT 'Impact Analysis Id 식별자. sp_impact_analysis_result Object와 관련 Object를 식별하거나 연결한다.',
  `change_target_text` text NOT NULL COMMENT 'Change Target Text Text 값.',
  `change_type_code` varchar(99) NOT NULL COMMENT 'Change Type Code 코드. Repository Metadata가 정의한 코드 체계로 관리한다. REFERENCE: UNRESOLVED. 공통코드 Group 또는 Master Repository 연결을 Metadata에서 확정해야 한다.',
  `affected_object_type_code` varchar(99) NOT NULL COMMENT 'Affected Object Type Code 코드. Repository Metadata가 정의한 코드 체계로 관리한다. REFERENCE: UNRESOLVED. 공통코드 Group 또는 Master Repository 연결을 Metadata에서 확정해야 한다.',
  `affected_object_name` varchar(150) NOT NULL COMMENT 'Affected Object Name 명칭. 사람이 이해할 수 있는 표시 이름을 관리한다.',
  `affected_file_path` varchar(2000) DEFAULT NULL COMMENT 'Affected File Path 값. sp_impact_analysis_result Object의 해당 속성을 관리한다.',
  `affected_line_no` int(11) DEFAULT NULL COMMENT 'Affected Line No 순번. 정렬 또는 처리 순서를 정수로 관리한다.',
  `affected_text` text DEFAULT NULL COMMENT 'Affected Text Text 값.',
  `risk_level_code` varchar(99) NOT NULL DEFAULT 'MEDIUM' COMMENT 'Risk Level Code 코드. Repository Metadata가 정의한 코드 체계로 관리한다. REFERENCE: te_common.cm_common_code의 group_code=HP_RISK_LEVEL. Generator, Engine 및 AI는 해당 Group의 code를 해석한다.',
  `analysis_note` text DEFAULT NULL COMMENT 'Analysis Note 값. sp_impact_analysis_result Object의 해당 속성을 관리한다.',
  `created_by` varchar(99) NOT NULL DEFAULT 'SYSTEM' COMMENT 'Object를 최초 생성한 사용자 또는 실행 주체 식별자.',
  `created_dt` datetime NOT NULL DEFAULT current_timestamp() COMMENT 'Object 최초 생성 일시.',
  `updated_by` varchar(99) DEFAULT NULL COMMENT 'Object를 최종 수정한 사용자 또는 실행 주체 식별자.',
  `updated_dt` datetime DEFAULT NULL COMMENT 'Object 최종 수정 일시.',
  `deleted_by` varchar(99) DEFAULT NULL COMMENT 'Object를 논리 삭제한 사용자 또는 실행 주체 식별자.',
  `deleted_dt` datetime DEFAULT NULL COMMENT 'Object 논리 삭제 처리 일시.',
  `client_ip` varchar(99) DEFAULT NULL COMMENT 'Object 변경 요청이 발생한 Client IP 주소.',
  `program_id` varchar(99) DEFAULT NULL COMMENT 'Object 생성·수정·삭제를 수행한 Program 식별자.',
  PRIMARY KEY (`impact_analysis_id`),
  KEY `idx_sp_impact_analysis_result_01` (`change_target_text`(768)),
  KEY `idx_sp_impact_analysis_result_02` (`affected_object_type_code`),
  KEY `idx_sp_impact_analysis_result_03` (`risk_level_code`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='PURPOSE: Repository 변경의 영향 Object와 Risk 분석 결과를 관리한다. ROLE: STORY_PLATFORM 공식 Repository. SSOT: 해당 Object 정의와 관계의 단일 원천. ENGINE_GUIDE: Generator, Engine 및 AI는 이 테이블을 Repository First로 해석하며 값과 규칙의 Hardcoding을 금지한다.'

INSERT INTO `sp_impact_analysis_result_backup_20260805_pilot` (`impact_analysis_id`, `change_target_text`, `change_type_code`, `affected_object_type_code`, `affected_object_name`, `affected_file_path`, `affected_line_no`, `affected_text`, `risk_level_code`, `analysis_note`, `created_by`, `created_dt`, `updated_by`, `updated_dt`, `deleted_by`, `deleted_dt`, `client_ip`, `program_id`) VALUES ('SP_RP_IMPACT_ANALYSIS_20260701_090144_00001', 'cm_common_code.code', 'COLUMN_RENAME', 'TABLE', 'cm_common_code', NULL, NULL, 'code -> common_code 후보', 'HIGH', '공통코드 핵심 컬럼. 직접 변경 금지. View 우선 적용.', 'SYSTEM', '2026-07-01T09:01:44', NULL, NULL, NULL, NULL, NULL, 'CM_CO_PROGRAM_20260701_090144_00031');
INSERT INTO `sp_impact_analysis_result_backup_20260805_pilot` (`impact_analysis_id`, `change_target_text`, `change_type_code`, `affected_object_type_code`, `affected_object_name`, `affected_file_path`, `affected_line_no`, `affected_text`, `risk_level_code`, `analysis_note`, `created_by`, `created_dt`, `updated_by`, `updated_dt`, `deleted_by`, `deleted_dt`, `client_ip`, `program_id`) VALUES ('SP_RP_IMPACT_ANALYSIS_20260701_090144_00002', 'cm_common_code.code_name', 'COLUMN_RENAME', 'TABLE', 'cm_common_code', NULL, NULL, 'code_name -> common_code_name 후보', 'HIGH', '공통코드 명칭 컬럼. View 우선 적용.', 'SYSTEM', '2026-07-01T09:01:44', NULL, NULL, NULL, NULL, NULL, 'CM_CO_PROGRAM_20260701_090144_00031');
INSERT INTO `sp_impact_analysis_result_backup_20260805_pilot` (`impact_analysis_id`, `change_target_text`, `change_type_code`, `affected_object_type_code`, `affected_object_name`, `affected_file_path`, `affected_line_no`, `affected_text`, `risk_level_code`, `analysis_note`, `created_by`, `created_dt`, `updated_by`, `updated_dt`, `deleted_by`, `deleted_dt`, `client_ip`, `program_id`) VALUES ('SP_RP_IMPACT_ANALYSIS_20260701_090144_00003', 'cm_common_code.code_description', 'COLUMN_RENAME', 'TABLE', 'cm_common_code', NULL, NULL, 'code_description -> common_code_description 후보', 'HIGH', '공통코드 설명 컬럼. View 우선 적용.', 'SYSTEM', '2026-07-01T09:01:44', NULL, NULL, NULL, NULL, NULL, 'CM_CO_PROGRAM_20260701_090144_00031');
INSERT INTO `sp_impact_analysis_result_backup_20260805_pilot` (`impact_analysis_id`, `change_target_text`, `change_type_code`, `affected_object_type_code`, `affected_object_name`, `affected_file_path`, `affected_line_no`, `affected_text`, `risk_level_code`, `analysis_note`, `created_by`, `created_dt`, `updated_by`, `updated_dt`, `deleted_by`, `deleted_dt`, `client_ip`, `program_id`) VALUES ('SP_RP_IMPACT_ANALYSIS_20260701_090144_00004', 'cm_common_code.group_code', 'COLUMN_RENAME', 'TABLE', 'cm_common_code', NULL, NULL, 'group_code -> common_code_group_code 후보', 'HIGH', 'PK/FK 영향 있음. 직접 변경 금지.', 'SYSTEM', '2026-07-01T09:01:44', NULL, NULL, NULL, NULL, NULL, 'CM_CO_PROGRAM_20260701_090144_00031');
INSERT INTO `sp_impact_analysis_result_backup_20260805_pilot` (`impact_analysis_id`, `change_target_text`, `change_type_code`, `affected_object_type_code`, `affected_object_name`, `affected_file_path`, `affected_line_no`, `affected_text`, `risk_level_code`, `analysis_note`, `created_by`, `created_dt`, `updated_by`, `updated_dt`, `deleted_by`, `deleted_dt`, `client_ip`, `program_id`) VALUES ('SP_RP_IMPACT_ANALYSIS_20260701_090144_00005', 'cm_common_code', 'VIEW_COMPATIBILITY', 'VIEW', 'vw_cm_common_code_standard', NULL, NULL, '표준 컬럼명 호환 View 생성 완료', 'LOW', '서비스/엔진/Generator는 View 기준 전환.', 'SYSTEM', '2026-07-01T09:01:44', NULL, NULL, NULL, NULL, NULL, 'CM_CO_PROGRAM_20260701_090144_00031');

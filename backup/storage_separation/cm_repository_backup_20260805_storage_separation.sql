-- SPS full table backup before one-row MongoDB storage separation pilot
-- Source: te_common.cm_repository
-- Backup date: 2026-08-05 KST
-- Row count: 3

SET NAMES utf8mb4;

CREATE TABLE `cm_repository_backup_20260805_storage_separation` (
  `repository_id` varchar(99) NOT NULL COMMENT 'Repository ID',
  `book_code` varchar(99) DEFAULT NULL COMMENT 'Story Book 코드 REFERENCE: UNRESOLVED. 공통코드 Group 또는 Master Repository 연결을 Metadata에서 확정해야 한다.',
  `chapter_code` varchar(99) DEFAULT NULL COMMENT 'Chapter 코드 REFERENCE: UNRESOLVED. 공통코드 Group 또는 Master Repository 연결을 Metadata에서 확정해야 한다.',
  `section_code` varchar(99) DEFAULT NULL COMMENT 'Section 코드 REFERENCE: UNRESOLVED. 공통코드 Group 또는 Master Repository 연결을 Metadata에서 확정해야 한다.',
  `page_no` int(11) DEFAULT NULL COMMENT 'Page 번호',
  `business_code` varchar(99) NOT NULL COMMENT 'Repository Data의 공식 Business Code. 관련 Business Master 및 Repository Metadata에서 해석하며 값을 Hardcoding하지 않는다.',
  `domain_code` varchar(99) NOT NULL COMMENT 'Repository Data의 기능 Domain Code. SSOT: te_common.cm_common_code의 group_code=CM_DOMAIN. SE, AP, DB, DC, DU, EN, FG, IC, LM, MD, MN, RP, SC, ST, TP, TS 등 등록값만 사용한다.',
  `data_type_code` varchar(99) NOT NULL COMMENT '자료구분 코드 REFERENCE: te_common.cm_common_code의 group_code=CM_DATA_TYPE. Generator, Engine 및 AI는 해당 Group의 code를 해석한다.',
  `data_code` varchar(99) NOT NULL COMMENT '자료 코드 REFERENCE: UNRESOLVED. 공통코드 Group 또는 Master Repository 연결을 Metadata에서 확정해야 한다.',
  `data_name` varchar(150) NOT NULL COMMENT '자료명',
  `data_version` varchar(99) NOT NULL DEFAULT 'v1.0' COMMENT '자료 버전',
  `data_json` longtext CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '자료 상세 JSON' CHECK (json_valid(`data_json`)),
  `footer_json` longtext CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT 'Story Footer JSON' CHECK (json_valid(`footer_json`)),
  `code_description` varchar(2000) DEFAULT NULL COMMENT '설명',
  `sort_no` int(11) NOT NULL DEFAULT 0 COMMENT '표시 및 처리 순서를 제어하는 정렬 순번.',
  `status_code` varchar(99) NOT NULL DEFAULT 'ACTIVE' COMMENT 'Status Code 코드. Repository Metadata가 정의한 코드 체계로 관리한다. REFERENCE: te_common.cm_common_code의 group_code=STATUS_CODE. Generator, Engine 및 AI는 해당 Group의 code를 해석한다.',
  `created_dt` datetime NOT NULL DEFAULT current_timestamp() COMMENT 'Object 최초 생성 일시.',
  `created_by` varchar(99) NOT NULL DEFAULT 'SYSTEM' COMMENT 'Object를 최초 생성한 사용자 또는 실행 주체 식별자.',
  `updated_dt` datetime NOT NULL DEFAULT current_timestamp() ON UPDATE current_timestamp() COMMENT 'Object 최종 수정 일시.',
  `updated_by` varchar(99) NOT NULL DEFAULT 'SYSTEM' COMMENT 'Object를 최종 수정한 사용자 또는 실행 주체 식별자.',
  `client_ip` varchar(99) DEFAULT NULL COMMENT 'Object 변경 요청이 발생한 Client IP 주소.',
  `deleted_by` varchar(99) DEFAULT NULL COMMENT 'Object를 논리 삭제한 사용자 또는 실행 주체 식별자.',
  `deleted_dt` datetime DEFAULT NULL COMMENT 'Object 논리 삭제 처리 일시.',
  `program_id` varchar(99) DEFAULT NULL COMMENT 'Object 생성·수정·삭제를 수행한 Program 식별자.',
  PRIMARY KEY (`repository_id`),
  UNIQUE KEY `uk_cm_repository_data` (`business_code`,`domain_code`,`data_type_code`,`data_code`,`data_version`),
  KEY `idx_cm_repository_business_domain` (`business_code`,`domain_code`),
  KEY `idx_cm_repository_data_type` (`data_type_code`),
  KEY `idx_cm_repository_status` (`status_code`,`deleted_dt`),
  KEY `idx_cm_repository_book_page` (`book_code`,`chapter_code`,`section_code`,`page_no`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='PURPOSE: Book·Chapter·Section 계층의 Repository Data Object를 관리한다. ROLE: COMMON 공식 Repository. SSOT: 해당 Object 정의와 관계의 단일 원천. ENGINE_GUIDE: Generator, Engine 및 AI는 이 테이블을 Repository First로 해석하며 값과 규칙의 Hardcoding을 금지한다.';

INSERT INTO `cm_repository_backup_20260805_storage_separation` (`repository_id`, `book_code`, `chapter_code`, `section_code`, `page_no`, `business_code`, `domain_code`, `data_type_code`, `data_code`, `data_name`, `data_version`, `data_json`, `footer_json`, `code_description`, `sort_no`, `status_code`, `created_dt`, `created_by`, `updated_dt`, `updated_by`, `client_ip`, `deleted_by`, `deleted_dt`, `program_id`) VALUES ('CM_CO_REPOSITORY_20260628_025148_00007', NULL, NULL, NULL, NULL, 'SP', 'SE', 'DEFINITION', 'SEQUENCE_POLICY_YEARLY', 'Yearly Sequence Policy Definition', 'v1.0', '{"policy_code": "YEARLY", "sequence_date_type": "YEARLY", "sequence_date_rule": "YYYY0000", "reset_unit": "YEAR", "description": "연도가 변경되면 시퀀스를 1부터 다시 시작한다."}', NULL, '연도별 시퀀스 정책 정의', 10, 'ACTIVE', '2026-06-28T02:51:48', 'SYSTEM', '2026-07-21T03:43:25', 'SYSTEM', NULL, NULL, NULL, 'CM_CO_PROGRAM_20260628_023031_00021');
INSERT INTO `cm_repository_backup_20260805_storage_separation` (`repository_id`, `book_code`, `chapter_code`, `section_code`, `page_no`, `business_code`, `domain_code`, `data_type_code`, `data_code`, `data_name`, `data_version`, `data_json`, `footer_json`, `code_description`, `sort_no`, `status_code`, `created_dt`, `created_by`, `updated_dt`, `updated_by`, `client_ip`, `deleted_by`, `deleted_dt`, `program_id`) VALUES ('CM_CO_REPOSITORY_20260628_025148_00008', NULL, NULL, NULL, NULL, 'SP', 'SE', 'DEFINITION', 'SEQUENCE_FORMAT_SPS_YEAR_5', 'SPS Year 5 Sequence Format Definition', 'v1.0', '{"format_code": "SPS_YEAR_5", "format_pattern": "{BUSINESS}_{DOMAIN}_{YYYY}_{SEQ:5}", "sequence_length": 5, "example": "SP_SE_2026_00001"}', NULL, 'SPS 기본 연도별 5자리 시퀀스 포맷 정의', 20, 'ACTIVE', '2026-06-28T02:51:48', 'SYSTEM', '2026-07-21T03:43:25', 'SYSTEM', NULL, NULL, NULL, 'CM_CO_PROGRAM_20260628_023031_00021');
INSERT INTO `cm_repository_backup_20260805_storage_separation` (`repository_id`, `book_code`, `chapter_code`, `section_code`, `page_no`, `business_code`, `domain_code`, `data_type_code`, `data_code`, `data_name`, `data_version`, `data_json`, `footer_json`, `code_description`, `sort_no`, `status_code`, `created_dt`, `created_by`, `updated_dt`, `updated_by`, `client_ip`, `deleted_by`, `deleted_dt`, `program_id`) VALUES ('CM_CO_REPOSITORY_20260628_025148_00009', NULL, NULL, NULL, NULL, 'SP', 'SE', 'DEFINITION', 'SEQUENCE_SP_SE', 'Story Programming Sequence Definition', 'v1.0', '{"sequence_code": "SPSE", "business_code": "SP", "domain_code": "SE", "policy_code": "YEARLY", "format_code": "SPS_YEAR_5", "sequence_length": 5, "prefix_code": "SP_SE"}', NULL, 'Story Programming Sequence 도메인 식별자 생성 정의', 30, 'ACTIVE', '2026-06-28T02:51:48', 'SYSTEM', '2026-07-21T03:43:25', 'SYSTEM', NULL, NULL, NULL, 'CM_CO_PROGRAM_20260628_023031_00021');

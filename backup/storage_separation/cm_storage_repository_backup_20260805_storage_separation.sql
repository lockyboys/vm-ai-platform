-- Backup: te_common.cm_storage_repository
-- Captured before MongoDB separation pilot on 2026-08-05.
-- Source row count: 7

CREATE TABLE `cm_storage_repository` (
  `repository_id` varchar(99) NOT NULL COMMENT '저장소ID',
  `repository_name` varchar(150) NOT NULL COMMENT '저장소명',
  `repository_type` varchar(99) NOT NULL COMMENT '저장소유형',
  `database_name` varchar(150) DEFAULT NULL COMMENT 'DB명',
  `connection_host` varchar(500) DEFAULT NULL COMMENT '접속주소',
  `retention_days` int(11) DEFAULT 365 COMMENT '보관일수',
  `archive_days` int(11) DEFAULT 90 COMMENT '보관소 이동일수',
  `disposal_days` int(11) DEFAULT 1095 COMMENT '폐기일수',
  `created_dt` datetime DEFAULT current_timestamp() COMMENT 'Object 최초 생성 일시.',
  `updated_dt` datetime DEFAULT current_timestamp() ON UPDATE current_timestamp() COMMENT 'Object 최종 수정 일시.',
  `created_by` varchar(99) NOT NULL DEFAULT 'SYSTEM' COMMENT 'Object를 최초 생성한 사용자 또는 실행 주체 식별자.',
  `updated_by` varchar(99) DEFAULT NULL COMMENT 'Object를 최종 수정한 사용자 또는 실행 주체 식별자.',
  `deleted_by` varchar(99) DEFAULT NULL COMMENT 'Object를 논리 삭제한 사용자 또는 실행 주체 식별자.',
  `deleted_dt` datetime DEFAULT NULL COMMENT 'Object 논리 삭제 처리 일시.',
  `change_story` varchar(2000) DEFAULT NULL COMMENT 'Change Story 값. cm_storage_repository Object의 해당 속성을 관리한다.',
  `client_ip` varchar(99) DEFAULT NULL COMMENT 'Object 변경 요청이 발생한 Client IP 주소.',
  `program_id` varchar(99) DEFAULT NULL COMMENT 'Object 생성·수정·삭제를 수행한 Program 식별자.',
  `status_code` varchar(99) NOT NULL DEFAULT 'ACTIVE' COMMENT 'Status Code 코드.',
  PRIMARY KEY (`repository_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

INSERT INTO `cm_storage_repository` (
  `repository_id`, `repository_name`, `repository_type`, `database_name`,
  `connection_host`, `retention_days`, `archive_days`, `disposal_days`,
  `created_dt`, `updated_dt`, `created_by`, `updated_by`,
  `deleted_by`, `deleted_dt`, `change_story`, `client_ip`, `program_id`, `status_code`
) VALUES
('CM_CO_REPOSITORY_20260624_103422_00001', '이미지 저장소', 'FILE', NULL, NULL, 365, 90, 1095, '2026-06-24 10:34:22', '2026-07-21 03:43:25', 'SYSTEM', NULL, NULL, NULL, NULL, NULL, NULL, 'ACTIVE'),
('CM_CO_REPOSITORY_20260624_103422_00002', 'AI Platform MariaDB', 'MARIADB', 'te_ai_platform', NULL, 365, 90, 1095, '2026-06-24 10:34:22', '2026-07-21 03:43:25', 'SYSTEM', NULL, NULL, NULL, NULL, NULL, NULL, 'ACTIVE'),
('CM_CO_REPOSITORY_20260624_103422_00003', '공통 MariaDB', 'MARIADB', 'te_common', NULL, 365, 90, 1095, '2026-06-24 10:34:22', '2026-07-21 03:43:25', 'SYSTEM', NULL, NULL, NULL, NULL, NULL, NULL, 'ACTIVE'),
('CM_CO_REPOSITORY_20260624_103422_00004', '건강동행 MariaDB', 'MARIADB', 'te_health_companion', NULL, 365, 90, 1095, '2026-06-24 10:34:22', '2026-07-21 03:43:25', 'SYSTEM', NULL, NULL, NULL, NULL, NULL, NULL, 'ACTIVE'),
('CM_CO_REPOSITORY_20260624_103422_00005', '건강동행 MongoDB', 'MONGODB', 'health_companion_ai', NULL, 365, 90, 1095, '2026-06-24 10:34:22', '2026-07-21 03:43:25', 'SYSTEM', NULL, NULL, NULL, NULL, NULL, NULL, 'ACTIVE'),
('CM_CO_REPOSITORY_20260624_103422_00006', 'PDF 저장소', 'FILE', NULL, NULL, 365, 90, 1095, '2026-06-24 10:34:22', '2026-07-21 03:43:25', 'SYSTEM', NULL, NULL, NULL, NULL, NULL, NULL, 'ACTIVE'),
('CM_CO_REPOSITORY_20260624_103422_00010', '음성 저장소', 'FILE', NULL, NULL, 365, 90, 1095, '2026-06-24 10:34:22', '2026-07-21 03:43:25', 'SYSTEM', NULL, NULL, NULL, NULL, NULL, NULL, 'ACTIVE');

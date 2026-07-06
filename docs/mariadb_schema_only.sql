/*M!999999\- enable the sandbox mode */ 
-- MariaDB dump 10.19  Distrib 10.11.14-MariaDB, for debian-linux-gnu (x86_64)
--
-- Host: localhost    Database: te_common
-- ------------------------------------------------------
-- Server version	10.11.14-MariaDB-0+deb12u2

/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET @OLD_CHARACTER_SET_RESULTS=@@CHARACTER_SET_RESULTS */;
/*!40101 SET @OLD_COLLATION_CONNECTION=@@COLLATION_CONNECTION */;
/*!40101 SET NAMES utf8mb4 */;
/*!40103 SET @OLD_TIME_ZONE=@@TIME_ZONE */;
/*!40103 SET TIME_ZONE='+00:00' */;
/*!40014 SET @OLD_UNIQUE_CHECKS=@@UNIQUE_CHECKS, UNIQUE_CHECKS=0 */;
/*!40014 SET @OLD_FOREIGN_KEY_CHECKS=@@FOREIGN_KEY_CHECKS, FOREIGN_KEY_CHECKS=0 */;
/*!40101 SET @OLD_SQL_MODE=@@SQL_MODE, SQL_MODE='NO_AUTO_VALUE_ON_ZERO' */;
/*!40111 SET @OLD_SQL_NOTES=@@SQL_NOTES, SQL_NOTES=0 */;

--
-- Table structure for table `cm_audit_policy`
--

DROP TABLE IF EXISTS `cm_audit_policy`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8mb4 */;
CREATE TABLE `cm_audit_policy` (
  `audit_policy_id` varchar(30) NOT NULL COMMENT '감사 정책 ID',
  `audit_policy_code` varchar(30) NOT NULL COMMENT '감사 정책 코드',
  `audit_policy_name` varchar(100) NOT NULL COMMENT '감사 정책명',
  `description` varchar(500) DEFAULT NULL COMMENT '설명',
  `sort_no` int(11) NOT NULL DEFAULT 0 COMMENT '정렬번호',
  `created_dt` datetime NOT NULL DEFAULT current_timestamp(),
  `created_by` varchar(100) NOT NULL DEFAULT 'SYSTEM',
  `updated_dt` datetime NOT NULL DEFAULT current_timestamp() ON UPDATE current_timestamp(),
  `updated_by` varchar(100) NOT NULL DEFAULT 'SYSTEM',
  `deleted_by` varchar(100) DEFAULT NULL,
  `deleted_dt` datetime DEFAULT NULL,
  `program_id` varchar(100) DEFAULT NULL,
  `client_ip` varchar(50) DEFAULT NULL,
  `status_code` varchar(50) NOT NULL DEFAULT 'ACTIVE',
  PRIMARY KEY (`audit_policy_id`),
  UNIQUE KEY `uk_cm_audit_policy_code` (`audit_policy_code`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci COMMENT='감사 정책';
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `cm_business_domain`
--

DROP TABLE IF EXISTS `cm_business_domain`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8mb4 */;
CREATE TABLE `cm_business_domain` (
  `business_domain_id` varchar(30) NOT NULL COMMENT '업무 도메인 ID',
  `business_domain_code` char(2) NOT NULL COMMENT '업무 도메인 코드',
  `business_domain_name` varchar(100) NOT NULL COMMENT '업무 도메인명',
  `description` varchar(500) DEFAULT NULL COMMENT '설명',
  `sort_no` int(11) NOT NULL DEFAULT 0 COMMENT '정렬번호',
  `created_dt` datetime NOT NULL DEFAULT current_timestamp(),
  `created_by` varchar(100) NOT NULL DEFAULT 'SYSTEM',
  `updated_dt` datetime NOT NULL DEFAULT current_timestamp() ON UPDATE current_timestamp(),
  `updated_by` varchar(100) NOT NULL DEFAULT 'SYSTEM',
  `deleted_by` varchar(100) DEFAULT NULL,
  `deleted_dt` datetime DEFAULT NULL,
  `program_id` varchar(100) DEFAULT NULL,
  `client_ip` varchar(50) DEFAULT NULL,
  `status_code` varchar(50) NOT NULL DEFAULT 'ACTIVE',
  PRIMARY KEY (`business_domain_id`),
  UNIQUE KEY `uk_cm_business_domain_code` (`business_domain_code`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci COMMENT='업무 도메인';
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `cm_change_history`
--

DROP TABLE IF EXISTS `cm_change_history`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8mb4 */;
CREATE TABLE `cm_change_history` (
  `change_history_id` bigint(20) NOT NULL AUTO_INCREMENT COMMENT '변경 이력 ID',
  `target_database_name` varchar(100) NOT NULL COMMENT '대상 DB명',
  `target_table_name` varchar(100) NOT NULL COMMENT '대상 테이블명',
  `target_record_id` varchar(100) NOT NULL COMMENT '대상 레코드 ID',
  `action_type` varchar(30) NOT NULL COMMENT '작업 유형 공통코드 CHANGE_ACTION_TYPE',
  `change_story` varchar(500) NOT NULL COMMENT '변경 스토리: 목적어 + 동사',
  `created_by` varchar(100) NOT NULL DEFAULT 'SYSTEM' COMMENT '변경자',
  `created_dt` datetime NOT NULL DEFAULT current_timestamp() COMMENT '변경일시',
  `client_ip` varchar(50) DEFAULT NULL COMMENT '접속 IP',
  `program_id` varchar(100) DEFAULT NULL COMMENT '프로그램 ID',
  `status_code` varchar(50) NOT NULL DEFAULT 'ACTIVE',
  PRIMARY KEY (`change_history_id`,`created_dt`),
  KEY `idx_change_history_target` (`target_database_name`,`target_table_name`,`target_record_id`),
  KEY `idx_change_history_created_dt` (`created_dt`),
  KEY `idx_change_history_action_type` (`action_type`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='공통 변경 이력'
 PARTITION BY RANGE  COLUMNS(`created_dt`)
(PARTITION `p202606` VALUES LESS THAN ('2026-07-01') ENGINE = InnoDB,
 PARTITION `p202607` VALUES LESS THAN ('2026-08-01') ENGINE = InnoDB,
 PARTITION `p202608` VALUES LESS THAN ('2026-09-01') ENGINE = InnoDB,
 PARTITION `p_future` VALUES LESS THAN (MAXVALUE) ENGINE = InnoDB);
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `cm_code_inspection_result`
--

DROP TABLE IF EXISTS `cm_code_inspection_result`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8mb4 */;
CREATE TABLE `cm_code_inspection_result` (
  `inspection_id` varchar(30) NOT NULL,
  `inspection_type` varchar(50) NOT NULL,
  `group_code` varchar(50) NOT NULL,
  `code` varchar(50) DEFAULT NULL,
  `code_name` varchar(100) DEFAULT NULL,
  `related_codes` varchar(500) DEFAULT NULL,
  `message` varchar(500) NOT NULL,
  `severity_code` varchar(20) NOT NULL DEFAULT 'WARNING',
  `created_dt` datetime NOT NULL DEFAULT current_timestamp(),
  `updated_dt` datetime NOT NULL DEFAULT current_timestamp() ON UPDATE current_timestamp(),
  `created_by` varchar(100) NOT NULL DEFAULT 'SYSTEM',
  `updated_by` varchar(100) DEFAULT NULL,
  `deleted_by` varchar(100) DEFAULT NULL,
  `deleted_dt` datetime DEFAULT NULL,
  `client_ip` varchar(50) DEFAULT NULL,
  `program_id` varchar(100) DEFAULT NULL,
  `status_code` varchar(50) NOT NULL DEFAULT 'ACTIVE',
  PRIMARY KEY (`inspection_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `cm_common_code`
--

DROP TABLE IF EXISTS `cm_common_code`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8mb4 */;
CREATE TABLE `cm_common_code` (
  `group_code` varchar(50) NOT NULL,
  `code` varchar(50) NOT NULL,
  `code_name` varchar(100) NOT NULL,
  `code_description` varchar(500) DEFAULT NULL COMMENT '코드 설명',
  `sort_no` int(11) NOT NULL DEFAULT 0,
  `status_code` varchar(50) NOT NULL DEFAULT 'ACTIVE',
  `created_dt` datetime NOT NULL DEFAULT current_timestamp(),
  `created_by` varchar(100) NOT NULL DEFAULT 'SYSTEM',
  `updated_dt` datetime NOT NULL DEFAULT current_timestamp() ON UPDATE current_timestamp(),
  `updated_by` varchar(100) NOT NULL DEFAULT 'SYSTEM',
  `client_ip` varchar(50) DEFAULT NULL,
  `deleted_by` varchar(100) DEFAULT NULL,
  `deleted_dt` datetime DEFAULT NULL,
  `program_id` varchar(100) DEFAULT NULL,
  PRIMARY KEY (`group_code`,`code`),
  CONSTRAINT `fk_cm_common_code_group` FOREIGN KEY (`group_code`) REFERENCES `cm_common_code_group` (`group_code`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `cm_common_code_group`
--

DROP TABLE IF EXISTS `cm_common_code_group`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8mb4 */;
CREATE TABLE `cm_common_code_group` (
  `group_code` varchar(50) NOT NULL,
  `group_name` varchar(100) NOT NULL,
  `group_description` varchar(500) DEFAULT NULL COMMENT '그룹 설명',
  `sort_no` int(11) DEFAULT 0,
  `status_code` varchar(50) NOT NULL DEFAULT 'ACTIVE',
  `reserved_yn` char(1) NOT NULL DEFAULT 'N' COMMENT '예약 그룹 여부',
  `system_yn` char(1) NOT NULL DEFAULT 'N' COMMENT '시스템 그룹 여부',
  `created_dt` datetime NOT NULL DEFAULT current_timestamp(),
  `created_by` varchar(100) NOT NULL DEFAULT 'SYSTEM',
  `updated_dt` datetime NOT NULL DEFAULT current_timestamp() ON UPDATE current_timestamp(),
  `updated_by` varchar(100) NOT NULL DEFAULT 'SYSTEM',
  `client_ip` varchar(50) DEFAULT NULL,
  `deleted_by` varchar(100) DEFAULT NULL,
  `deleted_dt` datetime DEFAULT NULL,
  `program_id` varchar(100) DEFAULT NULL,
  PRIMARY KEY (`group_code`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `cm_consent_history`
--

DROP TABLE IF EXISTS `cm_consent_history`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8mb4 */;
CREATE TABLE `cm_consent_history` (
  `consent_history_id` bigint(20) NOT NULL AUTO_INCREMENT,
  `user_id` varchar(100) NOT NULL,
  `consent_type` varchar(50) NOT NULL,
  `consent_yn` char(1) NOT NULL,
  `created_by` varchar(100) NOT NULL,
  `created_dt` datetime NOT NULL DEFAULT current_timestamp(),
  `updated_by` varchar(100) DEFAULT NULL,
  `updated_dt` datetime DEFAULT NULL,
  `deleted_by` varchar(100) DEFAULT NULL,
  `deleted_dt` datetime DEFAULT NULL,
  `change_story` varchar(500) DEFAULT NULL,
  `client_ip` varchar(50) DEFAULT NULL,
  `program_id` varchar(100) DEFAULT NULL,
  `status_code` varchar(50) NOT NULL DEFAULT 'ACTIVE',
  PRIMARY KEY (`consent_history_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `cm_country`
--

DROP TABLE IF EXISTS `cm_country`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8mb4 */;
CREATE TABLE `cm_country` (
  `country_code` varchar(10) NOT NULL,
  `country_name` varchar(100) NOT NULL,
  `native_name` varchar(100) DEFAULT NULL,
  `sort_no` int(11) NOT NULL DEFAULT 0,
  `status_code` varchar(50) NOT NULL DEFAULT 'ACTIVE',
  `created_dt` datetime NOT NULL DEFAULT current_timestamp(),
  `created_by` varchar(100) NOT NULL DEFAULT 'SYSTEM',
  `updated_dt` datetime NOT NULL DEFAULT current_timestamp() ON UPDATE current_timestamp(),
  `updated_by` varchar(100) NOT NULL DEFAULT 'SYSTEM',
  `client_ip` varchar(50) DEFAULT NULL,
  `deleted_by` varchar(100) DEFAULT NULL,
  `deleted_dt` datetime DEFAULT NULL,
  `program_id` varchar(100) DEFAULT NULL,
  PRIMARY KEY (`country_code`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `cm_data_classification`
--

DROP TABLE IF EXISTS `cm_data_classification`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8mb4 */;
CREATE TABLE `cm_data_classification` (
  `classification_code` varchar(50) NOT NULL COMMENT '데이터 등급 코드',
  `classification_name` varchar(100) NOT NULL COMMENT '데이터 등급',
  `description` varchar(500) DEFAULT NULL,
  `encryption_required_yn` char(1) DEFAULT 'N',
  `masking_required_yn` char(1) DEFAULT 'N',
  `ai_access_allowed_yn` char(1) DEFAULT 'Y',
  `external_transfer_allowed_yn` char(1) DEFAULT 'N',
  `created_by` varchar(100) NOT NULL DEFAULT 'SYSTEM',
  `created_dt` datetime NOT NULL DEFAULT current_timestamp(),
  `updated_by` varchar(100) DEFAULT NULL,
  `updated_dt` datetime DEFAULT NULL,
  `deleted_by` varchar(100) DEFAULT NULL,
  `deleted_dt` datetime DEFAULT NULL,
  `client_ip` varchar(50) DEFAULT NULL,
  `program_id` varchar(100) DEFAULT NULL,
  `status_code` varchar(50) NOT NULL DEFAULT 'ACTIVE',
  PRIMARY KEY (`classification_code`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `cm_data_lifecycle_index`
--

DROP TABLE IF EXISTS `cm_data_lifecycle_index`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8mb4 */;
CREATE TABLE `cm_data_lifecycle_index` (
  `lifecycle_id` bigint(20) NOT NULL AUTO_INCREMENT COMMENT '생명주기 ID',
  `user_id` varchar(100) NOT NULL COMMENT '사용자 ID',
  `data_asset_id` varchar(100) NOT NULL COMMENT '데이터 자산 ID',
  `data_type` varchar(50) NOT NULL COMMENT '데이터 유형',
  `repository_id` varchar(50) NOT NULL COMMENT '저장소 ID',
  `storage_database` varchar(100) DEFAULT NULL COMMENT 'DB명',
  `storage_collection` varchar(100) DEFAULT NULL COMMENT 'Mongo Collection',
  `storage_table` varchar(100) DEFAULT NULL COMMENT 'MariaDB Table',
  `storage_record_id` varchar(100) DEFAULT NULL COMMENT '레코드 ID',
  `storage_document_id` varchar(100) DEFAULT NULL COMMENT 'Mongo Document ID',
  `status_code` varchar(30) NOT NULL COMMENT '상태',
  `retention_days` int(11) DEFAULT 365 COMMENT '보관기간',
  `created_dt` datetime NOT NULL DEFAULT current_timestamp(),
  `updated_dt` datetime DEFAULT NULL,
  `disposed_at` datetime DEFAULT NULL COMMENT '폐기일시',
  `disposal_reason` varchar(500) DEFAULT NULL COMMENT '폐기사유',
  `created_by` varchar(100) NOT NULL DEFAULT 'SYSTEM',
  `updated_by` varchar(100) DEFAULT NULL,
  `deleted_by` varchar(100) DEFAULT NULL,
  `deleted_dt` datetime DEFAULT NULL,
  `change_story` varchar(500) DEFAULT NULL,
  `client_ip` varchar(50) DEFAULT NULL,
  `program_id` varchar(100) DEFAULT NULL,
  PRIMARY KEY (`lifecycle_id`),
  KEY `idx_user_id` (`user_id`),
  KEY `idx_data_asset_id` (`data_asset_id`),
  KEY `idx_status_code` (`status_code`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='데이터 생명주기 추적';
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `cm_data_type`
--

DROP TABLE IF EXISTS `cm_data_type`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8mb4 */;
CREATE TABLE `cm_data_type` (
  `data_type_code` varchar(50) NOT NULL,
  `data_type_name` varchar(100) DEFAULT NULL,
  `description` varchar(500) DEFAULT NULL,
  `default_classification_code` varchar(50) DEFAULT NULL,
  `default_storage_type` varchar(50) DEFAULT NULL,
  `default_retention_policy_code` varchar(50) DEFAULT NULL,
  `ai_analysis_allowed_yn` char(1) DEFAULT 'Y',
  `encryption_required_yn` char(1) DEFAULT 'N',
  `created_by` varchar(100) NOT NULL DEFAULT 'SYSTEM',
  `created_dt` datetime NOT NULL DEFAULT current_timestamp(),
  `updated_by` varchar(100) DEFAULT NULL,
  `updated_dt` datetime DEFAULT NULL,
  `deleted_by` varchar(100) DEFAULT NULL,
  `deleted_dt` datetime DEFAULT NULL,
  `client_ip` varchar(50) DEFAULT NULL,
  `program_id` varchar(100) DEFAULT NULL,
  `status_code` varchar(50) NOT NULL DEFAULT 'ACTIVE',
  PRIMARY KEY (`data_type_code`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `cm_language`
--

DROP TABLE IF EXISTS `cm_language`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8mb4 */;
CREATE TABLE `cm_language` (
  `language_code` varchar(10) NOT NULL,
  `language_name` varchar(100) NOT NULL,
  `native_name` varchar(100) NOT NULL,
  `sort_no` int(11) NOT NULL DEFAULT 0,
  `status_code` varchar(50) NOT NULL DEFAULT 'ACTIVE',
  `created_dt` datetime NOT NULL DEFAULT current_timestamp(),
  `created_by` varchar(100) NOT NULL DEFAULT 'SYSTEM',
  `updated_dt` datetime NOT NULL DEFAULT current_timestamp() ON UPDATE current_timestamp(),
  `updated_by` varchar(100) NOT NULL DEFAULT 'SYSTEM',
  `client_ip` varchar(50) DEFAULT NULL,
  `deleted_by` varchar(100) DEFAULT NULL,
  `deleted_dt` datetime DEFAULT NULL,
  `program_id` varchar(100) DEFAULT NULL,
  PRIMARY KEY (`language_code`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `cm_legal_retention_policy`
--

DROP TABLE IF EXISTS `cm_legal_retention_policy`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8mb4 */;
CREATE TABLE `cm_legal_retention_policy` (
  `legal_retention_policy_id` bigint(20) NOT NULL AUTO_INCREMENT COMMENT '법적 보존 정책 ID',
  `data_type` varchar(50) NOT NULL COMMENT '데이터 유형',
  `legal_basis_code` varchar(50) NOT NULL COMMENT '법적 근거 코드',
  `retention_days` int(11) NOT NULL COMMENT '법적 보존일수',
  `retention_reason` varchar(500) NOT NULL COMMENT '보존 사유',
  `disposal_action_code` varchar(50) NOT NULL COMMENT '보존기간 만료 후 처리 방식',
  `created_by` varchar(100) NOT NULL DEFAULT 'SYSTEM',
  `created_dt` datetime NOT NULL DEFAULT current_timestamp(),
  `updated_by` varchar(100) DEFAULT NULL,
  `updated_dt` datetime DEFAULT NULL,
  `deleted_by` varchar(100) DEFAULT NULL,
  `deleted_dt` datetime DEFAULT NULL,
  `client_ip` varchar(50) DEFAULT NULL,
  `program_id` varchar(100) DEFAULT NULL,
  `status_code` varchar(50) NOT NULL DEFAULT 'ACTIVE',
  PRIMARY KEY (`legal_retention_policy_id`),
  KEY `idx_legal_retention_data_type` (`data_type`),
  KEY `idx_legal_retention_basis` (`legal_basis_code`)
) ENGINE=InnoDB AUTO_INCREMENT=5 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='법적 보존기한 정책';
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `cm_locale`
--

DROP TABLE IF EXISTS `cm_locale`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8mb4 */;
CREATE TABLE `cm_locale` (
  `locale_code` varchar(20) NOT NULL,
  `language_code` varchar(10) NOT NULL,
  `country_code` varchar(10) NOT NULL,
  `locale_name` varchar(100) NOT NULL,
  `native_name` varchar(100) NOT NULL,
  `date_format` varchar(30) DEFAULT NULL,
  `time_format` varchar(30) DEFAULT NULL,
  `datetime_format` varchar(50) DEFAULT NULL,
  `number_format` varchar(30) DEFAULT NULL,
  `timezone_id` varchar(100) DEFAULT NULL,
  `sort_no` int(11) NOT NULL DEFAULT 0,
  `status_code` varchar(50) NOT NULL DEFAULT 'ACTIVE',
  `created_dt` datetime NOT NULL DEFAULT current_timestamp(),
  `created_by` varchar(100) NOT NULL DEFAULT 'SYSTEM',
  `updated_dt` datetime NOT NULL DEFAULT current_timestamp() ON UPDATE current_timestamp(),
  `updated_by` varchar(100) NOT NULL DEFAULT 'SYSTEM',
  `deleted_by` varchar(100) DEFAULT NULL,
  `deleted_dt` datetime DEFAULT NULL,
  `client_ip` varchar(50) DEFAULT NULL,
  `program_id` varchar(100) DEFAULT NULL,
  PRIMARY KEY (`locale_code`),
  KEY `fk_cm_locale_language` (`language_code`),
  KEY `fk_cm_locale_country` (`country_code`),
  CONSTRAINT `fk_cm_locale_country` FOREIGN KEY (`country_code`) REFERENCES `cm_country` (`country_code`),
  CONSTRAINT `fk_cm_locale_language` FOREIGN KEY (`language_code`) REFERENCES `cm_language` (`language_code`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `cm_login_history`
--

DROP TABLE IF EXISTS `cm_login_history`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8mb4 */;
CREATE TABLE `cm_login_history` (
  `login_history_id` varchar(30) NOT NULL,
  `member_id` varchar(30) DEFAULT NULL,
  `login_id` varchar(100) NOT NULL,
  `login_status_code` varchar(50) NOT NULL,
  `client_ip` varchar(50) DEFAULT NULL,
  `user_agent` varchar(500) DEFAULT NULL,
  `login_dt` datetime NOT NULL DEFAULT current_timestamp(),
  `status_code` varchar(50) NOT NULL DEFAULT 'ACTIVE',
  PRIMARY KEY (`login_history_id`),
  KEY `fk_cm_login_history_member` (`member_id`),
  CONSTRAINT `fk_cm_login_history_member` FOREIGN KEY (`member_id`) REFERENCES `cm_member` (`member_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `cm_member`
--

DROP TABLE IF EXISTS `cm_member`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8mb4 */;
CREATE TABLE `cm_member` (
  `member_id` varchar(30) NOT NULL,
  `email` varchar(200) NOT NULL,
  `password_hash` varchar(255) NOT NULL,
  `member_name` varchar(100) NOT NULL,
  `member_type_code` varchar(50) NOT NULL,
  `created_dt` datetime NOT NULL DEFAULT current_timestamp(),
  `created_by` varchar(100) NOT NULL DEFAULT 'SYSTEM',
  `updated_dt` datetime NOT NULL DEFAULT current_timestamp() ON UPDATE current_timestamp(),
  `updated_by` varchar(100) NOT NULL DEFAULT 'SYSTEM',
  `client_ip` varchar(50) DEFAULT NULL,
  `deleted_by` varchar(100) DEFAULT NULL,
  `deleted_dt` datetime DEFAULT NULL,
  `program_id` varchar(100) DEFAULT NULL,
  `status_code` varchar(50) NOT NULL DEFAULT 'ACTIVE',
  PRIMARY KEY (`member_id`),
  UNIQUE KEY `uk_cm_member_email` (`email`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `cm_member_private`
--

DROP TABLE IF EXISTS `cm_member_private`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8mb4 */;
CREATE TABLE `cm_member_private` (
  `member_id` varchar(30) NOT NULL,
  `birth_date` date DEFAULT NULL,
  `phone` varchar(30) DEFAULT NULL,
  `email` varchar(200) DEFAULT NULL,
  `address` varchar(500) DEFAULT NULL,
  `created_dt` datetime NOT NULL DEFAULT current_timestamp(),
  `created_by` varchar(100) NOT NULL DEFAULT 'SYSTEM',
  `updated_dt` datetime NOT NULL DEFAULT current_timestamp() ON UPDATE current_timestamp(),
  `updated_by` varchar(100) NOT NULL DEFAULT 'SYSTEM',
  `client_ip` varchar(50) DEFAULT NULL,
  `deleted_by` varchar(100) DEFAULT NULL,
  `deleted_dt` datetime DEFAULT NULL,
  `program_id` varchar(100) DEFAULT NULL,
  `status_code` varchar(50) NOT NULL DEFAULT 'ACTIVE',
  PRIMARY KEY (`member_id`),
  CONSTRAINT `fk_cm_member_private_member` FOREIGN KEY (`member_id`) REFERENCES `cm_member` (`member_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `cm_member_role`
--

DROP TABLE IF EXISTS `cm_member_role`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8mb4 */;
CREATE TABLE `cm_member_role` (
  `member_role_id` varchar(30) NOT NULL,
  `member_id` varchar(30) NOT NULL,
  `role_id` varchar(30) NOT NULL,
  `created_dt` datetime NOT NULL DEFAULT current_timestamp(),
  `created_by` varchar(100) NOT NULL DEFAULT 'SYSTEM',
  `updated_dt` datetime NOT NULL DEFAULT current_timestamp() ON UPDATE current_timestamp(),
  `updated_by` varchar(100) NOT NULL DEFAULT 'SYSTEM',
  `client_ip` varchar(50) DEFAULT NULL,
  `deleted_by` varchar(100) DEFAULT NULL,
  `deleted_dt` datetime DEFAULT NULL,
  `program_id` varchar(100) DEFAULT NULL,
  `status_code` varchar(50) NOT NULL DEFAULT 'ACTIVE',
  PRIMARY KEY (`member_role_id`),
  KEY `fk_cm_member_role_member` (`member_id`),
  KEY `fk_cm_member_role_role` (`role_id`),
  CONSTRAINT `fk_cm_member_role_member` FOREIGN KEY (`member_id`) REFERENCES `cm_member` (`member_id`),
  CONSTRAINT `fk_cm_member_role_role` FOREIGN KEY (`role_id`) REFERENCES `cm_role` (`role_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `cm_repository`
--

DROP TABLE IF EXISTS `cm_repository`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8mb4 */;
CREATE TABLE `cm_repository` (
  `repository_id` varchar(50) NOT NULL COMMENT 'Repository ID',
  `book_code` varchar(50) DEFAULT NULL COMMENT 'Story Book 코드',
  `chapter_code` varchar(50) DEFAULT NULL COMMENT 'Chapter 코드',
  `section_code` varchar(50) DEFAULT NULL COMMENT 'Section 코드',
  `page_no` int(11) DEFAULT NULL COMMENT 'Page 번호',
  `business_code` varchar(50) NOT NULL COMMENT '업무분류 코드',
  `domain_code` varchar(50) NOT NULL COMMENT '도메인 코드',
  `data_type_code` varchar(50) NOT NULL COMMENT '자료구분 코드',
  `data_code` varchar(100) NOT NULL COMMENT '자료 코드',
  `data_name` varchar(200) NOT NULL COMMENT '자료명',
  `data_version` varchar(30) NOT NULL DEFAULT 'v1.0' COMMENT '자료 버전',
  `data_json` longtext CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '자료 상세 JSON' CHECK (json_valid(`data_json`)),
  `footer_json` longtext CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT 'Story Footer JSON' CHECK (json_valid(`footer_json`)),
  `code_description` varchar(500) DEFAULT NULL COMMENT '설명',
  `sort_no` int(11) NOT NULL DEFAULT 0,
  `status_code` varchar(50) NOT NULL DEFAULT 'ACTIVE',
  `created_dt` datetime NOT NULL DEFAULT current_timestamp(),
  `created_by` varchar(100) NOT NULL DEFAULT 'SYSTEM',
  `updated_dt` datetime NOT NULL DEFAULT current_timestamp() ON UPDATE current_timestamp(),
  `updated_by` varchar(100) NOT NULL DEFAULT 'SYSTEM',
  `client_ip` varchar(50) DEFAULT NULL,
  `deleted_by` varchar(100) DEFAULT NULL,
  `deleted_dt` datetime DEFAULT NULL,
  `program_id` varchar(100) DEFAULT NULL,
  PRIMARY KEY (`repository_id`),
  UNIQUE KEY `uk_cm_repository_data` (`business_code`,`domain_code`,`data_type_code`,`data_code`,`data_version`),
  KEY `idx_cm_repository_business_domain` (`business_code`,`domain_code`),
  KEY `idx_cm_repository_data_type` (`data_type_code`),
  KEY `idx_cm_repository_status` (`status_code`,`deleted_dt`),
  KEY `idx_cm_repository_book_page` (`book_code`,`chapter_code`,`section_code`,`page_no`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='SPS Repository Core Table';
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `cm_role`
--

DROP TABLE IF EXISTS `cm_role`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8mb4 */;
CREATE TABLE `cm_role` (
  `role_id` varchar(30) NOT NULL,
  `role_code` varchar(50) NOT NULL,
  `role_name` varchar(100) NOT NULL,
  `created_dt` datetime NOT NULL DEFAULT current_timestamp(),
  `created_by` varchar(100) NOT NULL DEFAULT 'SYSTEM',
  `updated_dt` datetime NOT NULL DEFAULT current_timestamp() ON UPDATE current_timestamp(),
  `updated_by` varchar(100) NOT NULL DEFAULT 'SYSTEM',
  `client_ip` varchar(50) DEFAULT NULL,
  `deleted_by` varchar(100) DEFAULT NULL,
  `deleted_dt` datetime DEFAULT NULL,
  `program_id` varchar(100) DEFAULT NULL,
  `status_code` varchar(50) NOT NULL DEFAULT 'ACTIVE',
  PRIMARY KEY (`role_id`),
  UNIQUE KEY `role_code` (`role_code`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `cm_sequence`
--

DROP TABLE IF EXISTS `cm_sequence`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8mb4 */;
CREATE TABLE `cm_sequence` (
  `sequence_code` varchar(10) NOT NULL,
  `sequence_date` char(8) NOT NULL,
  `current_value` bigint(20) NOT NULL DEFAULT 0,
  `created_dt` datetime NOT NULL DEFAULT current_timestamp(),
  `updated_dt` datetime NOT NULL DEFAULT current_timestamp() ON UPDATE current_timestamp(),
  `created_by` varchar(100) NOT NULL DEFAULT 'SYSTEM',
  `updated_by` varchar(100) DEFAULT NULL,
  `deleted_by` varchar(100) DEFAULT NULL,
  `deleted_dt` datetime DEFAULT NULL,
  `client_ip` varchar(50) DEFAULT NULL,
  `program_id` varchar(100) DEFAULT NULL,
  `status_code` varchar(50) NOT NULL DEFAULT 'ACTIVE',
  PRIMARY KEY (`sequence_code`,`sequence_date`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `cm_sequence_definition`
--

DROP TABLE IF EXISTS `cm_sequence_definition`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8mb4 */;
CREATE TABLE `cm_sequence_definition` (
  `sequence_code` varchar(10) NOT NULL COMMENT '시퀀스 코드',
  `sequence_name` varchar(100) NOT NULL COMMENT '시퀀스명',
  `function_code` varchar(50) NOT NULL COMMENT '기능 코드',
  `domain_code` varchar(50) NOT NULL COMMENT '도메인 코드',
  `policy_code` varchar(30) NOT NULL COMMENT '시퀀스 정책 코드',
  `format_code` varchar(30) NOT NULL COMMENT '시퀀스 포맷 코드',
  `prefix_code` varchar(50) DEFAULT NULL COMMENT 'Prefix 코드',
  `sequence_length` int(11) NOT NULL DEFAULT 5 COMMENT '시퀀스 자리수',
  `code_description` varchar(500) DEFAULT NULL COMMENT '설명',
  `sort_no` int(11) NOT NULL DEFAULT 0,
  `status_code` varchar(50) NOT NULL DEFAULT 'ACTIVE',
  `created_dt` datetime NOT NULL DEFAULT current_timestamp(),
  `created_by` varchar(100) NOT NULL DEFAULT 'SYSTEM',
  `updated_dt` datetime NOT NULL DEFAULT current_timestamp() ON UPDATE current_timestamp(),
  `updated_by` varchar(100) NOT NULL DEFAULT 'SYSTEM',
  `client_ip` varchar(50) DEFAULT NULL,
  `deleted_by` varchar(100) DEFAULT NULL,
  `deleted_dt` datetime DEFAULT NULL,
  `program_id` varchar(100) DEFAULT NULL,
  PRIMARY KEY (`sequence_code`),
  KEY `fk_cm_sequence_definition_policy` (`policy_code`),
  KEY `fk_cm_sequence_definition_format` (`format_code`),
  CONSTRAINT `fk_cm_sequence_definition_format` FOREIGN KEY (`format_code`) REFERENCES `cm_sequence_format_definition` (`format_code`),
  CONSTRAINT `fk_cm_sequence_definition_policy` FOREIGN KEY (`policy_code`) REFERENCES `cm_sequence_policy_definition` (`policy_code`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='SPS Sequence Definition';
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `cm_sequence_format`
--

DROP TABLE IF EXISTS `cm_sequence_format`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8mb4 */;
CREATE TABLE `cm_sequence_format` (
  `format_code` varchar(30) NOT NULL COMMENT '시퀀스 포맷 코드',
  `format_name` varchar(100) NOT NULL COMMENT '시퀀스 포맷명',
  `format_pattern` varchar(300) NOT NULL COMMENT '시퀀스 생성 패턴',
  `sequence_length` int(11) NOT NULL DEFAULT 5 COMMENT '시퀀스 자리수',
  `description` varchar(500) DEFAULT NULL COMMENT '설명',
  `created_dt` datetime NOT NULL DEFAULT current_timestamp(),
  `updated_dt` datetime NOT NULL DEFAULT current_timestamp() ON UPDATE current_timestamp(),
  `created_by` varchar(100) NOT NULL DEFAULT 'SYSTEM',
  `updated_by` varchar(100) DEFAULT NULL,
  `deleted_by` varchar(100) DEFAULT NULL,
  `deleted_dt` datetime DEFAULT NULL,
  `client_ip` varchar(50) DEFAULT NULL,
  `program_id` varchar(100) DEFAULT NULL,
  `status_code` varchar(50) NOT NULL DEFAULT 'ACTIVE',
  PRIMARY KEY (`format_code`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='SPS 시퀀스 포맷 메타데이터';
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `cm_sequence_format_definition`
--

DROP TABLE IF EXISTS `cm_sequence_format_definition`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8mb4 */;
CREATE TABLE `cm_sequence_format_definition` (
  `format_code` varchar(30) NOT NULL COMMENT '시퀀스 포맷 코드',
  `format_name` varchar(100) NOT NULL COMMENT '시퀀스 포맷명',
  `format_pattern` varchar(300) NOT NULL COMMENT '생성 패턴',
  `sequence_length` int(11) NOT NULL DEFAULT 5 COMMENT '시퀀스 자리수',
  `code_description` varchar(500) DEFAULT NULL COMMENT '설명',
  `sort_no` int(11) NOT NULL DEFAULT 0,
  `status_code` varchar(50) NOT NULL DEFAULT 'ACTIVE',
  `created_dt` datetime NOT NULL DEFAULT current_timestamp(),
  `created_by` varchar(100) NOT NULL DEFAULT 'SYSTEM',
  `updated_dt` datetime NOT NULL DEFAULT current_timestamp() ON UPDATE current_timestamp(),
  `updated_by` varchar(100) NOT NULL DEFAULT 'SYSTEM',
  `client_ip` varchar(50) DEFAULT NULL,
  `deleted_by` varchar(100) DEFAULT NULL,
  `deleted_dt` datetime DEFAULT NULL,
  `program_id` varchar(100) DEFAULT NULL,
  PRIMARY KEY (`format_code`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='SPS Sequence Format Definition';
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `cm_sequence_policy`
--

DROP TABLE IF EXISTS `cm_sequence_policy`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8mb4 */;
CREATE TABLE `cm_sequence_policy` (
  `policy_code` varchar(30) NOT NULL COMMENT '시퀀스 초기화 정책 코드',
  `policy_name` varchar(100) NOT NULL COMMENT '시퀀스 초기화 정책명',
  `date_format` varchar(20) NOT NULL COMMENT '날짜 키 생성 형식',
  `description` varchar(500) DEFAULT NULL COMMENT '설명',
  `sort_order` int(11) NOT NULL DEFAULT 0 COMMENT '정렬순서',
  `created_dt` datetime NOT NULL DEFAULT current_timestamp(),
  `updated_dt` datetime NOT NULL DEFAULT current_timestamp() ON UPDATE current_timestamp(),
  `created_by` varchar(100) NOT NULL DEFAULT 'SYSTEM',
  `updated_by` varchar(100) DEFAULT NULL,
  `deleted_by` varchar(100) DEFAULT NULL,
  `deleted_dt` datetime DEFAULT NULL,
  `client_ip` varchar(50) DEFAULT NULL,
  `program_id` varchar(100) DEFAULT NULL,
  `status_code` varchar(50) NOT NULL DEFAULT 'ACTIVE',
  PRIMARY KEY (`policy_code`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='SPS 시퀀스 초기화 정책';
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `cm_sequence_policy_definition`
--

DROP TABLE IF EXISTS `cm_sequence_policy_definition`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8mb4 */;
CREATE TABLE `cm_sequence_policy_definition` (
  `policy_code` varchar(30) NOT NULL COMMENT '시퀀스 정책 코드',
  `policy_name` varchar(100) NOT NULL COMMENT '시퀀스 정책명',
  `sequence_date_type` varchar(30) NOT NULL COMMENT 'NO_RESET/YEARLY/MONTHLY/DAILY',
  `sequence_date_rule` varchar(30) NOT NULL COMMENT '00000000/YYYY0000/YYYYMM00/YYYYMMDD',
  `code_description` varchar(500) DEFAULT NULL COMMENT '설명',
  `sort_no` int(11) NOT NULL DEFAULT 0,
  `status_code` varchar(50) NOT NULL DEFAULT 'ACTIVE',
  `created_dt` datetime NOT NULL DEFAULT current_timestamp(),
  `created_by` varchar(100) NOT NULL DEFAULT 'SYSTEM',
  `updated_dt` datetime NOT NULL DEFAULT current_timestamp() ON UPDATE current_timestamp(),
  `updated_by` varchar(100) NOT NULL DEFAULT 'SYSTEM',
  `client_ip` varchar(50) DEFAULT NULL,
  `deleted_by` varchar(100) DEFAULT NULL,
  `deleted_dt` datetime DEFAULT NULL,
  `program_id` varchar(100) DEFAULT NULL,
  PRIMARY KEY (`policy_code`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='SPS Sequence Policy Definition';
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `cm_sequence_rule`
--

DROP TABLE IF EXISTS `cm_sequence_rule`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8mb4 */;
CREATE TABLE `cm_sequence_rule` (
  `sequence_code` varchar(10) NOT NULL COMMENT '시퀀스 코드',
  `sequence_name` varchar(100) NOT NULL COMMENT '시퀀스명',
  `classification_code` varchar(10) DEFAULT NULL COMMENT '분류 코드',
  `domain_code` varchar(10) DEFAULT NULL COMMENT '도메인 코드',
  `work_type_code` varchar(10) DEFAULT NULL COMMENT '업무유형 코드',
  `policy_code` varchar(30) NOT NULL COMMENT '초기화 정책 코드',
  `format_code` varchar(30) NOT NULL COMMENT '포맷 코드',
  `prefix_code` varchar(30) DEFAULT NULL COMMENT 'Prefix 코드',
  `description` varchar(500) DEFAULT NULL COMMENT '설명',
  `created_dt` datetime NOT NULL DEFAULT current_timestamp(),
  `updated_dt` datetime NOT NULL DEFAULT current_timestamp() ON UPDATE current_timestamp(),
  `created_by` varchar(100) NOT NULL DEFAULT 'SYSTEM',
  `updated_by` varchar(100) DEFAULT NULL,
  `deleted_by` varchar(100) DEFAULT NULL,
  `deleted_dt` datetime DEFAULT NULL,
  `client_ip` varchar(50) DEFAULT NULL,
  `program_id` varchar(100) DEFAULT NULL,
  `status_code` varchar(50) NOT NULL DEFAULT 'ACTIVE',
  PRIMARY KEY (`sequence_code`),
  KEY `fk_cm_sequence_rule_policy` (`policy_code`),
  KEY `fk_cm_sequence_rule_format` (`format_code`),
  CONSTRAINT `fk_cm_sequence_rule_format` FOREIGN KEY (`format_code`) REFERENCES `cm_sequence_format` (`format_code`),
  CONSTRAINT `fk_cm_sequence_rule_policy` FOREIGN KEY (`policy_code`) REFERENCES `cm_sequence_policy` (`policy_code`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='SPS 시퀀스 생성 규칙 메타데이터';
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `cm_storage_policy`
--

DROP TABLE IF EXISTS `cm_storage_policy`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8mb4 */;
CREATE TABLE `cm_storage_policy` (
  `policy_id` bigint(20) NOT NULL AUTO_INCREMENT,
  `data_type` varchar(50) NOT NULL COMMENT '데이터유형',
  `repository_id` varchar(50) NOT NULL COMMENT '저장소ID',
  `retention_days` int(11) NOT NULL COMMENT '보관일수',
  `archive_days` int(11) NOT NULL COMMENT '보관소이동일수',
  `disposal_days` int(11) NOT NULL COMMENT '폐기일수',
  `created_dt` datetime DEFAULT current_timestamp(),
  `updated_dt` datetime DEFAULT current_timestamp() ON UPDATE current_timestamp(),
  `created_by` varchar(100) NOT NULL DEFAULT 'SYSTEM',
  `updated_by` varchar(100) DEFAULT NULL,
  `deleted_by` varchar(100) DEFAULT NULL,
  `deleted_dt` datetime DEFAULT NULL,
  `change_story` varchar(500) DEFAULT NULL,
  `client_ip` varchar(50) DEFAULT NULL,
  `program_id` varchar(100) DEFAULT NULL,
  `status_code` varchar(50) NOT NULL DEFAULT 'ACTIVE',
  PRIMARY KEY (`policy_id`),
  KEY `fk_storage_policy_repository` (`repository_id`),
  CONSTRAINT `fk_storage_policy_repository` FOREIGN KEY (`repository_id`) REFERENCES `cm_storage_repository` (`repository_id`)
) ENGINE=InnoDB AUTO_INCREMENT=7 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='데이터 저장 정책';
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `cm_storage_repository`
--

DROP TABLE IF EXISTS `cm_storage_repository`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8mb4 */;
CREATE TABLE `cm_storage_repository` (
  `repository_id` varchar(50) NOT NULL COMMENT '저장소ID',
  `repository_name` varchar(200) NOT NULL COMMENT '저장소명',
  `repository_type` varchar(50) NOT NULL COMMENT '저장소유형',
  `database_name` varchar(100) DEFAULT NULL COMMENT 'DB명',
  `connection_host` varchar(200) DEFAULT NULL COMMENT '접속주소',
  `retention_days` int(11) DEFAULT 365 COMMENT '보관일수',
  `archive_days` int(11) DEFAULT 90 COMMENT '보관소 이동일수',
  `disposal_days` int(11) DEFAULT 1095 COMMENT '폐기일수',
  `created_dt` datetime DEFAULT current_timestamp(),
  `updated_dt` datetime DEFAULT current_timestamp() ON UPDATE current_timestamp(),
  `created_by` varchar(100) NOT NULL DEFAULT 'SYSTEM',
  `updated_by` varchar(100) DEFAULT NULL,
  `deleted_by` varchar(100) DEFAULT NULL,
  `deleted_dt` datetime DEFAULT NULL,
  `change_story` varchar(500) DEFAULT NULL,
  `client_ip` varchar(50) DEFAULT NULL,
  `program_id` varchar(100) DEFAULT NULL,
  `status_code` varchar(50) NOT NULL DEFAULT 'ACTIVE',
  PRIMARY KEY (`repository_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='저장소 관리';
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `ev_evidence`
--

DROP TABLE IF EXISTS `ev_evidence`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8mb4 */;
CREATE TABLE `ev_evidence` (
  `evidence_id` varchar(30) NOT NULL COMMENT '근거 ID',
  `evidence_code` varchar(100) NOT NULL COMMENT '근거 코드',
  `evidence_name` varchar(200) NOT NULL COMMENT '근거명',
  `evidence_level_code` char(1) NOT NULL COMMENT '근거수준 A/B/C/D',
  `evidence_category_code` varchar(50) NOT NULL COMMENT '근거 분류 코드',
  `organization_name` varchar(200) DEFAULT NULL COMMENT '기관명',
  `source_title` varchar(300) DEFAULT NULL COMMENT '출처 제목',
  `published_dt` date DEFAULT NULL COMMENT '발행일',
  `effective_from_dt` date DEFAULT NULL COMMENT '적용 시작일',
  `effective_to_dt` date DEFAULT NULL COMMENT '적용 종료일',
  `version_no` varchar(30) NOT NULL DEFAULT '1.0' COMMENT '버전',
  `status_code` varchar(30) NOT NULL DEFAULT 'ACTIVE' COMMENT '상태 코드',
  `summary` text DEFAULT NULL COMMENT '요약',
  `remark` varchar(500) DEFAULT NULL COMMENT '비고',
  `sort_no` int(11) NOT NULL DEFAULT 0 COMMENT '정렬번호',
  `created_dt` datetime NOT NULL DEFAULT current_timestamp(),
  `created_by` varchar(100) NOT NULL DEFAULT 'SYSTEM',
  `updated_dt` datetime NOT NULL DEFAULT current_timestamp() ON UPDATE current_timestamp(),
  `updated_by` varchar(100) NOT NULL DEFAULT 'SYSTEM',
  `deleted_by` varchar(100) DEFAULT NULL,
  `deleted_dt` datetime DEFAULT NULL,
  `program_id` varchar(100) DEFAULT NULL,
  `client_ip` varchar(50) DEFAULT NULL,
  PRIMARY KEY (`evidence_id`),
  UNIQUE KEY `uk_ev_evidence_code` (`evidence_code`),
  KEY `ix_ev_evidence_category` (`evidence_category_code`),
  KEY `ix_ev_evidence_level` (`evidence_level_code`),
  KEY `ix_ev_evidence_status` (`status_code`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci COMMENT='근거';
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `ev_evidence_reference`
--

DROP TABLE IF EXISTS `ev_evidence_reference`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8mb4 */;
CREATE TABLE `ev_evidence_reference` (
  `reference_id` varchar(30) NOT NULL COMMENT '근거 참조 ID',
  `evidence_id` varchar(30) NOT NULL COMMENT '근거 ID',
  `reference_type_code` varchar(30) NOT NULL COMMENT '참조 유형 코드',
  `reference_title` varchar(300) NOT NULL COMMENT '참조 제목',
  `organization_name` varchar(200) DEFAULT NULL COMMENT '기관명',
  `author_name` varchar(200) DEFAULT NULL COMMENT '저자명',
  `journal_name` varchar(200) DEFAULT NULL COMMENT '학술지명',
  `doi` varchar(200) DEFAULT NULL COMMENT 'DOI',
  `pmid` varchar(100) DEFAULT NULL COMMENT 'PubMed ID',
  `reference_url` varchar(1000) DEFAULT NULL COMMENT '참조 URL',
  `published_dt` date DEFAULT NULL COMMENT '발행일',
  `remark` varchar(500) DEFAULT NULL COMMENT '비고',
  `sort_no` int(11) NOT NULL DEFAULT 0 COMMENT '정렬번호',
  `created_dt` datetime NOT NULL DEFAULT current_timestamp(),
  `created_by` varchar(100) NOT NULL DEFAULT 'SYSTEM',
  `updated_dt` datetime NOT NULL DEFAULT current_timestamp() ON UPDATE current_timestamp(),
  `updated_by` varchar(100) NOT NULL DEFAULT 'SYSTEM',
  `deleted_by` varchar(100) DEFAULT NULL,
  `deleted_dt` datetime DEFAULT NULL,
  `program_id` varchar(100) DEFAULT NULL,
  `client_ip` varchar(50) DEFAULT NULL,
  `status_code` varchar(50) NOT NULL DEFAULT 'ACTIVE',
  PRIMARY KEY (`reference_id`),
  KEY `ix_ev_reference_evidence` (`evidence_id`),
  CONSTRAINT `fk_ev_reference_evidence` FOREIGN KEY (`evidence_id`) REFERENCES `ev_evidence` (`evidence_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci COMMENT='근거 참조';
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `ev_evidence_version`
--

DROP TABLE IF EXISTS `ev_evidence_version`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8mb4 */;
CREATE TABLE `ev_evidence_version` (
  `evidence_version_id` varchar(30) NOT NULL COMMENT '근거 버전 ID',
  `evidence_id` varchar(30) NOT NULL COMMENT '근거 ID',
  `version_no` varchar(30) NOT NULL COMMENT '버전',
  `effective_from_dt` date NOT NULL COMMENT '적용 시작일',
  `effective_to_dt` date DEFAULT NULL COMMENT '적용 종료일',
  `change_summary` varchar(1000) DEFAULT NULL COMMENT '변경 요약',
  `remark` varchar(500) DEFAULT NULL COMMENT '비고',
  `created_dt` datetime NOT NULL DEFAULT current_timestamp(),
  `created_by` varchar(100) NOT NULL DEFAULT 'SYSTEM',
  `updated_dt` datetime NOT NULL DEFAULT current_timestamp() ON UPDATE current_timestamp(),
  `updated_by` varchar(100) NOT NULL DEFAULT 'SYSTEM',
  `deleted_by` varchar(100) DEFAULT NULL,
  `deleted_dt` datetime DEFAULT NULL,
  `program_id` varchar(100) DEFAULT NULL,
  `client_ip` varchar(50) DEFAULT NULL,
  `status_code` varchar(50) NOT NULL DEFAULT 'ACTIVE',
  PRIMARY KEY (`evidence_version_id`),
  KEY `ix_ev_version_evidence` (`evidence_id`),
  CONSTRAINT `fk_ev_version_evidence` FOREIGN KEY (`evidence_id`) REFERENCES `ev_evidence` (`evidence_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci COMMENT='근거 버전';
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `health_report`
--

DROP TABLE IF EXISTS `health_report`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8mb4 */;
CREATE TABLE `health_report` (
  `health_report_id` bigint(20) NOT NULL AUTO_INCREMENT,
  `patient_id` bigint(20) NOT NULL,
  `report_title` varchar(200) NOT NULL,
  `report_content` text DEFAULT NULL,
  `created_dt` datetime NOT NULL DEFAULT current_timestamp(),
  `updated_dt` datetime DEFAULT NULL,
  `created_by` varchar(100) NOT NULL DEFAULT 'SYSTEM',
  `updated_by` varchar(100) DEFAULT NULL,
  `deleted_by` varchar(100) DEFAULT NULL,
  `deleted_dt` datetime DEFAULT NULL,
  `change_story` varchar(500) DEFAULT NULL,
  `client_ip` varchar(50) DEFAULT NULL,
  `program_id` varchar(100) DEFAULT NULL,
  `status_code` varchar(50) NOT NULL DEFAULT 'ACTIVE',
  PRIMARY KEY (`health_report_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `health_report_backup_20260624`
--

DROP TABLE IF EXISTS `health_report_backup_20260624`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8mb4 */;
CREATE TABLE `health_report_backup_20260624` (
  `health_report_id` bigint(20) NOT NULL DEFAULT 0,
  `patient_id` bigint(20) NOT NULL,
  `report_title` varchar(200) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL,
  `report_content` text CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL,
  `created_at` datetime NOT NULL DEFAULT current_timestamp(),
  `updated_at` datetime DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `md_object`
--

DROP TABLE IF EXISTS `md_object`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8mb4 */;
CREATE TABLE `md_object` (
  `md_object_id` varchar(50) NOT NULL,
  `object_type_group_code` varchar(50) NOT NULL DEFAULT 'OBJECT_TYPE',
  `object_type_code` varchar(50) NOT NULL,
  `object_code` varchar(100) NOT NULL,
  `object_name` varchar(200) NOT NULL,
  `description` text DEFAULT NULL,
  `attribute_json` longtext CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL CHECK (json_valid(`attribute_json`)),
  `sort_no` int(11) NOT NULL DEFAULT 0,
  `status_code` varchar(50) NOT NULL DEFAULT 'ACTIVE',
  `created_dt` datetime NOT NULL DEFAULT current_timestamp(),
  `created_by` varchar(100) NOT NULL DEFAULT 'SYSTEM',
  `updated_dt` datetime NOT NULL DEFAULT current_timestamp() ON UPDATE current_timestamp(),
  `updated_by` varchar(100) NOT NULL DEFAULT 'SYSTEM',
  `deleted_by` varchar(100) DEFAULT NULL,
  `deleted_dt` datetime DEFAULT NULL,
  `client_ip` varchar(50) DEFAULT NULL,
  `program_id` varchar(100) DEFAULT NULL,
  PRIMARY KEY (`md_object_id`),
  UNIQUE KEY `uk_md_object_code` (`object_type_code`,`object_code`),
  KEY `ix_md_object_type` (`object_type_group_code`,`object_type_code`),
  CONSTRAINT `fk_md_object_type` FOREIGN KEY (`object_type_group_code`, `object_type_code`) REFERENCES `cm_common_code` (`group_code`, `code`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `md_relation`
--

DROP TABLE IF EXISTS `md_relation`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8mb4 */;
CREATE TABLE `md_relation` (
  `md_relation_id` varchar(50) NOT NULL,
  `source_md_object_id` varchar(50) NOT NULL,
  `target_md_object_id` varchar(50) NOT NULL,
  `relation_type_code` varchar(50) NOT NULL,
  `direction_code` varchar(50) NOT NULL DEFAULT 'UNI',
  `cardinality_code` varchar(50) NOT NULL DEFAULT 'N:N',
  `description` text DEFAULT NULL,
  `sort_no` int(11) NOT NULL DEFAULT 0,
  `status_code` varchar(50) NOT NULL DEFAULT 'ACTIVE',
  `created_dt` datetime NOT NULL DEFAULT current_timestamp(),
  `created_by` varchar(100) NOT NULL DEFAULT 'SYSTEM',
  `updated_dt` datetime NOT NULL DEFAULT current_timestamp() ON UPDATE current_timestamp(),
  `updated_by` varchar(100) NOT NULL DEFAULT 'SYSTEM',
  `deleted_by` varchar(100) DEFAULT NULL,
  `deleted_dt` datetime DEFAULT NULL,
  `client_ip` varchar(50) DEFAULT NULL,
  `program_id` varchar(100) DEFAULT NULL,
  PRIMARY KEY (`md_relation_id`),
  KEY `ix_md_relation_source` (`source_md_object_id`),
  KEY `ix_md_relation_target` (`target_md_object_id`),
  KEY `ix_md_relation_type` (`relation_type_code`),
  KEY `ix_md_relation_direction` (`direction_code`),
  KEY `ix_md_relation_cardinality` (`cardinality_code`),
  CONSTRAINT `fk_md_relation_source` FOREIGN KEY (`source_md_object_id`) REFERENCES `md_object` (`md_object_id`),
  CONSTRAINT `fk_md_relation_target` FOREIGN KEY (`target_md_object_id`) REFERENCES `md_object` (`md_object_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `rl_rule`
--

DROP TABLE IF EXISTS `rl_rule`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8mb4 */;
CREATE TABLE `rl_rule` (
  `rule_id` varchar(30) NOT NULL COMMENT '규칙 ID',
  `rule_code` varchar(100) NOT NULL COMMENT '규칙 코드',
  `rule_name` varchar(200) NOT NULL COMMENT '규칙명',
  `rule_type_code` varchar(30) NOT NULL COMMENT '규칙 유형 코드',
  `rule_group_code` varchar(50) DEFAULT NULL COMMENT '규칙 그룹 코드',
  `description` varchar(1000) DEFAULT NULL COMMENT '설명',
  `priority_no` int(11) NOT NULL DEFAULT 0 COMMENT '우선순위',
  `status_code` varchar(30) NOT NULL DEFAULT 'ACTIVE' COMMENT '상태 코드',
  `version_no` varchar(30) NOT NULL DEFAULT '1.0' COMMENT '버전',
  `remark` varchar(500) DEFAULT NULL COMMENT '비고',
  `sort_no` int(11) NOT NULL DEFAULT 0 COMMENT '정렬번호',
  `created_dt` datetime NOT NULL DEFAULT current_timestamp(),
  `created_by` varchar(100) NOT NULL DEFAULT 'SYSTEM',
  `updated_dt` datetime NOT NULL DEFAULT current_timestamp() ON UPDATE current_timestamp(),
  `updated_by` varchar(100) NOT NULL DEFAULT 'SYSTEM',
  `deleted_by` varchar(100) DEFAULT NULL,
  `deleted_dt` datetime DEFAULT NULL,
  `program_id` varchar(100) DEFAULT NULL,
  `client_ip` varchar(50) DEFAULT NULL,
  PRIMARY KEY (`rule_id`),
  UNIQUE KEY `uk_rl_rule_code` (`rule_code`),
  KEY `ix_rl_rule_type` (`rule_type_code`),
  KEY `ix_rl_rule_status` (`status_code`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci COMMENT='업무 규칙';
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `rl_rule_action`
--

DROP TABLE IF EXISTS `rl_rule_action`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8mb4 */;
CREATE TABLE `rl_rule_action` (
  `rule_action_id` varchar(30) NOT NULL COMMENT '규칙 실행 ID',
  `rule_id` varchar(30) NOT NULL COMMENT '규칙 ID',
  `action_type_code` varchar(50) NOT NULL COMMENT '실행 유형 코드',
  `action_value` varchar(500) DEFAULT NULL COMMENT '실행 값',
  `sort_no` int(11) NOT NULL DEFAULT 0 COMMENT '실행 정렬번호',
  `remark` varchar(500) DEFAULT NULL COMMENT '비고',
  `created_dt` datetime NOT NULL DEFAULT current_timestamp(),
  `created_by` varchar(100) NOT NULL DEFAULT 'SYSTEM',
  `updated_dt` datetime NOT NULL DEFAULT current_timestamp() ON UPDATE current_timestamp(),
  `updated_by` varchar(100) NOT NULL DEFAULT 'SYSTEM',
  `deleted_by` varchar(100) DEFAULT NULL,
  `deleted_dt` datetime DEFAULT NULL,
  `program_id` varchar(100) DEFAULT NULL,
  `client_ip` varchar(50) DEFAULT NULL,
  `status_code` varchar(50) NOT NULL DEFAULT 'ACTIVE',
  PRIMARY KEY (`rule_action_id`),
  KEY `ix_rl_action_rule` (`rule_id`),
  CONSTRAINT `fk_rl_action_rule` FOREIGN KEY (`rule_id`) REFERENCES `rl_rule` (`rule_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci COMMENT='업무 규칙 실행';
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `rl_rule_condition`
--

DROP TABLE IF EXISTS `rl_rule_condition`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8mb4 */;
CREATE TABLE `rl_rule_condition` (
  `condition_id` varchar(30) NOT NULL COMMENT '규칙 조건 ID',
  `rule_id` varchar(30) NOT NULL COMMENT '규칙 ID',
  `sort_no` int(11) NOT NULL DEFAULT 0 COMMENT '조건 정렬번호',
  `field_code` varchar(100) NOT NULL COMMENT '대상 필드 코드',
  `operator_code` varchar(30) NOT NULL COMMENT '연산자 코드',
  `condition_value` varchar(200) NOT NULL COMMENT '조건 값',
  `logical_operator_code` varchar(30) DEFAULT NULL COMMENT '논리 연산자 코드',
  `remark` varchar(500) DEFAULT NULL COMMENT '비고',
  `created_dt` datetime NOT NULL DEFAULT current_timestamp(),
  `created_by` varchar(100) NOT NULL DEFAULT 'SYSTEM',
  `updated_dt` datetime NOT NULL DEFAULT current_timestamp() ON UPDATE current_timestamp(),
  `updated_by` varchar(100) NOT NULL DEFAULT 'SYSTEM',
  `deleted_by` varchar(100) DEFAULT NULL,
  `deleted_dt` datetime DEFAULT NULL,
  `program_id` varchar(100) DEFAULT NULL,
  `client_ip` varchar(50) DEFAULT NULL,
  `status_code` varchar(50) NOT NULL DEFAULT 'ACTIVE',
  PRIMARY KEY (`condition_id`),
  KEY `ix_rl_condition_rule` (`rule_id`),
  CONSTRAINT `fk_rl_condition_rule` FOREIGN KEY (`rule_id`) REFERENCES `rl_rule` (`rule_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci COMMENT='업무 규칙 조건';
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `rl_rule_evidence`
--

DROP TABLE IF EXISTS `rl_rule_evidence`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8mb4 */;
CREATE TABLE `rl_rule_evidence` (
  `rule_evidence_id` varchar(30) NOT NULL COMMENT '규칙 근거 연결 ID',
  `rule_id` varchar(30) NOT NULL COMMENT '규칙 ID',
  `evidence_id` varchar(30) NOT NULL COMMENT '근거 ID',
  `primary_yn` char(1) NOT NULL DEFAULT 'N' COMMENT '대표 근거 여부',
  `remark` varchar(500) DEFAULT NULL COMMENT '비고',
  `created_dt` datetime NOT NULL DEFAULT current_timestamp(),
  `created_by` varchar(100) NOT NULL DEFAULT 'SYSTEM',
  `updated_dt` datetime NOT NULL DEFAULT current_timestamp() ON UPDATE current_timestamp(),
  `updated_by` varchar(100) NOT NULL DEFAULT 'SYSTEM',
  `deleted_by` varchar(100) DEFAULT NULL,
  `deleted_dt` datetime DEFAULT NULL,
  `program_id` varchar(100) DEFAULT NULL,
  `client_ip` varchar(50) DEFAULT NULL,
  `status_code` varchar(50) NOT NULL DEFAULT 'ACTIVE',
  PRIMARY KEY (`rule_evidence_id`),
  UNIQUE KEY `uk_rl_rule_evidence` (`rule_id`,`evidence_id`),
  KEY `ix_rl_rule_evidence_rule` (`rule_id`),
  KEY `ix_rl_rule_evidence_evidence` (`evidence_id`),
  CONSTRAINT `fk_rl_rule_evidence_evidence` FOREIGN KEY (`evidence_id`) REFERENCES `ev_evidence` (`evidence_id`),
  CONSTRAINT `fk_rl_rule_evidence_rule` FOREIGN KEY (`rule_id`) REFERENCES `rl_rule` (`rule_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci COMMENT='업무 규칙 근거 연결';
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `sql_guard_execution_log`
--

DROP TABLE IF EXISTS `sql_guard_execution_log`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8mb4 */;
CREATE TABLE `sql_guard_execution_log` (
  `execution_id` bigint(20) NOT NULL AUTO_INCREMENT,
  `user_id` bigint(20) NOT NULL,
  `menu_code` varchar(100) NOT NULL,
  `button_code` varchar(100) NOT NULL,
  `query_id` varchar(150) NOT NULL,
  `crud_type` varchar(20) NOT NULL,
  `success_yn` char(1) NOT NULL,
  `row_count` int(11) DEFAULT NULL,
  `error_message` text DEFAULT NULL,
  `executed_at` datetime NOT NULL DEFAULT current_timestamp(),
  `status_code` varchar(50) NOT NULL DEFAULT 'ACTIVE',
  PRIMARY KEY (`execution_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `sql_guard_verification_log`
--

DROP TABLE IF EXISTS `sql_guard_verification_log`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8mb4 */;
CREATE TABLE `sql_guard_verification_log` (
  `log_id` bigint(20) NOT NULL AUTO_INCREMENT,
  `query_id` varchar(150) DEFAULT NULL,
  `check_step` varchar(100) NOT NULL,
  `pass_yn` char(1) NOT NULL,
  `message` text DEFAULT NULL,
  `created_dt` datetime NOT NULL DEFAULT current_timestamp(),
  `created_by` varchar(100) NOT NULL DEFAULT 'SYSTEM',
  `updated_by` varchar(100) DEFAULT NULL,
  `updated_dt` datetime DEFAULT NULL,
  `deleted_by` varchar(100) DEFAULT NULL,
  `deleted_dt` datetime DEFAULT NULL,
  `change_story` varchar(500) DEFAULT NULL,
  `client_ip` varchar(50) DEFAULT NULL,
  `program_id` varchar(100) DEFAULT NULL,
  `status_code` varchar(50) NOT NULL DEFAULT 'ACTIVE',
  PRIMARY KEY (`log_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `sql_guard_verification_log_backup_20260624`
--

DROP TABLE IF EXISTS `sql_guard_verification_log_backup_20260624`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8mb4 */;
CREATE TABLE `sql_guard_verification_log_backup_20260624` (
  `log_id` bigint(20) NOT NULL DEFAULT 0,
  `query_id` varchar(150) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL,
  `check_step` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL,
  `pass_yn` char(1) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci NOT NULL,
  `message` text CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci DEFAULT NULL,
  `created_at` datetime NOT NULL DEFAULT current_timestamp()
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `system_menu`
--

DROP TABLE IF EXISTS `system_menu`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8mb4 */;
CREATE TABLE `system_menu` (
  `menu_code` varchar(100) NOT NULL,
  `menu_name` varchar(100) NOT NULL,
  `menu_url` varchar(300) DEFAULT NULL,
  `menu_sort_order` int(11) NOT NULL DEFAULT 0,
  `created_dt` datetime NOT NULL DEFAULT current_timestamp(),
  `updated_dt` datetime DEFAULT NULL,
  `created_by` varchar(100) NOT NULL DEFAULT 'SYSTEM',
  `updated_by` varchar(100) DEFAULT NULL,
  `deleted_by` varchar(100) DEFAULT NULL,
  `deleted_dt` datetime DEFAULT NULL,
  `client_ip` varchar(50) DEFAULT NULL,
  `program_id` varchar(100) DEFAULT NULL,
  `status_code` varchar(50) NOT NULL DEFAULT 'ACTIVE',
  PRIMARY KEY (`menu_code`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `system_menu_button`
--

DROP TABLE IF EXISTS `system_menu_button`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8mb4 */;
CREATE TABLE `system_menu_button` (
  `button_code` varchar(100) NOT NULL,
  `menu_code` varchar(100) NOT NULL,
  `button_name` varchar(100) NOT NULL,
  `crud_type` varchar(20) NOT NULL,
  `query_id` varchar(150) NOT NULL,
  `button_sort_order` int(11) NOT NULL DEFAULT 0,
  `created_dt` datetime NOT NULL DEFAULT current_timestamp(),
  `updated_dt` datetime DEFAULT NULL,
  `created_by` varchar(100) NOT NULL DEFAULT 'SYSTEM',
  `updated_by` varchar(100) DEFAULT NULL,
  `deleted_by` varchar(100) DEFAULT NULL,
  `deleted_dt` datetime DEFAULT NULL,
  `client_ip` varchar(50) DEFAULT NULL,
  `program_id` varchar(100) DEFAULT NULL,
  `status_code` varchar(50) NOT NULL DEFAULT 'ACTIVE',
  PRIMARY KEY (`button_code`),
  KEY `fk_system_menu_button_menu` (`menu_code`),
  CONSTRAINT `fk_system_menu_button_menu` FOREIGN KEY (`menu_code`) REFERENCES `system_menu` (`menu_code`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `system_menu_button_crud_permission`
--

DROP TABLE IF EXISTS `system_menu_button_crud_permission`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8mb4 */;
CREATE TABLE `system_menu_button_crud_permission` (
  `permission_id` bigint(20) NOT NULL AUTO_INCREMENT,
  `menu_code` varchar(100) NOT NULL,
  `button_code` varchar(100) NOT NULL,
  `user_role_code` varchar(50) NOT NULL,
  `can_create_yn` char(1) NOT NULL DEFAULT 'N',
  `can_read_yn` char(1) NOT NULL DEFAULT 'N',
  `can_update_yn` char(1) NOT NULL DEFAULT 'N',
  `can_delete_yn` char(1) NOT NULL DEFAULT 'N',
  `can_alter_yn` char(1) NOT NULL DEFAULT 'N',
  `created_dt` datetime NOT NULL DEFAULT current_timestamp(),
  `updated_dt` datetime DEFAULT NULL,
  `created_by` varchar(100) NOT NULL DEFAULT 'SYSTEM',
  `updated_by` varchar(100) DEFAULT NULL,
  `deleted_by` varchar(100) DEFAULT NULL,
  `deleted_dt` datetime DEFAULT NULL,
  `client_ip` varchar(50) DEFAULT NULL,
  `program_id` varchar(100) DEFAULT NULL,
  `status_code` varchar(50) NOT NULL DEFAULT 'ACTIVE',
  PRIMARY KEY (`permission_id`),
  UNIQUE KEY `uk_button_role_permission` (`menu_code`,`button_code`,`user_role_code`),
  KEY `fk_button_permission_button` (`button_code`),
  CONSTRAINT `fk_button_permission_button` FOREIGN KEY (`button_code`) REFERENCES `system_menu_button` (`button_code`),
  CONSTRAINT `fk_button_permission_menu` FOREIGN KEY (`menu_code`) REFERENCES `system_menu` (`menu_code`)
) ENGINE=InnoDB AUTO_INCREMENT=9 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `system_user`
--

DROP TABLE IF EXISTS `system_user`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8mb4 */;
CREATE TABLE `system_user` (
  `user_id` bigint(20) NOT NULL AUTO_INCREMENT,
  `user_login_id` varchar(100) NOT NULL,
  `user_name` varchar(100) NOT NULL,
  `user_role_code` varchar(50) NOT NULL,
  `created_dt` datetime NOT NULL DEFAULT current_timestamp(),
  `updated_dt` datetime DEFAULT NULL,
  `created_by` varchar(100) NOT NULL DEFAULT 'SYSTEM',
  `updated_by` varchar(100) DEFAULT NULL,
  `deleted_by` varchar(100) DEFAULT NULL,
  `deleted_dt` datetime DEFAULT NULL,
  `client_ip` varchar(50) DEFAULT NULL,
  `program_id` varchar(100) DEFAULT NULL,
  `status_code` varchar(50) NOT NULL DEFAULT 'ACTIVE',
  PRIMARY KEY (`user_id`),
  UNIQUE KEY `user_login_id` (`user_login_id`)
) ENGINE=InnoDB AUTO_INCREMENT=3 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `verified_sql_query`
--

DROP TABLE IF EXISTS `verified_sql_query`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8mb4 */;
CREATE TABLE `verified_sql_query` (
  `query_id` varchar(150) NOT NULL,
  `query_name` varchar(200) NOT NULL,
  `crud_type` varchar(20) NOT NULL,
  `sql_text` longtext NOT NULL,
  `verified_yn` char(1) NOT NULL DEFAULT 'N',
  `certified_level` varchar(10) DEFAULT NULL,
  `verification_message` text DEFAULT NULL,
  `created_by` varchar(100) DEFAULT NULL,
  `created_dt` datetime NOT NULL DEFAULT current_timestamp(),
  `verified_by` varchar(100) DEFAULT NULL,
  `verified_at` datetime DEFAULT NULL,
  `updated_dt` datetime DEFAULT NULL,
  `story_programming_rule_pass_yn` char(1) NOT NULL DEFAULT 'N' COMMENT 'Story Programming 이름 규칙 통과 여부',
  `snake_case_pass_yn` char(1) NOT NULL DEFAULT 'N' COMMENT 'snake_case 규칙 통과 여부',
  `table_exists_pass_yn` char(1) NOT NULL DEFAULT 'N' COMMENT '테이블 존재 검증 통과 여부',
  `column_exists_pass_yn` char(1) NOT NULL DEFAULT 'N' COMMENT '컬럼 존재 검증 통과 여부',
  `crud_match_pass_yn` char(1) NOT NULL DEFAULT 'N' COMMENT 'CRUD 타입 일치 검증 통과 여부',
  `where_clause_pass_yn` char(1) NOT NULL DEFAULT 'N' COMMENT 'UPDATE DELETE WHERE 조건 검증 통과 여부',
  `created_user_id` bigint(20) DEFAULT NULL COMMENT '생성 사용자 ID',
  `created_user_login_id` varchar(100) DEFAULT NULL COMMENT '생성 사용자 로그인 ID',
  `created_ip_address` varchar(50) DEFAULT NULL COMMENT '생성 IP 주소',
  `created_program_id` varchar(100) DEFAULT NULL COMMENT '생성 프로그램 ID',
  `updated_user_id` bigint(20) DEFAULT NULL COMMENT '수정 사용자 ID',
  `updated_user_login_id` varchar(100) DEFAULT NULL COMMENT '수정 사용자 로그인 ID',
  `updated_ip_address` varchar(50) DEFAULT NULL COMMENT '수정 IP 주소',
  `updated_program_id` varchar(100) DEFAULT NULL COMMENT '수정 프로그램 ID',
  `deleted_dt` datetime DEFAULT NULL,
  `deleted_user_id` bigint(20) DEFAULT NULL COMMENT '삭제 사용자 ID',
  `deleted_user_login_id` varchar(100) DEFAULT NULL COMMENT '삭제 사용자 로그인 ID',
  `deleted_ip_address` varchar(50) DEFAULT NULL COMMENT '삭제 IP 주소',
  `deleted_program_id` varchar(100) DEFAULT NULL COMMENT '삭제 프로그램 ID',
  `status_code` varchar(50) NOT NULL DEFAULT 'ACTIVE',
  PRIMARY KEY (`query_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;
/*!40101 SET character_set_client = @saved_cs_client */;
/*!40103 SET TIME_ZONE=@OLD_TIME_ZONE */;

/*!40101 SET SQL_MODE=@OLD_SQL_MODE */;
/*!40014 SET FOREIGN_KEY_CHECKS=@OLD_FOREIGN_KEY_CHECKS */;
/*!40014 SET UNIQUE_CHECKS=@OLD_UNIQUE_CHECKS */;
/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
/*!40111 SET SQL_NOTES=@OLD_SQL_NOTES */;

-- Dump completed on 2026-06-28 12:02:18
/*M!999999\- enable the sandbox mode */ 
-- MariaDB dump 10.19  Distrib 10.11.14-MariaDB, for debian-linux-gnu (x86_64)
--
-- Host: localhost    Database: te_ai_platform
-- ------------------------------------------------------
-- Server version	10.11.14-MariaDB-0+deb12u2

/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET @OLD_CHARACTER_SET_RESULTS=@@CHARACTER_SET_RESULTS */;
/*!40101 SET @OLD_COLLATION_CONNECTION=@@COLLATION_CONNECTION */;
/*!40101 SET NAMES utf8mb4 */;
/*!40103 SET @OLD_TIME_ZONE=@@TIME_ZONE */;
/*!40103 SET TIME_ZONE='+00:00' */;
/*!40014 SET @OLD_UNIQUE_CHECKS=@@UNIQUE_CHECKS, UNIQUE_CHECKS=0 */;
/*!40014 SET @OLD_FOREIGN_KEY_CHECKS=@@FOREIGN_KEY_CHECKS, FOREIGN_KEY_CHECKS=0 */;
/*!40101 SET @OLD_SQL_MODE=@@SQL_MODE, SQL_MODE='NO_AUTO_VALUE_ON_ZERO' */;
/*!40111 SET @OLD_SQL_NOTES=@@SQL_NOTES, SQL_NOTES=0 */;
/*!40103 SET TIME_ZONE=@OLD_TIME_ZONE */;

/*!40101 SET SQL_MODE=@OLD_SQL_MODE */;
/*!40014 SET FOREIGN_KEY_CHECKS=@OLD_FOREIGN_KEY_CHECKS */;
/*!40014 SET UNIQUE_CHECKS=@OLD_UNIQUE_CHECKS */;
/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
/*!40111 SET SQL_NOTES=@OLD_SQL_NOTES */;

-- Dump completed on 2026-06-28 12:04:36
/*M!999999\- enable the sandbox mode */ 
-- MariaDB dump 10.19  Distrib 10.11.14-MariaDB, for debian-linux-gnu (x86_64)
--
-- Host: localhost    Database: te_health_companion
-- ------------------------------------------------------
-- Server version	10.11.14-MariaDB-0+deb12u2

/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET @OLD_CHARACTER_SET_RESULTS=@@CHARACTER_SET_RESULTS */;
/*!40101 SET @OLD_COLLATION_CONNECTION=@@COLLATION_CONNECTION */;
/*!40101 SET NAMES utf8mb4 */;
/*!40103 SET @OLD_TIME_ZONE=@@TIME_ZONE */;
/*!40103 SET TIME_ZONE='+00:00' */;
/*!40014 SET @OLD_UNIQUE_CHECKS=@@UNIQUE_CHECKS, UNIQUE_CHECKS=0 */;
/*!40014 SET @OLD_FOREIGN_KEY_CHECKS=@@FOREIGN_KEY_CHECKS, FOREIGN_KEY_CHECKS=0 */;
/*!40101 SET @OLD_SQL_MODE=@@SQL_MODE, SQL_MODE='NO_AUTO_VALUE_ON_ZERO' */;
/*!40111 SET @OLD_SQL_NOTES=@@SQL_NOTES, SQL_NOTES=0 */;

--
-- Table structure for table `ac_action`
--

DROP TABLE IF EXISTS `ac_action`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8mb4 */;
CREATE TABLE `ac_action` (
  `action_id` varchar(30) NOT NULL COMMENT '실행 ID',
  `action_code` varchar(100) NOT NULL COMMENT '실행 코드',
  `decision_id` varchar(30) NOT NULL COMMENT '판단 ID',
  `action_type_code` varchar(50) NOT NULL COMMENT '실행 유형 코드',
  `action_status_code` varchar(50) NOT NULL DEFAULT 'READY' COMMENT '실행 상태 코드',
  `action_target_type_code` varchar(50) DEFAULT NULL COMMENT '실행 대상 유형 코드',
  `action_target_id` varchar(100) DEFAULT NULL COMMENT '실행 대상 ID',
  `action_value` varchar(1000) DEFAULT NULL COMMENT '실행 값',
  `action_message` text DEFAULT NULL COMMENT '실행 메시지',
  `requested_dt` datetime DEFAULT NULL COMMENT '요청일시',
  `started_dt` datetime DEFAULT NULL COMMENT '시작일시',
  `finished_dt` datetime DEFAULT NULL COMMENT '종료일시',
  `result_code` varchar(50) DEFAULT NULL COMMENT '결과 코드',
  `result_message` text DEFAULT NULL COMMENT '결과 메시지',
  `remark` varchar(500) DEFAULT NULL COMMENT '비고',
  `created_dt` datetime NOT NULL DEFAULT current_timestamp(),
  `created_by` varchar(100) NOT NULL DEFAULT 'SYSTEM',
  `updated_dt` datetime NOT NULL DEFAULT current_timestamp() ON UPDATE current_timestamp(),
  `updated_by` varchar(100) NOT NULL DEFAULT 'SYSTEM',
  `deleted_by` varchar(100) DEFAULT NULL,
  `deleted_dt` datetime DEFAULT NULL,
  `program_id` varchar(100) DEFAULT NULL,
  `client_ip` varchar(50) DEFAULT NULL,
  PRIMARY KEY (`action_id`),
  UNIQUE KEY `uk_ac_action_code` (`action_code`),
  KEY `ix_ac_action_decision` (`decision_id`),
  KEY `ix_ac_action_type` (`action_type_code`),
  KEY `ix_ac_action_status` (`action_status_code`),
  CONSTRAINT `fk_ac_action_decision` FOREIGN KEY (`decision_id`) REFERENCES `dc_decision` (`decision_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci COMMENT='실행';
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `at_audit`
--

DROP TABLE IF EXISTS `at_audit`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8mb4 */;
CREATE TABLE `at_audit` (
  `audit_id` varchar(30) NOT NULL COMMENT '감사 ID',
  `audit_code` varchar(100) NOT NULL COMMENT '감사 코드',
  `audit_type_code` varchar(50) NOT NULL COMMENT '감사 유형 코드',
  `business_domain_code` char(2) DEFAULT NULL COMMENT '업무 도메인 코드',
  `target_table_name` varchar(100) DEFAULT NULL COMMENT '대상 테이블명',
  `target_pk_value` varchar(100) DEFAULT NULL COMMENT '대상 PK 값',
  `engine_name` varchar(100) DEFAULT NULL COMMENT '엔진명',
  `rule_id` varchar(30) DEFAULT NULL COMMENT '규칙 ID',
  `evidence_id` varchar(30) DEFAULT NULL COMMENT '근거 ID',
  `decision_id` varchar(30) DEFAULT NULL COMMENT '판단 ID',
  `action_id` varchar(30) DEFAULT NULL COMMENT '실행 ID',
  `before_value_json` longtext CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '변경 전 JSON' CHECK (json_valid(`before_value_json`)),
  `after_value_json` longtext CHARACTER SET utf8mb4 COLLATE utf8mb4_bin DEFAULT NULL COMMENT '변경 후 JSON' CHECK (json_valid(`after_value_json`)),
  `audit_result_code` varchar(50) NOT NULL DEFAULT 'SUCCESS' COMMENT '감사 결과 코드',
  `error_message` text DEFAULT NULL COMMENT '오류 메시지',
  `ai_provider_code` varchar(50) DEFAULT NULL COMMENT 'AI 제공자 코드',
  `ai_model_name` varchar(100) DEFAULT NULL COMMENT 'AI 모델명',
  `ai_used_yn` char(1) NOT NULL DEFAULT 'N' COMMENT 'AI 사용 여부',
  `audit_dt` datetime NOT NULL DEFAULT current_timestamp() COMMENT '감사일시',
  `remark` varchar(500) DEFAULT NULL COMMENT '비고',
  `created_dt` datetime NOT NULL DEFAULT current_timestamp(),
  `created_by` varchar(100) NOT NULL DEFAULT 'SYSTEM',
  `updated_dt` datetime NOT NULL DEFAULT current_timestamp() ON UPDATE current_timestamp(),
  `updated_by` varchar(100) NOT NULL DEFAULT 'SYSTEM',
  `deleted_by` varchar(100) DEFAULT NULL,
  `deleted_dt` datetime DEFAULT NULL,
  `program_id` varchar(100) DEFAULT NULL,
  `client_ip` varchar(50) DEFAULT NULL,
  PRIMARY KEY (`audit_id`),
  UNIQUE KEY `uk_at_audit_code` (`audit_code`),
  KEY `ix_at_audit_target` (`target_table_name`,`target_pk_value`),
  KEY `ix_at_audit_domain` (`business_domain_code`),
  KEY `ix_at_audit_dt` (`audit_dt`),
  KEY `ix_at_audit_decision` (`decision_id`),
  KEY `ix_at_audit_action` (`action_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci COMMENT='감사';
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `dc_decision`
--

DROP TABLE IF EXISTS `dc_decision`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8mb4 */;
CREATE TABLE `dc_decision` (
  `decision_id` varchar(30) NOT NULL COMMENT '판단 ID',
  `decision_code` varchar(100) NOT NULL COMMENT '판단 코드',
  `user_id` varchar(100) NOT NULL COMMENT '사용자 ID',
  `decision_type_code` varchar(50) NOT NULL COMMENT '판단 유형 코드',
  `decision_result_code` varchar(50) NOT NULL COMMENT '판단 결과 코드',
  `priority_score` decimal(10,2) DEFAULT NULL COMMENT '우선순위 점수',
  `confidence_score` decimal(10,2) DEFAULT NULL COMMENT '신뢰도 점수',
  `rule_id` varchar(30) DEFAULT NULL COMMENT '대표 규칙 ID',
  `evidence_id` varchar(30) DEFAULT NULL COMMENT '대표 근거 ID',
  `decision_summary` varchar(1000) DEFAULT NULL COMMENT '판단 요약',
  `decision_dt` datetime NOT NULL DEFAULT current_timestamp() COMMENT '판단일시',
  `status_code` varchar(30) NOT NULL DEFAULT 'ACTIVE' COMMENT '상태 코드',
  `remark` varchar(500) DEFAULT NULL COMMENT '비고',
  `created_dt` datetime NOT NULL DEFAULT current_timestamp(),
  `created_by` varchar(100) NOT NULL DEFAULT 'SYSTEM',
  `updated_dt` datetime NOT NULL DEFAULT current_timestamp() ON UPDATE current_timestamp(),
  `updated_by` varchar(100) NOT NULL DEFAULT 'SYSTEM',
  `deleted_by` varchar(100) DEFAULT NULL,
  `deleted_dt` datetime DEFAULT NULL,
  `program_id` varchar(100) DEFAULT NULL,
  `client_ip` varchar(50) DEFAULT NULL,
  PRIMARY KEY (`decision_id`),
  UNIQUE KEY `uk_dc_decision_code` (`decision_code`),
  KEY `ix_dc_decision_user` (`user_id`),
  KEY `ix_dc_decision_type` (`decision_type_code`),
  KEY `ix_dc_decision_result` (`decision_result_code`),
  KEY `ix_dc_decision_dt` (`decision_dt`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci COMMENT='판단';
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `dc_decision_detail`
--

DROP TABLE IF EXISTS `dc_decision_detail`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8mb4 */;
CREATE TABLE `dc_decision_detail` (
  `decision_detail_id` varchar(30) NOT NULL COMMENT '판단 상세 ID',
  `decision_id` varchar(30) NOT NULL COMMENT '판단 ID',
  `rule_id` varchar(30) DEFAULT NULL COMMENT '적용 규칙 ID',
  `evidence_id` varchar(30) DEFAULT NULL COMMENT '적용 근거 ID',
  `input_field_code` varchar(100) DEFAULT NULL COMMENT '입력 필드 코드',
  `input_value` varchar(500) DEFAULT NULL COMMENT '입력 값',
  `condition_result_code` varchar(30) DEFAULT NULL COMMENT '조건 결과 코드',
  `detail_summary` varchar(1000) DEFAULT NULL COMMENT '상세 요약',
  `sort_no` int(11) NOT NULL DEFAULT 0 COMMENT '정렬번호',
  `remark` varchar(500) DEFAULT NULL COMMENT '비고',
  `created_dt` datetime NOT NULL DEFAULT current_timestamp(),
  `created_by` varchar(100) NOT NULL DEFAULT 'SYSTEM',
  `updated_dt` datetime NOT NULL DEFAULT current_timestamp() ON UPDATE current_timestamp(),
  `updated_by` varchar(100) NOT NULL DEFAULT 'SYSTEM',
  `deleted_by` varchar(100) DEFAULT NULL,
  `deleted_dt` datetime DEFAULT NULL,
  `program_id` varchar(100) DEFAULT NULL,
  `client_ip` varchar(50) DEFAULT NULL,
  PRIMARY KEY (`decision_detail_id`),
  KEY `ix_dc_detail_decision` (`decision_id`),
  KEY `ix_dc_detail_rule` (`rule_id`),
  KEY `ix_dc_detail_evidence` (`evidence_id`),
  CONSTRAINT `fk_dc_detail_decision` FOREIGN KEY (`decision_id`) REFERENCES `dc_decision` (`decision_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci COMMENT='판단 상세';
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Table structure for table `fb_feedback`
--

DROP TABLE IF EXISTS `fb_feedback`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!40101 SET character_set_client = utf8mb4 */;
CREATE TABLE `fb_feedback` (
  `feedback_id` varchar(30) NOT NULL COMMENT '피드백 ID',
  `feedback_code` varchar(100) NOT NULL COMMENT '피드백 코드',
  `user_id` varchar(100) NOT NULL COMMENT '사용자 ID',
  `decision_id` varchar(30) DEFAULT NULL COMMENT '판단 ID',
  `action_id` varchar(30) DEFAULT NULL COMMENT '실행 ID',
  `feedback_type_code` varchar(50) NOT NULL COMMENT '피드백 유형 코드',
  `rating_score` decimal(5,2) DEFAULT NULL COMMENT '평점',
  `feedback_message` text DEFAULT NULL COMMENT '피드백 메시지',
  `feedback_dt` datetime NOT NULL DEFAULT current_timestamp() COMMENT '피드백일시',
  `status_code` varchar(30) NOT NULL DEFAULT 'ACTIVE' COMMENT '상태 코드',
  `remark` varchar(500) DEFAULT NULL COMMENT '비고',
  `created_dt` datetime NOT NULL DEFAULT current_timestamp(),
  `created_by` varchar(100) NOT NULL DEFAULT 'SYSTEM',
  `updated_dt` datetime NOT NULL DEFAULT current_timestamp() ON UPDATE current_timestamp(),
  `updated_by` varchar(100) NOT NULL DEFAULT 'SYSTEM',
  `deleted_by` varchar(100) DEFAULT NULL,
  `deleted_dt` datetime DEFAULT NULL,
  `program_id` varchar(100) DEFAULT NULL,
  `client_ip` varchar(50) DEFAULT NULL,
  PRIMARY KEY (`feedback_id`),
  UNIQUE KEY `uk_fb_feedback_code` (`feedback_code`),
  KEY `ix_fb_feedback_user` (`user_id`),
  KEY `ix_fb_feedback_decision` (`decision_id`),
  KEY `ix_fb_feedback_action` (`action_id`),
  KEY `ix_fb_feedback_type` (`feedback_type_code`),
  CONSTRAINT `fk_fb_feedback_action` FOREIGN KEY (`action_id`) REFERENCES `ac_action` (`action_id`),
  CONSTRAINT `fk_fb_feedback_decision` FOREIGN KEY (`decision_id`) REFERENCES `dc_decision` (`decision_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci COMMENT='피드백';
/*!40101 SET character_set_client = @saved_cs_client */;
/*!40103 SET TIME_ZONE=@OLD_TIME_ZONE */;

/*!40101 SET SQL_MODE=@OLD_SQL_MODE */;
/*!40014 SET FOREIGN_KEY_CHECKS=@OLD_FOREIGN_KEY_CHECKS */;
/*!40014 SET UNIQUE_CHECKS=@OLD_UNIQUE_CHECKS */;
/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
/*!40111 SET SQL_NOTES=@OLD_SQL_NOTES */;

-- Dump completed on 2026-06-28 12:05:09

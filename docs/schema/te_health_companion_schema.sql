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

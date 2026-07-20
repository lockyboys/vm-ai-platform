/*
File Name : repository_data_type_patch_20260720.sql
Purpose   : One-time hardcoded Repository Data Type Migration Patch Batch.
Method    : Each PATCH keeps the fixed Backup -> Transaction Copy -> Count Verify
            -> ALTER TABLE -> Result Verify sequence.
*/


/* =============================================================================
PATCH 002 START
Database : te_health_companion
Table    : dc_decision
Backup   : dc_decision_backup_20260720_01
============================================================================= */

-- 1. 변경 전 백업
CREATE TABLE `te_health_companion`.`dc_decision_backup_20260720_01`
LIKE `te_health_companion`.`dc_decision`;

START TRANSACTION;

INSERT INTO `te_health_companion`.`dc_decision_backup_20260720_01`
SELECT *
FROM `te_health_companion`.`dc_decision`;

COMMIT;


-- 2. 백업 검증
SELECT
    (SELECT COUNT(*)
       FROM `te_health_companion`.`dc_decision`) AS original_count,
    (SELECT COUNT(*)
       FROM `te_health_companion`.`dc_decision_backup_20260720_01`) AS backup_count;


-- 3. ALTER TABLE 문 실행
ALTER TABLE `te_health_companion`.`dc_decision`
    MODIFY COLUMN `decision_code` VARCHAR(99) NOT NULL
        COMMENT '판단 코드',
    MODIFY COLUMN `user_id` VARCHAR(99) NOT NULL
        COMMENT '사용자 ID',
    MODIFY COLUMN `decision_type_code` VARCHAR(99) NOT NULL
        COMMENT '판단 유형 코드',
    MODIFY COLUMN `decision_result_code` VARCHAR(99) NOT NULL
        COMMENT '판단 결과 코드',
    MODIFY COLUMN `priority_score` DECIMAL(10,4) DEFAULT NULL
        COMMENT '우선순위 점수',
    MODIFY COLUMN `confidence_score` DECIMAL(10,4) DEFAULT NULL
        COMMENT '신뢰도 점수',
    MODIFY COLUMN `rule_id` VARCHAR(99) DEFAULT NULL
        COMMENT '대표 규칙 ID',
    MODIFY COLUMN `evidence_id` VARCHAR(99) DEFAULT NULL
        COMMENT '대표 근거 ID',
    MODIFY COLUMN `decision_summary` VARCHAR(2000) DEFAULT NULL
        COMMENT '판단 요약',
    MODIFY COLUMN `status_code` VARCHAR(99) NOT NULL DEFAULT 'ACTIVE'
        COMMENT '상태 코드',
    MODIFY COLUMN `remark` VARCHAR(2000) DEFAULT NULL
        COMMENT '비고';


-- 4. 변경 결과 확인
SHOW CREATE TABLE `te_health_companion`.`dc_decision`;

SELECT COUNT(*) AS row_count
FROM `te_health_companion`.`dc_decision`;

/* =============================================================================
PATCH 002 END
============================================================================= */

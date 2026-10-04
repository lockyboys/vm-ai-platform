/* Append MongoDB payload mapping to existing MariaDB table comments. Existing comments are preserved. */
SET NAMES utf8mb4;
DROP PROCEDURE IF EXISTS append_mongodb_payload_comment;
DELIMITER $$
CREATE PROCEDURE append_mongodb_payload_comment(
    IN p_schema_name VARCHAR(64),
    IN p_table_name VARCHAR(64),
    IN p_collection_name VARCHAR(128),
    IN p_mongodb_role VARCHAR(64),
    IN p_payload_description VARCHAR(1000)
)
BEGIN
    DECLARE v_existing_comment LONGTEXT DEFAULT '';
    DECLARE v_new_comment LONGTEXT;
    DECLARE v_sql LONGTEXT;
    SELECT COALESCE(TABLE_COMMENT, '') INTO v_existing_comment
      FROM information_schema.TABLES
     WHERE TABLE_SCHEMA = p_schema_name AND TABLE_NAME = p_table_name;
    IF INSTR(v_existing_comment, '[MONGODB_PAYLOAD]') = 0 THEN
        SET v_new_comment = CONCAT(v_existing_comment,
            CASE WHEN v_existing_comment = '' THEN '' ELSE CHAR(10, 10) END,
            '[MONGODB_PAYLOAD] Collection: ', p_collection_name,
            '; MongoDB Role: ', p_mongodb_role,
            '; MariaDB Role: INDEX_ONLY; ', p_payload_description);
        SET v_sql = CONCAT('ALTER TABLE `', p_schema_name, '`.`', p_table_name, '` COMMENT = ', QUOTE(v_new_comment));
        PREPARE stmt FROM v_sql;
        EXECUTE stmt;
        DEALLOCATE PREPARE stmt;
    END IF;
END$$
DELIMITER ;
CALL append_mongodb_payload_comment('te_common','cm_verified_sql_query','cm_verified_sql_query_payload','COMMON','MariaDB에는 query_id·검증상태를 유지하고 상세 SQL payload는 MongoDB에 저장한다.');
CALL append_mongodb_payload_comment('te_common','model_history','model_history_payload','COMMON','MariaDB에는 모델 이력 색인을 유지하고 features 상세값은 MongoDB에 저장한다.');
CALL append_mongodb_payload_comment('te_common','health_report','health_report_payload','HEALTH','MariaDB에는 건강 리포트 색인을 유지하고 report_content·change_story는 MongoDB에 저장한다.');
CALL append_mongodb_payload_comment('te_common','cm_repository','cm_repository_payload','COMMON','MariaDB에는 Repository 식별·분류를 유지하고 data_json·footer_json·code_description은 MongoDB에 저장한다.');
CALL append_mongodb_payload_comment('te_common','cm_storage_repository','cm_storage_repository_payload','COMMON','MariaDB에는 Storage 식별·정책을 유지하고 상세 payload는 MongoDB에 저장한다.');
CALL append_mongodb_payload_comment('te_common','sql_guard_execution_log','sql_guard_execution_log_payload','HEALTH','MariaDB에는 SQL 실행 색인을 유지하고 error_message 상세값은 MongoDB에 저장한다.');
CALL append_mongodb_payload_comment('te_common','sql_guard_verification_log','sql_guard_verification_log_payload','HEALTH','MariaDB에는 검증 단계 색인을 유지하고 message·change_story는 MongoDB에 저장한다.');
CALL append_mongodb_payload_comment('te_common','cron_logs','cron_logs_payload','COMMON','MariaDB에는 Cron 실행 색인을 유지하고 message 상세값은 MongoDB에 저장한다.');
CALL append_mongodb_payload_comment('te_common','cm_code_inspection_result','cm_code_inspection_result_payload','COMMON','MariaDB에는 검사 결과 색인을 유지하고 related_codes·message는 MongoDB에 저장한다.');
CALL append_mongodb_payload_comment('te_common','pipeline_results','pipeline_results_payload','COMMON','MariaDB에는 Pipeline 결과 색인을 유지하고 data_json은 MongoDB에 저장한다.');
CALL append_mongodb_payload_comment('te_story_platform','sp_impact_analysis_result','sp_impact_analysis_result_payload','HEALTH','MariaDB에는 영향분석 색인을 유지하고 변경·영향 분석 상세값은 MongoDB에 저장한다.');
DROP PROCEDURE IF EXISTS append_mongodb_payload_comment;
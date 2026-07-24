/*
 * Stored Procedure and Verified Query registration.
 * No table or column definition is changed.
 */
USE te_story_platform;

DROP PROCEDURE IF EXISTS sp_register_repository_object;
DELIMITER $$

CREATE PROCEDURE sp_register_repository_object(IN p_request_json JSON)
BEGIN
    DECLARE v_object_id VARCHAR(99);
    DECLARE v_object_code VARCHAR(99);
    DECLARE v_object_name VARCHAR(150);
    DECLARE v_business_code VARCHAR(99);
    DECLARE v_domain_code VARCHAR(99);
    DECLARE v_object_type_code VARCHAR(99);
    DECLARE v_object_description VARCHAR(2000);
    DECLARE v_object_level INT;
    DECLARE v_sort_no INT;
    DECLARE v_status_code VARCHAR(99);
    DECLARE v_active_yn CHAR(1);
    DECLARE v_created_by VARCHAR(99);
    DECLARE v_program_id VARCHAR(99);
    DECLARE v_client_ip VARCHAR(99);
    DECLARE v_registered_yn CHAR(1) DEFAULT 'N';

    IF p_request_json IS NULL OR JSON_VALID(p_request_json) = 0 THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Repository Object request_json is required.';
    END IF;

    SET v_object_id = JSON_UNQUOTE(JSON_EXTRACT(p_request_json, '$.object_id'));
    SET v_object_code = JSON_UNQUOTE(JSON_EXTRACT(p_request_json, '$.object_code'));
    SET v_object_name = JSON_UNQUOTE(JSON_EXTRACT(p_request_json, '$.object_name'));
    SET v_business_code = JSON_UNQUOTE(JSON_EXTRACT(p_request_json, '$.business_code'));
    SET v_domain_code = JSON_UNQUOTE(JSON_EXTRACT(p_request_json, '$.domain_code'));
    SET v_object_type_code = JSON_UNQUOTE(JSON_EXTRACT(p_request_json, '$.object_type_code'));
    SET v_object_description = JSON_UNQUOTE(JSON_EXTRACT(p_request_json, '$.object_description'));
    SET v_object_level = CAST(JSON_UNQUOTE(JSON_EXTRACT(p_request_json, '$.object_level')) AS UNSIGNED);
    SET v_sort_no = CAST(JSON_UNQUOTE(JSON_EXTRACT(p_request_json, '$.sort_no')) AS UNSIGNED);
    SET v_status_code = JSON_UNQUOTE(JSON_EXTRACT(p_request_json, '$.status_code'));
    SET v_active_yn = JSON_UNQUOTE(JSON_EXTRACT(p_request_json, '$.active_yn'));
    SET v_created_by = JSON_UNQUOTE(JSON_EXTRACT(p_request_json, '$.created_by'));
    SET v_program_id = JSON_UNQUOTE(JSON_EXTRACT(p_request_json, '$.program_id'));
    SET v_client_ip = JSON_UNQUOTE(JSON_EXTRACT(p_request_json, '$.client_ip'));

    IF v_object_id IS NULL OR v_object_code IS NULL OR v_object_name IS NULL
       OR v_business_code IS NULL OR v_domain_code IS NULL OR v_object_type_code IS NULL
       OR v_object_level IS NULL OR v_status_code IS NULL OR v_active_yn IS NULL
       OR v_created_by IS NULL OR v_program_id IS NULL THEN
        SIGNAL SQLSTATE '45000' SET MESSAGE_TEXT = 'Repository Object request is missing required fields.';
    END IF;

    INSERT INTO sp_object
    (
        object_id, object_code, object_name, business_code, domain_code,
        object_type_code, object_description, object_level, sort_no,
        status_code, active_yn, created_by, updated_by, program_id, client_ip
    )
    SELECT
        v_object_id, v_object_code, v_object_name, v_business_code, v_domain_code,
        v_object_type_code, v_object_description, v_object_level, COALESCE(v_sort_no, 0),
        v_status_code, v_active_yn, v_created_by, v_created_by, v_program_id, v_client_ip
    WHERE NOT EXISTS
    (
        SELECT 1 FROM sp_object
        WHERE object_code = v_object_code
          AND deleted_dt IS NULL
    );

    IF ROW_COUNT() = 1 THEN
        SET v_registered_yn = 'Y';
    END IF;

    SELECT
        object_id,
        object_code,
        v_registered_yn AS registered_yn
    FROM sp_object
    WHERE object_code = v_object_code
      AND deleted_dt IS NULL
    LIMIT 1;
END$$

DELIMITER ;

USE te_common;

START TRANSACTION;

SET @query_id = 'SP_RP_SQL_QUERY_20260725_REGISTER_REPOSITORY_OBJECT_00001';
SET @procedure_name = 'sp_register_repository_object';
SET @program_id = 'REGISTER_ACTION_METADATA_20260725';
SET @client_ip = '127.0.0.1';

INSERT INTO cm_verified_sql_query
(
    query_id, query_name, query_description, crud_type, sql_text,
    verified_yn, certified_level_code, verification_description,
    created_by, verified_by, verified_dt,
    story_programming_rule_pass_yn, snake_case_pass_yn,
    table_exists_pass_yn, column_exists_pass_yn, crud_match_pass_yn,
    where_clause_pass_yn, status_code, program_id, client_ip
)
VALUES
(
    @query_id,
    'Repository Object 등록 Stored Procedure',
    JSON_OBJECT(
        'procedure_name', @procedure_name,
        'parameter_definition', JSON_OBJECT(
            'type', 'object',
            'required', JSON_ARRAY(
                'object_id', 'object_code', 'object_name', 'business_code',
                'domain_code', 'object_type_code', 'object_level',
                'status_code', 'active_yn', 'created_by', 'program_id'
            )
        ),
        'result_definition', JSON_OBJECT(
            'type', 'object',
            'required', JSON_ARRAY('object_id', 'object_code', 'registered_yn')
        ),
        'database_role', 'STORY_PLATFORM',
        'transaction_required_yn', 'Y',
        'rollback_policy', 'ROLLBACK_ON_ERROR',
        'timeout_seconds', 30
    ),
    'PROCEDURE',
    CONCAT('CALL ', @procedure_name, '(?)'),
    'Y', 'A',
    'Action Metadata Runtime 전용 Procedure 계약 검증 완료.',
    'SYSTEM', 'SYSTEM', CURRENT_TIMESTAMP,
    'Y', 'Y', 'Y', 'Y', 'Y', 'Y',
    'ACTIVE', @program_id, @client_ip
)
ON DUPLICATE KEY UPDATE
    query_name = VALUES(query_name),
    query_description = VALUES(query_description),
    crud_type = VALUES(crud_type),
    sql_text = VALUES(sql_text),
    verified_yn = VALUES(verified_yn),
    certified_level_code = VALUES(certified_level_code),
    verification_description = VALUES(verification_description),
    verified_by = VALUES(verified_by),
    verified_dt = VALUES(verified_dt),
    story_programming_rule_pass_yn = VALUES(story_programming_rule_pass_yn),
    snake_case_pass_yn = VALUES(snake_case_pass_yn),
    table_exists_pass_yn = VALUES(table_exists_pass_yn),
    column_exists_pass_yn = VALUES(column_exists_pass_yn),
    crud_match_pass_yn = VALUES(crud_match_pass_yn),
    where_clause_pass_yn = VALUES(where_clause_pass_yn),
    status_code = VALUES(status_code),
    updated_dt = CURRENT_TIMESTAMP,
    updated_by = VALUES(created_by),
    program_id = VALUES(program_id),
    client_ip = VALUES(client_ip);

SELECT query_id, query_name, query_description, sql_text
FROM cm_verified_sql_query
WHERE query_id = @query_id
  AND verified_yn = 'Y'
  AND status_code = 'ACTIVE'
  AND deleted_dt IS NULL;

COMMIT;

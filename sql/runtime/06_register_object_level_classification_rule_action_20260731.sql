/*
 * Object Level 기본 분류 Rule Action의 실행 Procedure.
 * 테이블·컬럼 구조를 변경하지 않는다.
 */
USE te_common;

DROP PROCEDURE IF EXISTS sp_resolve_object_level_classification;
DELIMITER $$

CREATE PROCEDURE sp_resolve_object_level_classification(IN p_request_json JSON)
BEGIN
    DECLARE v_default_object_level INT;

    IF p_request_json IS NOT NULL AND JSON_VALID(p_request_json) = 0 THEN
        SIGNAL SQLSTATE '45000'
            SET MESSAGE_TEXT = 'Object Level classification request must be valid JSON.';
    END IF;

    SELECT CAST(
        JSON_UNQUOTE(JSON_EXTRACT(common_code_json, '$.default_object_level'))
        AS UNSIGNED
    )
    INTO v_default_object_level
    FROM cm_common_code
    WHERE group_code = 'ACTION_TYPE'
      AND code = 'OBJECT_LEVEL_CLASSIFICATION'
      AND status_code = 'ACTIVE'
      AND deleted_dt IS NULL
    LIMIT 1;

    IF v_default_object_level IS NULL THEN
        SIGNAL SQLSTATE '45000'
            SET MESSAGE_TEXT = 'Object Level default Action Metadata not found.';
    END IF;

    SELECT
        r.rule_id,
        r.rule_code,
        v_default_object_level AS default_object_level,
        'DEFAULT' AS resolution_source
    FROM rl_rule r
    WHERE r.rule_code = 'RL_OBJECT_LEVEL_CLASSIFICATION'
      AND r.status_code = 'ACTIVE'
      AND r.deleted_dt IS NULL
    LIMIT 1;
END$$

DELIMITER ;

SELECT
    r.rule_id,
    r.rule_code,
    a.rule_action_id,
    a.action_type_code,
    JSON_UNQUOTE(JSON_EXTRACT(a.action_value, '$.verified_query_id')) AS verified_query_id,
    q.query_name,
    JSON_UNQUOTE(JSON_EXTRACT(q.query_description, '$.procedure_name')) AS procedure_name
FROM rl_rule r
LEFT JOIN rl_rule_action a
  ON a.rule_id = r.rule_id
 AND a.status_code = 'ACTIVE'
 AND a.deleted_dt IS NULL
LEFT JOIN cm_verified_sql_query q
  ON q.query_id = JSON_UNQUOTE(JSON_EXTRACT(a.action_value, '$.verified_query_id'))
 AND q.status_code = 'ACTIVE'
 AND q.deleted_dt IS NULL
WHERE r.rule_code = 'RL_OBJECT_LEVEL_CLASSIFICATION'
  AND r.status_code = 'ACTIVE'
  AND r.deleted_dt IS NULL;

/*
 * 20260802 | OpenAI | Object Level Rule Action Procedure가 선택된 Rule Action
 * 실행 문맥을 사용하도록 정정함.
 * 테이블·컬럼 구조는 변경하지 않는다.
 */
USE te_common;

DROP PROCEDURE IF EXISTS sp_resolve_object_level_classification;
DELIMITER $$

CREATE PROCEDURE sp_resolve_object_level_classification(IN p_request_json JSON)
BEGIN
    /* Repository key columns use two legacy collations; bind each local key accordingly. */
    DECLARE v_rule_id VARCHAR(99) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci;
    DECLARE v_rule_action_id VARCHAR(99) CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci;
    DECLARE v_action_type_code VARCHAR(99) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
    DECLARE v_action_type_group_code VARCHAR(99) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
    DECLARE v_default_object_level INT;
    DECLARE v_selected_rule_id VARCHAR(99);
    DECLARE v_selected_rule_code VARCHAR(99);
    DECLARE v_selected_rule_action_id VARCHAR(99);
    DECLARE v_selected_action_type_code VARCHAR(99);
    DECLARE v_selected_condition_id VARCHAR(99);

    IF p_request_json IS NULL
       OR JSON_VALID(p_request_json) = 0
       OR JSON_TYPE(p_request_json) <> 'OBJECT' THEN
        SIGNAL SQLSTATE '45000'
            SET MESSAGE_TEXT = 'Object Level classification request must be a valid JSON object.';
    END IF;

    SET v_rule_id = NULLIF(
        TRIM(JSON_UNQUOTE(JSON_EXTRACT(p_request_json, '$.rule_id'))),
        ''
    );
    SET v_rule_action_id = NULLIF(
        TRIM(JSON_UNQUOTE(JSON_EXTRACT(p_request_json, '$.rule_action_id'))),
        ''
    );
    SET v_action_type_code = NULLIF(
        TRIM(JSON_UNQUOTE(JSON_EXTRACT(p_request_json, '$.action_type_code'))),
        ''
    );
    SET v_action_type_group_code = NULLIF(
        TRIM(JSON_UNQUOTE(JSON_EXTRACT(p_request_json, '$.action_type_group_code'))),
        ''
    );

    IF v_rule_id IS NULL
       OR v_rule_action_id IS NULL
       OR v_action_type_code IS NULL
       OR v_action_type_group_code IS NULL THEN
        SIGNAL SQLSTATE '45000'
            SET MESSAGE_TEXT = 'Object Level classification Rule Action context is required.';
    END IF;

    SELECT
        CAST(
            COALESCE(
                NULLIF(
                    JSON_UNQUOTE(
                        JSON_EXTRACT(a.action_value, '$.default_object_level')
                    ),
                    ''
                ),
                NULLIF(
                    JSON_UNQUOTE(
                        JSON_EXTRACT(c.common_code_json, '$.default_object_level')
                    ),
                    ''
                )
            )
            AS UNSIGNED
        ),
        r.rule_id,
        r.rule_code,
        a.rule_action_id,
        a.action_type_code,
        NULLIF(
            TRIM(JSON_UNQUOTE(JSON_EXTRACT(a.action_value, '$.condition_id'))),
            ''
        )
    INTO
        v_default_object_level,
        v_selected_rule_id,
        v_selected_rule_code,
        v_selected_rule_action_id,
        v_selected_action_type_code,
        v_selected_condition_id
    FROM rl_rule r
    JOIN rl_rule_action a
      ON a.rule_id = r.rule_id
     AND a.status_code = 'ACTIVE'
     AND a.deleted_dt IS NULL
    JOIN cm_common_code c
      ON c.group_code = v_action_type_group_code
     AND c.code = a.action_type_code
     AND c.status_code = 'ACTIVE'
     AND c.deleted_dt IS NULL
    WHERE r.rule_id = v_rule_id
      AND a.rule_action_id = v_rule_action_id
      AND a.action_type_code = v_action_type_code
      AND r.status_code = 'ACTIVE'
      AND r.deleted_dt IS NULL
    LIMIT 1;

    IF v_selected_rule_id IS NULL
       OR v_default_object_level IS NULL
       OR v_default_object_level <= 0 THEN
        SIGNAL SQLSTATE '45000'
            SET MESSAGE_TEXT = 'Active Object Level Rule Action metadata not found.';
    END IF;

    IF v_selected_condition_id IS NOT NULL THEN
        SIGNAL SQLSTATE '45000'
            SET MESSAGE_TEXT = 'Object Level classification Procedure may execute only the Negative Default Action.';
    END IF;

    SELECT
        v_selected_rule_id AS rule_id,
        v_selected_rule_code AS rule_code,
        v_selected_rule_action_id AS rule_action_id,
        v_selected_action_type_code AS action_type_code,
        v_default_object_level AS default_object_level,
        'DEFAULT' AS resolution_source;
END$$

DELIMITER ;

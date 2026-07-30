/*
 * Register the Object Level default policy in the Rule Repository.
 *
 * Rule ID must be issued by IdentifierEngine using the RL_RULE Object.
 * This SQL performs no schema change and never constructs an identifier.
 */
USE te_common;

START TRANSACTION;

SELECT
    rule_id,
    rule_code,
    rule_name,
    rule_description,
    remark,
    status_code,
    version_num
FROM rl_rule
WHERE rule_code = 'RL_OBJECT_LEVEL_CLASSIFICATION'
  AND deleted_dt IS NULL;

COMMIT;

/*
 * Apply with:
 *   python -m tools.register_object_level_classification_rule
 *
 * Registered policy:
 *   An Object target that has no explicit Object Level Rule entry defaults to Level 4.
 */

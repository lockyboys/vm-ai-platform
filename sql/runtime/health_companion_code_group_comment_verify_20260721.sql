-- Resume verification after successful statements 1-23
SELECT
 (SELECT COUNT(*) FROM te_common.rl_rule_action r
  LEFT JOIN te_common.cm_common_code c
    ON c.group_code='ACTION_TYPE' AND c.code=r.action_type_code COLLATE utf8mb4_unicode_ci
  WHERE c.code IS NULL) AS invalid_rule_action_type_count,
 (SELECT COUNT(*) FROM te_health_companion.ac_action a
  LEFT JOIN te_common.cm_common_code c
    ON c.group_code='ACTION_TYPE' AND c.code=a.action_type_code COLLATE utf8mb4_unicode_ci
  WHERE c.code IS NULL) AS invalid_action_type_count,
 (SELECT COUNT(*) FROM te_health_companion.ac_action a
  LEFT JOIN te_common.cm_common_code c
    ON c.group_code='CM_JOB_STATUS' AND c.code=a.result_code COLLATE utf8mb4_unicode_ci
  WHERE a.result_code IS NOT NULL AND c.code IS NULL) AS invalid_result_count,
 (SELECT COUNT(*) FROM te_health_companion.at_audit a
  LEFT JOIN te_common.cm_common_code c
    ON c.group_code='CM_JOB_STATUS' AND c.code=a.audit_result_code COLLATE utf8mb4_unicode_ci
  WHERE c.code IS NULL) AS invalid_audit_result_count,
 (SELECT COUNT(*) FROM te_health_companion.at_audit a
  LEFT JOIN te_common.cm_common_code c
    ON c.group_code='AI_PROVIDER' AND c.code=a.ai_provider_code COLLATE utf8mb4_unicode_ci
  WHERE a.ai_provider_code IS NOT NULL AND c.code IS NULL) AS invalid_ai_provider_count,
 (SELECT COUNT(*) FROM te_health_companion.dc_decision d
  LEFT JOIN te_common.cm_common_code c
    ON c.group_code='DECISION_TYPE' AND c.code=d.decision_type_code COLLATE utf8mb4_unicode_ci
  WHERE c.code IS NULL) AS invalid_decision_type_count;

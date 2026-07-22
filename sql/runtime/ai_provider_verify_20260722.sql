-- AI_PROVIDER Repository verification 20260722
-- Decision: no provider code is registered until an actual external AI call is evidenced.
-- API-key presence or planned integration is not sufficient evidence.

SELECT
    g.group_code,
    g.group_name,
    g.group_description,
    g.status_code,
    COUNT(c.code) AS registered_provider_count
FROM te_common.cm_common_code_group g
LEFT JOIN te_common.cm_common_code c
  ON c.group_code = g.group_code
WHERE g.group_code = 'AI_PROVIDER'
GROUP BY g.group_code, g.group_name, g.group_description, g.status_code;

SELECT
    COUNT(*) AS ai_used_count,
    SUM(CASE WHEN ai_used_yn = 'Y' AND ai_provider_code IS NULL THEN 1 ELSE 0 END)
        AS missing_provider_when_ai_used_count,
    SUM(CASE WHEN ai_provider_code IS NOT NULL AND ai_used_yn <> 'Y' THEN 1 ELSE 0 END)
        AS provider_without_ai_use_count
FROM te_health_companion.at_audit;

SELECT DISTINCT ai_provider_code, ai_model_name
FROM te_health_companion.at_audit
WHERE ai_used_yn = 'Y'
   OR ai_provider_code IS NOT NULL
   OR ai_model_name IS NOT NULL
ORDER BY ai_provider_code, ai_model_name;

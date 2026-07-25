/*
 * Read-only baseline for Action Metadata Runtime COMMENT changes.
 * Run this first. Do not execute ALTER TABLE COMMENT until the result is reviewed.
 */

SELECT
    table_schema,
    table_name,
    table_comment
FROM information_schema.tables
WHERE table_schema = 'te_common'
  AND table_name IN (
      'cm_common_code',
      'cm_verified_sql_query',
      'rl_rule_action'
  )
ORDER BY table_name;

SELECT
    table_schema,
    table_name,
    column_name,
    column_type,
    is_nullable,
    column_default,
    column_comment
FROM information_schema.columns
WHERE table_schema = 'te_common'
  AND (
      (table_name = 'cm_common_code'
       AND column_name = 'common_code_json')
   OR (table_name = 'cm_verified_sql_query'
       AND column_name IN ('query_description', 'sql_text'))
   OR (table_name = 'rl_rule_action'
       AND column_name = 'action_value')
  )
ORDER BY table_name, ordinal_position;

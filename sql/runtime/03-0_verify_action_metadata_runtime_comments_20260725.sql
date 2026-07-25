/*
 * Read-only preflight for Action Metadata Runtime COMMENT changes.
 *
 * All target definitions must return PASS before the COMMENT DDL is reviewed.
 * This query never changes the database and does not grant execution approval.
 */

WITH expected_columns AS (
    SELECT 'cm_common_code' AS table_name,
           'common_code_json' AS column_name,
           'longtext' AS column_type,
           'YES' AS is_nullable,
           CAST(NULL AS CHAR(1)) AS column_default,
           'utf8mb4' AS character_set_name,
           'utf8mb4_unicode_ci' AS collation_name,
           '' AS extra
    UNION ALL
    SELECT 'cm_verified_sql_query', 'query_description', 'varchar(2000)', 'YES',
           CAST(NULL AS CHAR(1)), 'utf8mb4', 'utf8mb4_general_ci', ''
    UNION ALL
    SELECT 'cm_verified_sql_query', 'sql_text', 'longtext', 'NO',
           CAST(NULL AS CHAR(1)), 'utf8mb4', 'utf8mb4_general_ci', ''
    UNION ALL
    SELECT 'rl_rule_action', 'action_value', 'varchar(2000)', 'YES',
           CAST(NULL AS CHAR(1)), 'utf8mb4', 'utf8mb4_general_ci', ''
)
SELECT
    c.table_schema,
    c.table_name,
    c.column_name,
    c.column_type,
    c.is_nullable,
    c.column_default,
    c.character_set_name,
    c.collation_name,
    c.extra,
    c.column_comment AS current_column_comment,
    CASE
        WHEN c.column_type = e.column_type
         AND c.is_nullable = e.is_nullable
         AND c.column_default <=> e.column_default
         AND c.character_set_name <=> e.character_set_name
         AND c.collation_name <=> e.collation_name
         AND c.extra = e.extra
        THEN 'PASS'
        ELSE 'FAIL'
    END AS modify_definition_match
FROM information_schema.columns c
JOIN expected_columns e
  ON e.table_name = c.table_name
 AND e.column_name = c.column_name
WHERE c.table_schema = 'te_common'
ORDER BY c.table_name, c.ordinal_position;

SELECT
    table_schema,
    table_name,
    table_comment AS current_table_comment
FROM information_schema.tables
WHERE table_schema = 'te_common'
  AND table_name IN (
      'cm_common_code',
      'cm_verified_sql_query',
      'rl_rule_action'
  )
ORDER BY table_name;

/* ============================================================================
SPS Verified Query Registration
- Column name -> Common Code Group candidate lookup
- Cross-Repository physical/logical relationship analysis
============================================================================ */

USE te_common;

INSERT INTO cm_verified_sql_query
(
    query_id,
    query_name,
    query_description,
    crud_type,
    sql_text,
    verified_yn,
    certified_level_code,
    verification_description,
    created_by,
    created_dt,
    verified_by,
    verified_dt,
    updated_dt,
    updated_by,
    story_programming_rule_pass_yn,
    snake_case_pass_yn,
    table_exists_pass_yn,
    column_exists_pass_yn,
    crud_match_pass_yn,
    where_clause_pass_yn,
    status_code,
    program_id,
    client_ip
)
VALUES
(
    'SP_RP_SQL_QUERY_20260720_231939_00001',
    'Column Common Code Group 후보 조회',
    'Column 이름에서 _CODE 접미사와 Namespace 접두사를 제거한 어근으로 cm_common_code_group 후보를 조회한다.',
    'READ',
    'SELECT DISTINCT
    g.group_code,
    REGEXP_REPLACE(
        UPPER(g.group_code),
        ''^(AI|AU|CM|DC|EV|HC|HP|HS|MB|OC|RL|SP|SPS|WF)_'',
        ''''
    ) AS group_root,
    REGEXP_REPLACE(
        REGEXP_REPLACE(UPPER(:column_name), ''_CODE$'', ''''),
        ''^(AI|AU|CM|DC|EV|HC|HP|HS|MB|OC|RL|SP|SPS|WF)_'',
        ''''
    ) AS column_root
FROM cm_common_code_group g
WHERE
    REGEXP_REPLACE(
        UPPER(g.group_code),
        ''^(AI|AU|CM|DC|EV|HC|HP|HS|MB|OC|RL|SP|SPS|WF)_'',
        ''''
    ) LIKE CONCAT(
        ''%'',
        REGEXP_REPLACE(
            REGEXP_REPLACE(UPPER(:column_name), ''_CODE$'', ''''),
            ''^(AI|AU|CM|DC|EV|HC|HP|HS|MB|OC|RL|SP|SPS|WF)_'',
            ''''
        ),
        ''%''
    )
    OR REGEXP_REPLACE(
        REGEXP_REPLACE(UPPER(:column_name), ''_CODE$'', ''''),
        ''^(AI|AU|CM|DC|EV|HC|HP|HS|MB|OC|RL|SP|SPS|WF)_'',
        ''''
    ) LIKE CONCAT(
        ''%'',
        REGEXP_REPLACE(
            UPPER(g.group_code),
            ''^(AI|AU|CM|DC|EV|HC|HP|HS|MB|OC|RL|SP|SPS|WF)_'',
            ''''
        ),
        ''%''
    )
ORDER BY g.group_code',
    'Y',
    'A',
    'cm_common_code_group 실 Schema와 MariaDB REGEXP_REPLACE 문법을 기준으로 검증한 Parameterized READ Query.',
    'SYSTEM',
    NOW(),
    'SYSTEM',
    NOW(),
    NOW(),
    'SYSTEM',
    'Y',
    'Y',
    'Y',
    'Y',
    'Y',
    'Y',
    'ACTIVE',
    'SPS_RELATIONSHIP_ANALYSIS_REGISTER',
    '127.0.0.1'
),
(
    'SP_RP_SQL_QUERY_20260720_231939_00002',
    'Repository 물리·논리 관계 조회',
    'COMMON, STORY_PLATFORM, HEALTH_COMPANION 세 Repository의 실제 FK와 동일 _id/_code Column 기반 논리 관계를 함께 조회한다.',
    'READ',
    'SELECT
    ''PHYSICAL_FK'' AS relation_type,
    k.constraint_name,
    k.constraint_schema AS source_schema,
    k.table_name AS source_table,
    k.column_name AS source_column,
    k.referenced_table_schema AS target_schema,
    k.referenced_table_name AS target_table,
    k.referenced_column_name AS target_column
FROM information_schema.key_column_usage k
JOIN information_schema.tables st
  ON st.table_schema = k.constraint_schema
 AND st.table_name = k.table_name
 AND st.table_type = ''BASE TABLE''
JOIN information_schema.tables tt
  ON tt.table_schema = k.referenced_table_schema
 AND tt.table_name = k.referenced_table_name
 AND tt.table_type = ''BASE TABLE''
WHERE k.referenced_table_name IS NOT NULL
  AND k.constraint_schema IN (
      :common_schema,
      :story_platform_schema,
      :health_companion_schema
  )
  AND k.table_name NOT REGEXP ''(_backup_|_rollback_|_bak$)''
  AND k.referenced_table_name NOT REGEXP ''(_backup_|_rollback_|_bak$)''

UNION ALL

SELECT
    ''LOGICAL_SHARED_COLUMN'' AS relation_type,
    NULL AS constraint_name,
    c1.table_schema AS source_schema,
    c1.table_name AS source_table,
    c1.column_name AS source_column,
    c2.table_schema AS target_schema,
    c2.table_name AS target_table,
    c2.column_name AS target_column
FROM information_schema.columns c1
JOIN information_schema.tables t1
  ON t1.table_schema = c1.table_schema
 AND t1.table_name = c1.table_name
 AND t1.table_type = ''BASE TABLE''
JOIN information_schema.columns c2
  ON c2.column_name = c1.column_name
 AND CONCAT(c1.table_schema, ''.'', c1.table_name)
     < CONCAT(c2.table_schema, ''.'', c2.table_name)
JOIN information_schema.tables t2
  ON t2.table_schema = c2.table_schema
 AND t2.table_name = c2.table_name
 AND t2.table_type = ''BASE TABLE''
WHERE c1.table_schema IN (
      :common_schema,
      :story_platform_schema,
      :health_companion_schema
  )
  AND c2.table_schema IN (
      :common_schema,
      :story_platform_schema,
      :health_companion_schema
  )
  AND c1.column_name REGEXP ''(_id|_code)$''
  AND c1.table_name NOT REGEXP ''(_backup_|_rollback_|_bak$)''
  AND c2.table_name NOT REGEXP ''(_backup_|_rollback_|_bak$)''
  AND NOT EXISTS (
      SELECT 1
      FROM information_schema.key_column_usage fk
      WHERE fk.referenced_table_name IS NOT NULL
        AND (
            (
                fk.constraint_schema = c1.table_schema
                AND fk.table_name = c1.table_name
                AND fk.column_name = c1.column_name
                AND fk.referenced_table_schema = c2.table_schema
                AND fk.referenced_table_name = c2.table_name
                AND fk.referenced_column_name = c2.column_name
            )
            OR
            (
                fk.constraint_schema = c2.table_schema
                AND fk.table_name = c2.table_name
                AND fk.column_name = c2.column_name
                AND fk.referenced_table_schema = c1.table_schema
                AND fk.referenced_table_name = c1.table_name
                AND fk.referenced_column_name = c1.column_name
            )
        )
  )
ORDER BY relation_type, source_schema, source_table, source_column, target_schema, target_table',
    'Y',
    'A',
    'information_schema의 TABLES, COLUMNS, KEY_COLUMN_USAGE를 사용하며 Backup Table과 물리 FK로 이미 확정된 중복 논리 관계를 제외한다.',
    'SYSTEM',
    NOW(),
    'SYSTEM',
    NOW(),
    NOW(),
    'SYSTEM',
    'Y',
    'Y',
    'Y',
    'Y',
    'Y',
    'Y',
    'ACTIVE',
    'SPS_RELATIONSHIP_ANALYSIS_REGISTER',
    '127.0.0.1'
)
ON DUPLICATE KEY UPDATE
    query_name                    = VALUES(query_name),
    query_description             = VALUES(query_description),
    crud_type                     = VALUES(crud_type),
    sql_text                      = VALUES(sql_text),
    verified_yn                   = VALUES(verified_yn),
    certified_level_code          = VALUES(certified_level_code),
    verification_description      = VALUES(verification_description),
    verified_by                   = VALUES(verified_by),
    verified_dt                   = VALUES(verified_dt),
    updated_dt                    = NOW(),
    updated_by                    = VALUES(updated_by),
    story_programming_rule_pass_yn = VALUES(story_programming_rule_pass_yn),
    snake_case_pass_yn            = VALUES(snake_case_pass_yn),
    table_exists_pass_yn          = VALUES(table_exists_pass_yn),
    column_exists_pass_yn         = VALUES(column_exists_pass_yn),
    crud_match_pass_yn            = VALUES(crud_match_pass_yn),
    where_clause_pass_yn          = VALUES(where_clause_pass_yn),
    status_code                   = VALUES(status_code),
    deleted_dt                    = NULL,
    deleted_by                    = NULL,
    program_id                    = VALUES(program_id),
    client_ip                     = VALUES(client_ip);

SELECT
    query_id,
    query_name,
    crud_type,
    verified_yn,
    certified_level_code,
    status_code
FROM cm_verified_sql_query
WHERE query_id IN
(
    'SP_RP_SQL_QUERY_20260720_231939_00001',
    'SP_RP_SQL_QUERY_20260720_231939_00002'
)
ORDER BY query_id;

-- Prepare Verified SQL Repository for full runtime batch registration
ALTER TABLE te_common.cm_verified_sql_query
    MODIFY COLUMN sql_text LONGTEXT NOT NULL
    COMMENT '검증 또는 실행이 승인된 SQL Batch 원문. sql/runtime 전체 Batch를 손실 없이 Repository에 보관한다.';

SELECT column_name, column_type, is_nullable, column_comment
FROM information_schema.columns
WHERE table_schema = 'te_common'
  AND table_name = 'cm_verified_sql_query'
  AND column_name = 'sql_text';

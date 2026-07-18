/*
 * SPS Harness v2.0 Repository Inspection
 *
 * 목적:
 * - Harness Session, Context, Memory 관련 기존 Table Object 확인
 * - 신규 테이블 생성 전 중복 및 통합 가능성 검증
 */

SELECT
    DATABASE() AS current_database,
    USER() AS connection_user,
    CURRENT_USER() AS privilege_user;

SELECT
    table_name,
    table_comment
FROM information_schema.tables
WHERE table_schema = DATABASE()
  AND (
       table_name LIKE '%harness%'
    OR table_name LIKE '%session%'
    OR table_name LIKE '%context%'
    OR table_name LIKE '%memory%'
    OR table_name LIKE '%checkpoint%'
    OR table_name LIKE '%conversation%'
  )
ORDER BY table_name;

SELECT
    table_name,
    column_name,
    column_type,
    is_nullable,
    column_default,
    column_key,
    column_comment
FROM information_schema.columns
WHERE table_schema = DATABASE()
  AND (
       column_name LIKE '%session%'
    OR column_name LIKE '%context%'
    OR column_name LIKE '%memory%'
    OR column_name LIKE '%checkpoint%'
    OR column_name LIKE '%conversation%'
  )
ORDER BY table_name, ordinal_position;

SELECT
    object_id,
    object_code,
    object_name,
    object_level,
    status_code
FROM sp_object
WHERE
       object_code LIKE '%HARNESS%'
    OR object_code LIKE '%SESSION%'
    OR object_code LIKE '%CONTEXT%'
    OR object_code LIKE '%MEMORY%'
    OR object_name LIKE '%Harness%'
    OR object_name LIKE '%Session%'
    OR object_name LIKE '%Context%'
    OR object_name LIKE '%Memory%'
ORDER BY object_code;

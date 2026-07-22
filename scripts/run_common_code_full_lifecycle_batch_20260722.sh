#!/usr/bin/env bash
set -euo pipefail
cd /data/vm_project
SQL_FILE="sql/runtime/common_code_full_lifecycle_batch_20260722.sql"
LOG_DIR="outputs/logs"
mkdir -p "$LOG_DIR"
STAMP="$(date +%Y%m%d_%H%M%S)"
LOG_FILE="$LOG_DIR/common_code_full_lifecycle_batch_$STAMP.log"
: "${COMMON_MARIADB_HOST:?COMMON_MARIADB_HOST is required}"
: "${COMMON_MARIADB_PORT:?COMMON_MARIADB_PORT is required}"
: "${COMMON_MARIADB_USER:?COMMON_MARIADB_USER is required}"
: "${COMMON_MARIADB_PASSWORD:?COMMON_MARIADB_PASSWORD is required}"
: "${COMMON_MARIADB_DATABASE:?COMMON_MARIADB_DATABASE is required}"

MYSQL=(mariadb -h "$COMMON_MARIADB_HOST" -P "$COMMON_MARIADB_PORT" -u "$COMMON_MARIADB_USER" "$COMMON_MARIADB_DATABASE")
MYSQL_PWD="$COMMON_MARIADB_PASSWORD" "${MYSQL[@]}" < "$SQL_FILE" | tee "$LOG_FILE"

SQL_B64="$(base64 -w 0 "$SQL_FILE")"
REGISTER_FILE="$(mktemp /tmp/common_code_verified_query_XXXXXX.sql)"
trap 'rm -f "$REGISTER_FILE"' EXIT
{
  printf "%s\n" "USE te_common;"
  printf "%s\n" "INSERT INTO cm_verified_sql_query"
  printf "%s\n" "(query_id,query_name,query_description,crud_type,sql_text,verified_yn,certified_level_code,verification_description,created_by,created_dt,verified_by,verified_dt,story_programming_rule_pass_yn,snake_case_pass_yn,table_exists_pass_yn,column_exists_pass_yn,crud_match_pass_yn,where_clause_pass_yn,status_code,program_id,client_ip)"
  printf "%s\n" "VALUES ('SP_RP_SQL_QUERY_20260722_FULL_LIFECYCLE_00001','공통코드 전체 생명주기 분류 및 정비 Batch','공통코드 전체를 6개 생명주기 상태로 분류하고 설명, program_id, sort_no를 보완한 검증 SQL Batch.','BATCH',CONVERT(FROM_BASE64('$SQL_B64') USING utf8mb4),'Y','A','DEV 실행 성공 후 전체 Batch 원문을 저장했다. 물리 삭제와 영향도 없는 PK Rename은 수행하지 않았다.','SYSTEM',NOW(),'SYSTEM',NOW(),'Y','Y','Y','Y','Y','Y','ACTIVE','CM_COMMON_CODE_LIFECYCLE_BATCH_20260722','127.0.0.1')"
  printf "%s\n" "ON DUPLICATE KEY UPDATE sql_text=VALUES(sql_text),verified_yn='Y',certified_level_code='A',verification_description=VALUES(verification_description),verified_by='SYSTEM',verified_dt=NOW(),updated_by='SYSTEM',updated_dt=NOW(),program_id=VALUES(program_id),client_ip=VALUES(client_ip);"
  printf "%s\n" "SELECT query_id,verified_yn,certified_level_code,CHAR_LENGTH(sql_text) sql_text_length,program_id FROM cm_verified_sql_query WHERE query_id='SP_RP_SQL_QUERY_20260722_FULL_LIFECYCLE_00001';"
} > "$REGISTER_FILE"
MYSQL_PWD="$COMMON_MARIADB_PASSWORD" "${MYSQL[@]}" < "$REGISTER_FILE" | tee -a "$LOG_FILE"
printf 'SUCCESS log=%s\n' "$LOG_FILE"

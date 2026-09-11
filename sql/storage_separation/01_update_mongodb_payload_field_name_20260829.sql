-- =============================================================================
-- File Story
-- =============================================================================
-- STORAGE_SEPARATION_TARGET 공통코드의 MongoDB document payload field 명칭을 정정한다.
-- 이 파일의 UPDATE는 직접 실행하지 않는다. cm_verified_sql_query 등록 후 Query ID로만 실행한다.
--
-- Change History
-- 20260829 | CODEX | MariaDB 원본 상세 컬럼과 MongoDB Payload field를 분리해 네 계약의 문서 필드명을 정정한다.
-- =============================================================================

UPDATE cm_common_code
SET
    common_code_json = JSON_SET(
        common_code_json,
        '$.mongodb_payload_field_name',
        CASE code
            WHEN 'HEALTH_REPORT_CONTENT' THEN 'health_report_content'
            WHEN 'SQL_GUARD_EXECUTION_DETAIL' THEN 'sql_guard_executionr_message'
            WHEN 'SQL_GUARD_VERIFICATION_DETAIL' THEN 'sql_guard_verification_message'
            WHEN 'IMPACT_ANALYSIS_DETAIL' THEN 'sp_impact_analysis_text'
        END
    ),
    updated_by = %s,
    updated_dt = CURRENT_TIMESTAMP,
    program_id = %s,
    client_ip = %s
WHERE group_code = 'STORAGE_SEPARATION_TARGET'
  AND code IN (
      'HEALTH_REPORT_CONTENT',
      'SQL_GUARD_EXECUTION_DETAIL',
      'SQL_GUARD_VERIFICATION_DETAIL',
      'IMPACT_ANALYSIS_DETAIL'
  )
  AND status_code = 'ACTIVE'
  AND deleted_dt IS NULL;

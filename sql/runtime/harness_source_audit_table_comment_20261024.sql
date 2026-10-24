/* harness_source_audit 테이블 COMMENT 수정 (2026-10-24, LuckyBoys 요청)
   목적 : pipeline_results -> harness_source_audit 이름 변경 후, 표준 [MONGODB_PAYLOAD] 형식은 유지하고
          컬렉션명과 용도 설명만 소스 작업 감사 용도로 바꾼다.
   이유 : MCP mariadb_ddl_execute가 따옴표 안의 ';'도 문장 구분자로 보고 거부한다
          ("Provide exactly one table DDL statement without SQL comments"). 표준 형식은 ';'를 구분자로 써야 해서
          MCP로는 적용할 수 없으므로 수동 실행용으로 남긴다.
   주의 : 컬렉션명 harness_source_audit_payload는 MongoDB 이름 변경이 끝난 뒤에 실행할 것.
          (2026-10-24 현재 mongodb_rename_collection 도구 버그로 pipeline_results_payload가 그대로 남아 있음)
   검증 : 실행 후 SHOW CREATE TABLE te_common.harness_source_audit 로 COMMENT를 확인한다. 컬럼 COMMENT는 MCP로 적용 완료. */
SET NAMES utf8mb4;

ALTER TABLE `te_common`.`harness_source_audit`
  COMMENT = '[MONGODB_PAYLOAD] Collection: harness_source_audit_payload; MongoDB Role: COMMON; MariaDB Role: INDEX_ONLY; MariaDB에는 Harness MCP 소스 작업(source_write, source_patch, source_delete, 실행, 테스트 검증) 감사 색인을 유지하고 상세 내용(diff, 실행 출력, sha256 등 data_json)은 MongoDB에 저장한다. 2026-10-24 pipeline_results에서 이름 변경.';

SHOW CREATE TABLE `te_common`.`harness_source_audit`;

Current Task:
- SPS Object Level 분류 Rule의 condition_id 분기 등록·실행 검증 완료
- Health Companion Repository/ERD 확장 사전 검증 및 SPS Harness MCP OAuth 운영 배포 검증 대기

Completed:
- sp_entity를 ERD 범위로 이관하고 기존 Entity 14건을 연결
- COMMON:CM Repository Sync Batch Apply 완료: Table 7, Entity 16, Attribute 126, Relationship 6
- sp_relationship의 Source/Target Entity 복합 FK 적용 및 6건 검증 완료
- Batch 재실행 안정성 검증 완료: inserted 없음
- Commit: c0e8a74 feat(erd): scope entities by ERD and enforce relationship references
- feature/spds-v0.1 원격 push 완료
- Object Level Rule SQL 수정·stage 완료: sql/runtime/register_object_level_classification_rule_20260729.sql
- 확정 Rule: cm_data_classification.classification_id=Level 2, sp_erd.erd_id=Level 2, sp_object.object_id=정체에 따라 Level 0~5, Table Object=Level 3, 별도 등록 Attribute/Relationship Attribute=Level 4
- te_common.cm_verified_sql_query의 빈 구형 감사 컬럼 12개 삭제 완료 및 구조 백업 완료: /data/vm_project/backup_cm_verified_sql_query_20260729.sql
- cm_verified_sql_query 감사 컬럼을 테이블 맨 끝으로 정렬 완료: created_by, created_dt, updated_by, updated_dt, deleted_by, deleted_dt, program_id, client_ip
- SPS Harness MCP OAuth Provider 구현: harness/mcp/oauth_provider.py
- Google OIDC Authorization Code 로그인, 허용 이메일 환경설정, PKCE/DCR, CommonAuth 기반 JWT Access/Refresh 발급·검증·회전·폐기 구현
- FastMCP OAuth Authorization Server Metadata, RFC 9728 Protected Resource Metadata, 보호된 /mcp 연결 구현
- OAuth 회귀 테스트 추가: tests/harness/mcp/test_oauth_provider.py, tests/harness/mcp/test_oauth_http.py
- 격리 실행 검증 완료: 5 passed in 4.44s
- HTTP 경계 검증 완료: OAuth metadata 200, 무토큰 /mcp 401, WWW-Authenticate resource_metadata 확인
- requirements.txt에 mcp 1.28.0, Google OIDC 의존성 google-auth/httpx/requests 및 pytest 명시
- Object Level Rule 분기 등록 완료: rule_id=SP_RP_RL_RULE_20260731_00001
  - condition_id별 명시 분기: ERD → Level 2, ENTITY → Level 3, RELATIONSHIP → Level 3
  - 각 명시 Action의 action_value.condition_id가 정확히 한 Condition을 참조함
  - condition_id 없는 유일한 Default Action은 양성 분기 0건에서 Level 4를 반환함
- Resolver 실검증 완료: ERD=2 EXPLICIT_RULE, ENTITY=3 EXPLICIT_RULE, RELATIONSHIP=3 EXPLICIT_RULE, EXECUTION_HISTORY=4 DEFAULT
- DB 구조 변경 없음. sql/runtime/07_reconcile_object_level_rule_action_context_20260802.sql 적용 및 관련 pytest 4 passed
- 20260804 변경을 책임별 로컬 Commit으로 분리 완료
  - 5707094 feat(identifier): resolve object levels through repository rules
  - ae062d6 feat(storage): separate MariaDB indexes from MongoDB documents
  - e368de5 feat(harness): add lifecycle reconciliation and verified SQL registration
  - 191db0c feat(ui-runtime): migrate UI repository and screen identifiers

Next Task:
- HEALTH_COMPANION:HC 대상 Dry Run 실행 후 Apply 여부를 결정한다
- source_read 범위 밖인 실제 Nginx 및 ngrok systemd 설정을 운영 권한으로 읽고 OAuth callback 및 well-known 경로 프록시 여부를 검증한다
- 운영 환경에 SPS_MCP_OAUTH_*, SPS_MCP_GOOGLE_* 및 기존 SPS_AUTH_JWT_* 설정을 주입한다. 허용 이메일은 jeajea.park@gmail.com으로 설정한다
- Google Cloud OAuth Redirect URI를 운영 callback URL과 일치시키고 Harness MCP 서비스를 재시작한다
- 실제 Google 브라우저 로그인, 토큰 교환, Bearer /mcp 호출 E2E를 수행한다
- 로컬 Commit은 사용자가 검토한 뒤 직접 원격 push한다

Decisions:
- 이후 작업에서는 DB 구조를 변경하지 않는다
- Entity는 erd_id 범위에서 관리한다
- Relationship Source/Target은 동일 erd_id의 Entity만 참조한다
- sp_attribute는 테이블 Object 단위의 공용 Column Metadata로 유지한다
- 테이블 PK 한 건의 Level은 일괄적으로 4가 아니며, 그 ID가 표현하는 대상 정체로 결정한다
- Object Level은 테이블명, _log/_history/_result 접미사, 저장 위치, SELECT 행위로 결정하지 않는다
- Object Level의 양성 분기는 Action JSON의 condition_id로 1:1 바인딩한다
- 양성 분기 0건은 유일한 Default Action으로 처리하고, 복수 명시 Action 또는 복수 Default Action은 fail-closed 한다
- Repository First, Metadata Driven, 하드코딩 금지 원칙을 유지한다
- OAuth 설정값과 허용 계정은 코드에 하드코딩하지 않고 환경변수로만 관리하며, JWT 서명·검증은 common.auth.CommonAuth를 단일 구현으로 사용한다
- OAuth 런타임 상태는 DB 구조를 변경하지 않고 프로세스 메모리에 유지한다. 운영은 단일 MCP 프로세스를 전제로 한다
- 비밀값, 토큰, Google Client Secret은 로그·체크포인트·소스에 기록하지 않는다
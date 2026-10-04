2026-09-18 01:08+09:00 verification
- After user restart: sps-harness MainPID=1607251, active/running, MCP /mcp 200 OK.
- Common-code SSOT patch is active: previous sp_business table error is gone.
- Both repository_table_object_reconcile(apply=false) and object_lifecycle_reconcile(apply=false) now stop at the next real contract inconsistency: table prefix CM maps to domain CO, but CM_DOMAIN common-code metadata has no CO code.
- Confirmed CM_BUSINESS and CM_DOMAIN groups/codes from cm_common_code/group. No DB mutation performed.
- Applied final message patch changing stale error text from cm_business_domain to CM_DOMAIN common-code metadata (SHA256=4ff6a31c6f07280073d89ecde985039ae4d6d5dda2d2ead48bbae20323169a20). Service restart required only to load this message patch.
- agent_long_term_memory remains 0; registration still not started. Do not invent CM->domain mapping or insert a new code without explicit data decision.

2026-10-04 pipeline-results
- Pipeline-results 저장 경로 전환·보상 구현 완료: pipeline.py는 save_both('pipeline_results', ...) 대신 Repository 서비스 save_pipeline_results(...)를 호출한다.
- MariaDB 색인 + 실행 이력/링크와 계약 지정 MongoDB payload 저장을 수행하며, 후속 MariaDB 단계 실패 시 롤백 및 Mongo 보상 삭제가 적용된다.
- Mongo source_object_id 및 execution link는 참조 Object SP_RP_OBJECT_20260707_212013_00004 (DOCUMENT)를 사용한다.
- tests/services/test_pipeline_results_repository.py: 정상 저장·강제 링크 실패 보상·save_both 경로 제거 테스트 3개 통과. 운영 DB 쓰기 및 서비스 재시작 미실행.

2026-10-05 git commit 작업
- 기능별 선행 커밋 10개: c434305, 8e0bec3, adb9809, 89f47fb, 9f06cbf, b134ef8, 5bf1471, 2b24562, 3e4e888, 2e406d9.
- 커밋하지 않은 변경은 별도 검증 후 기능 단위로 기록한다. Git push 미실행.
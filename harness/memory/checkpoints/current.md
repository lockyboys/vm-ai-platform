Current Task:
- cm_business_domain SSOT 기반 Repository 전체 동기화 배치 구현 완료

Completed:
- engine/batch/business_domain_repository_sync_batch.py 생성
- Table → Entity → Attribute → ERD → Relationship 동기화 구현
- Repository 역할 기반 DB 연결
- IdentifierEngine 기반 ID 발행
- 기본 dry-run 및 --apply DML 실행 분리
- 트랜잭션 commit/rollback 적용
- 커밋 fd07ad7 완료
- Git working tree clean 확인

Next Task:
- 서버에서 dry-run 실행
- 실제 Repository Table 구조 및 저장 행 검증
- 멱등성 검증: --apply 2회 실행 후 신규 중복 0 확인
- 필요 시 검증 결과 기반 보완 커밋

Decisions:
- cm_business_domain을 Domain SSOT로 사용
- DB 구조 변경 금지
- 물리 Database 명 하드코딩 금지
- 기존 Repository ID 유지
- 실행 전 dry-run 기본값 유지
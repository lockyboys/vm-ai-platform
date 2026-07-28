Current Task:
- Health Companion Repository/ERD 확장 사전 검증

Completed:
- sp_entity를 ERD 범위로 이관하고 기존 Entity 14건을 연결
- COMMON:CM Repository Sync Batch Apply 완료: Table 7, Entity 16, Attribute 126, Relationship 6
- sp_relationship의 Source/Target Entity 복합 FK 적용 및 6건 검증 완료
- Batch 재실행 안정성 검증 완료: inserted 없음
- Commit: c0e8a74 feat(erd): scope entities by ERD and enforce relationship references
- feature/spds-v0.1 원격 push 완료
- Git working tree clean 확인

Next Task:
- HEALTH_COMPANION:HC 대상 Dry Run 실행
- 결과 검증 후 Apply 여부를 결정한다

Decisions:
- DB 구조 변경은 하지 않는다
- Entity는 erd_id 범위에서 관리한다
- Relationship Source/Target은 동일 erd_id의 Entity만 참조한다
- sp_attribute는 테이블 Object 단위의 공용 Column Metadata로 유지한다
- Repository First, Metadata Driven, 하드코딩 금지 원칙을 유지한다
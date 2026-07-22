# SPS Work Checkpoint

## Current Task
- K-디지털 트레이닝 해커톤 시연 준비를 최우선으로 둔다.
- Rule Repository 및 Identifier DB 구조 정비는 시연 이후 재개한다.

## Completed
- `rl_rule_action`의 의미를 Rule Action이 아니라 Rule Decision으로 정정하기로 결정했다.
- 동기화 대상은 `rl_rule_decision`, `rl_rule_evidence.rule_decision_id`, Rule Decision 공통코드, `sp_object`, `sp_metadata`, `sp_relationship`, 관련 문서·Generator·Engine 설정으로 확정했다.
- `ac_action`과 `cm_role_rule`은 변경 대상에서 제외하기로 확정했다.
- 오늘 DB `ALTER`·`RENAME`·`UPDATE`·실행 및 Git 변경은 수행하지 않았다.

## Next Task
- 시연 종료 후 Rule 관련 테이블 전체 동기화 범위를 최종 확정한다.
- 원본 보존용 백업을 포함한 정비 SQL을 작성·검토한 뒤 승인된 범위만 적용한다.

## Decisions
- 테이블명 변경은 단독 변경이 아니라 PK·FK·필드명·`*_code` 공통코드·Repository 메타데이터를 한 묶음으로 동기화한다.
- 과거 사실인 변경 이력은 소급 수정하지 않고, 정비 사실을 새 변경 이력으로 남긴다.
- 시연 전에는 위험한 DB 구조 변경을 하지 않는다.

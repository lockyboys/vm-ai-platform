Current Task:
- Identifier Engine 단일 구현 경로 통합 Git 마무리

Completed:
- core/identifier/identifier_engine.py를 canonical engine 호환 모듈로 정리
- Identifier Engine 단위 테스트 및 caller import 계약 정비
- Identifier 테스트: 7 passed, 20 subtests passed
- 전체 테스트: 44 passed, 20 subtests passed, 실패 0
- 요청한 4개 파일만 stage 및 commit 완료
- Commit: fe24506 refactor: unify identifier engine callers

Next Task:
- feature/spds-v0.1 브랜치 push
- push 결과 확인 후 다음 Identifier Engine 작업 결정

Decisions:
- canonical 구현은 engine.identifier_engine.IdentifierEngine을 사용한다
- legacy core.identifier 경로는 호환 import만 제공한다
- DB 구조를 변경하지 않는다
- Identifier Metadata를 하드코딩하지 않는다
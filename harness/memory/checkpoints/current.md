# SPS Current Checkpoint

Updated: 2026-07-20 KST

## Current Task

- Repository 물리 Schema 표준화 결과를 확정한다.
- Data Type과 TABLE/COLUMN COMMENT 정비는 완료했다.
- 다음 대상은 `REFERENCE: UNRESOLVED`로 식별된 73개 `_code` 컬럼의 연결 원천 확정이다.

## Completed

- 실제 DB Column 1,285개 Data Type 검증 완료: mismatch 0건.
- HEALTH_COMPANION 109개, STORY_PLATFORM 378개, COMMON 798개 컬럼이 Metadata Type 표준과 일치한다.
- `version_no`를 `version_num VARCHAR(99)`로 정비하고 18개 명명 권고를 반영했다.
- 실운영 75개 Table의 TABLE COMMENT를 Repository Metadata 표준으로 정비했다.
- 변경 대상 839개 COLUMN COMMENT를 보강했다.
- 빈 TABLE COMMENT 0건, 빈 COLUMN COMMENT 0건을 확인했다.
- 영향받는 Foreign Key 22개를 DROP 후 동일 정의로 복원했고 22개 전부 존재함을 확인했다.
- 공통코드 및 Master Repository 확정 연결을 COLUMN COMMENT에 반영했다.
- COMMENT 패치 생성기, 실행 SQL, Rollback SQL Commit 완료: `90317dc`.

## Next Task

1. 미확정 `_code` 73개를 자체 Object Code, Master Repository Code, 공통코드 Group으로 분류한다.
2. 공통코드 연결은 실제 `cm_common_code.group_code`와 값 일치 여부를 검증한다.
3. 확정된 연결을 Metadata와 COLUMN COMMENT에 반영한다.
4. Analyzer를 재실행하여 `REFERENCE: UNRESOLVED` 잔존 건수를 검증한다.

## Decisions

- 완료 판단 기준은 보고서가 아니라 실제 DB 재조회 결과이다.
- `_no`는 순번 `INT`, `_num`은 문자열 번호 `VARCHAR(99)` 표준을 사용한다.
- TABLE/COLUMN COMMENT는 사람 설명이 아니라 Generator, Engine 및 AI가 읽는 공식 Repository Metadata다.
- `_code`는 공통코드 또는 Master Repository 연결 원천을 명시하며, 미확정 연결은 숨기지 않고 `REFERENCE: UNRESOLVED`로 관리한다.
- 일회성 Migration Batch의 명시적 Hardcoding은 허용하되 Runtime과 Engine의 Hardcoding은 금지한다.

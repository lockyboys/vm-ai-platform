# SPS Current Checkpoint

Updated: 2026-07-21 KST

## Current Task
- Repository Table `_id` Level 4 Migration 완료 후 후속 검증과 Source 정합성을 관리한다.

## Completed
- Level 4 형식 확정: `BUSINESS_DOMAIN_OBJECT_YYYYMMDD_HHMMSS_SEQ5`.
- 운영 Base Table 72개와 `_id` 컬럼 207개 구조 전수 조사 완료.
- 값이 존재하며 위반이 있던 98개 컬럼 Migration 완료.
- 연결군 Migration Map 357건 생성, HOLD 0건.
- 본 Migration Batch 292문장 SUCCESS.
- 97개 컬럼 `invalid_count=0` 확인.
- 최종 `cm_change_history.target_record_id` 3건 변환 SUCCESS.
- 98개 대상 컬럼 전체 Level 4 위반 0건.
- Query ID 7건과 Menu/Relationship 참조 6건도 Level 4 유지.
- Migration 전 Backup Table 44개 보존.

## Artifacts
- tools/generate_repository_level4_id_migration_20260721.py
- outputs/reports/repository_level4_id_migration_map_20260721.csv
- outputs/reports/repository_level4_id_migration_hold_20260721.csv
- sql/runtime/repository_level4_id_migration_20260721.sql
- sql/runtime/repository_level4_id_final_3_patch_20260721.sql
- docs/reports/repository_level4_id_full_audit_20260721.md

## Next Task
1. 실제 DB 전체 `_id` 재분석 보고서 생성.
2. PK/FK 및 논리 참조 고아값 0건 검증.
3. 신규 입력 Level 4 Validator 적용.
4. Source Seed/Runtime SQL의 Legacy ID 검색 및 정비.
5. Backup Table 삭제는 검증과 Commit 이후 별도 Cleanup Batch로 수행.
6. Git status 검토 후 명시 파일만 Commit/Push.

## Decisions
- 모든 Table `_id`는 Level 4.
- Random 금지.
- PK/FK/논리 참조는 연결군 단위로 함께 Migration.
- 일회성 Migration Hardcoding 허용.
- 과거 Snapshot/Backup은 검증 완료 전 보존.

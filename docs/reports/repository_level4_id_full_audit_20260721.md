# Repository Level 4 ID 전수 조사 보고서

- 조사일: 2026-07-21 KST
- 대상: HEALTH_COMPANION, STORY_PLATFORM, COMMON
- 규칙: `{BUSINESS_CODE}_{DOMAIN_CODE}_{OBJECT_CODE}_{YYYYMMDD}_{HHMMSS}_{SEQ5}`
- 제외: View 및 `*_backup_*` Migration 백업 테이블

## 요약

| 항목 | 결과 |
|---|---:|
| 운영 Base Table | 72 |
| 전체 `_id` 컬럼 | 207 |
| PK `_id` 컬럼 | 58 |
| 값이 존재하는 `_id` 컬럼 | 102 |
| 빈 `_id` 컬럼 | 105 |
| Level 4 완전 준수 컬럼 | 4 |
| 위반값이 존재하는 컬럼 | 98 |
| 조회된 비어 있지 않은 값 | 1,186 |
| Level 4 준수값 | 119 |
| Level 4 위반값 | 1,067 |

> 값 집계는 MCP가 반환한 실제 행 기준이다. `cm_common_code`, `sp_metadata`, `cm_change_history`는 조회 상한 때문에 위반값 합계가 최소치다. 구조 조사는 72개 테이블 전체 DDL을 기준으로 완료했다.

## Database별 결과

| Database | _id 컬럼 | 값 존재 | 위반 컬럼 |
|---|---:|---:|---:|
| COMMON | 114 | 47 | 45 |
| HEALTH_COMPANION | 25 | 24 | 24 |
| STORY_PLATFORM | 68 | 31 | 29 |

## 현재 완전 준수 컬럼

- `te_common.cm_verified_sql_query.query_id`
- `te_common.system_menu_button.query_id`
- `te_story_platform.sp_metadata.metadata_id`
- `te_story_platform.sp_relationship.relationship_id`

## 혼합 상태

- `sp_identifier_sequence.identifier_sequence_id`: 20건 중 2건 준수, 18건 위반
- `sp_relationship.target_object_id`: Query ID 2건 준수, 기존 Object ID 2건 위반

## 주요 위반 그룹

| 위치 | 확인 위반 | 예시 |
|---|---:|---|
| `te_story_platform.sp_metadata.target_id` | 100 | `SP_MT_METADATA_20260714_00001` |
| `te_story_platform.sp_metadata.program_id` | 100 | `MetadataGenerator`, `upsert_column_semantic_metadata_20260719`, `upsert_column_suffix_metadata_20260719` |
| `te_story_platform.sp_knowledge_hold.knowledge_id` | 79 | `1`, `129`, `130` |
| `te_story_platform.sp_knowledge_hold.knowledge_type_id` | 79 | `5`, `6` |
| `te_story_platform.sp_knowledge_hold.program_id` | 79 | `SPS_BLUEPRINT_HOLD_REGISTER`, `SPS_REPOSITORY_KNOWLEDGE_BATCH_20260719` |
| `te_common.cm_common_code.program_id` | 63 | `SPS_BUSINESS_INIT`, `SPS_REPOSITORY_INIT`, `SPS_DOMAIN_INIT` |
| `te_story_platform.sp_knowledge_relationship_hold.knowledge_relationship_id` | 53 | `100`, `101`, `102` |
| `te_story_platform.sp_knowledge_relationship_hold.source_knowledge_id` | 53 | `156`, `161`, `145` |
| `te_story_platform.sp_knowledge_relationship_hold.target_knowledge_id` | 53 | `154`, `160`, `144` |
| `te_story_platform.sp_knowledge_relationship_hold.program_id` | 53 | `SPS_REPOSITORY_KNOWLEDGE_BATCH_20260719` |
| `te_common.cm_common_code_group.program_id` | 36 | `SPS_COMMON_INIT`, `SPS_REPOSITORY_INIT`, `SPS_COMMON_CODE_CLEANUP` |
| `te_common.sp_policy_rule_keyword.rule_keyword_id` | 24 | `1`, `10`, `11` |
| `te_story_platform.sp_identifier_sequence.program_id` | 20 | `test_identifier_engine_single.py`, `test_identifier_engine_batch.py`, `test_sps_distributed_transaction.py` |
| `te_story_platform.sp_identifier_sequence.identifier_sequence_id` | 18 | `IS_20260705_AP_API`, `IS_20260705_AT_ATTRIBUTE`, `IS_20260705_BU_BUSINESS` |
| `te_story_platform.sp_knowledge_type_hold.knowledge_type_id` | 15 | `1`, `10`, `11` |
| `te_story_platform.sp_execution_history.execution_history_id` | 12 | `1`, `10`, `11` |
| `te_story_platform.sp_execution_history.trace_id` | 12 | `TR_20260707_100612`, `TR_20260707_154742`, `TR_20260707_172119` |
| `te_story_platform.sp_execution_history.object_id` | 12 | `OB_20260706_00001` |
| `te_common.sp_policy_rule_candidate.rule_candidate_id` | 9 | `1`, `2`, `3` |
| `te_common.sp_policy_rule_candidate.program_id` | 9 | `pa_rule_candidate_extractor` |
| `te_story_platform.sp_object.object_id` | 9 | `OB_2026_00001`, `OB_2026_00002`, `OB_2026_00003` |
| `te_common.system_menu_button_crud_permission.permission_id` | 8 | `1`, `2`, `3` |
| `te_common.cm_business_domain.business_domain_id` | 7 | `BD_AC`, `BD_AT`, `BD_DC` |
| `te_common.cm_storage_repository.repository_id` | 7 | `IMAGE_STORAGE`, `MARIADB_AI_PLATFORM`, `MARIADB_COMMON` |
| `te_common.cm_verified_sql_query.program_id` | 7 | `SPS_QUERY_ID_LEVEL4_MIGRATION` |
| `te_story_platform.sp_object.program_id` | 7 | `init_object_identifier_blueprint`, `object_runtime_engine`, `ObjectDefinitionGenerator` |
| `te_common.cm_storage_policy.policy_id` | 6 | `1`, `2`, `3` |
| `te_common.cm_storage_policy.repository_id` | 6 | `MARIADB_COMMON`, `MONGODB_HEALTH`, `VOICE_STORAGE` |
| `te_common.cm_change_history.change_history_id` | 5 | `1`, `2`, `CH_20260720_COUNTRY_COMMON_CODE_00001` |
| `te_common.cm_change_history.target_record_id` | 5 | `TE_MR_20260621000001`, `TE_RL_20260620000001`, `COUNTRY` |

## 원인 분류

1. 숫자형 Legacy ID: Knowledge HOLD, Execution History, Policy Candidate/Keyword, Permission 등.
2. 이전 단계 ID: `RL_20260626000001`, `OB_2026_00001`, `TE_MB_20260620000001` 등 날짜·시간·도메인 일부 누락.
3. 의미 코드형 ID: `AP_FULL`, `MARIADB_COMMON`, `LC_ACTIVE` 등.
4. 감사 필드의 실행 주체 문자열: `program_id`에 Script/Generator 이름 저장.
5. 로그인 식별자: `user_login_id`에 `admin`, `user01` 저장.

## Migration 우선순위

1. PK와 물리 FK 연결군.
2. 논리 참조 연결군(`target_object_id`, `source_object_id` 포함).
3. 독립 PK.
4. `program_id`, `user_id`, `login_id`의 의미 재정의 후 Migration.
5. 빈 컬럼 105개는 신규 입력 Validator로 차단.

## 결론

Query ID 7건 Migration만 Level 4 전환이 완료되었다. 전체 Repository의 `_id` 정비는 아직 완료 상태가 아니며, PK/FK/논리 참조를 연결군 단위로 동시에 변경해야 한다.

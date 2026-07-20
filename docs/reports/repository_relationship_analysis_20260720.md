# SPS Repository 관계 분석 및 공통 Reference 통합 보고서

- 작성일: 2026-07-20 KST
- 기준: 실제 MariaDB `te_common`, `te_story_platform`, `te_health_companion`
- 상태: 분석 Query 등록 완료 / Common Reference Migration 실행 완료 / 실 DB 재조회 완료
- 원칙: Repository First, Metadata Driven, SSOT, Runtime Hardcoding 금지

## 1. 결론

`cm_country`, `cm_language`, `cm_locale`는 독립 Master Table로 유지하지 않는다.

| 기존 Table | Row | 통합 SSOT | 이관 방식 | 최종 처리 |
|---|---:|---|---|---|
| `cm_country` | 5 | `cm_common_code / COUNTRY` | Code·Name은 정규 Column, `native_name`은 JSON | REMOVE |
| `cm_language` | 4 | `cm_common_code / LANGUAGE` | Code·Name은 정규 Column, `native_name`은 JSON | REMOVE |
| `cm_locale` | 5 | `cm_common_code / LOCALE` | 표시 형식·Timezone·상위 Code 관계는 JSON | REMOVE |

Migration 전 `COUNTRY`, `LANGUAGE`, `LOCALE` Group과 대상 Code는 0건이었다. Migration 실행 결과 3개 Group과 14개 Code가 충돌 없이 등록됐다.

Migration 전후 실 DB 재조회 결과는 다음과 같다.

| 항목 | 변경 전 | 변경 후 |
|---|---:|---:|
| Base Table | 75 | 72 |
| 물리 FK | 40 | 38 |
| `cm_common_code_group` | 51 | 54 |
| `cm_common_code` | 344 | 358 |
| Verified Query | 5 | 7 |

Source/Target 검증은 `COUNTRY 5=5`, `LANGUAGE 4=4`, `LOCALE 5=5`, JSON 오류 0건, `migration_verified=1`로 통과했다.

## 2. 조사 범위와 근거 — Migration 전 Baseline

### 실운영 Object

- COMMON: 49 Tables
- STORY_PLATFORM: 21 Tables
- HEALTH_COMPANION: 5 Tables
- 합계: 75 Base Tables, 1 View
- Backup Table은 관계 판단에서 제외했다.
- `*_hold` Table은 Backup이 아니라 실운영 Repository이므로 포함했다.
- Migration 후 실운영 구조는 COMMON 46, STORY_PLATFORM 21, HEALTH_COMPANION 5, 합계 72 Base Tables다.

### 관계 근거

- 물리 관계: `information_schema.KEY_COLUMN_USAGE`의 실제 Foreign Key 40건
- Cross-Schema 물리 FK: 0건
- 논리 관계: 동일 `_id` 또는 `_code` Column을 공유하는 관계 43개
- Runtime Source 검색: 대상 Table 직접 조회 없음
- 수정이 필요한 생성기 참조: `tools/generate_repository_table_column_comment_patch_20260720.py`
- 별도 Hardcoding 후보: `engine/generator/knowledge_document_generator.py`의 `language_code = ko`

## 3. 대상 세 Table 관계 분석

### 물리 FK

대상 세 Table을 참조하는 물리 FK는 2건이며 두 건 모두 `cm_locale`에서 나가는 내부 FK다. 대상 범위 밖 Table이 세 Table을 참조하는 외부 FK는 0건이다.

| Source | Constraint | Target | 판단 |
|---|---|---|---|
| `cm_locale.country_code` | `fk_cm_locale_country` | `cm_country.country_code` | 세 Table 내부 관계 |
| `cm_locale.language_code` | `fk_cm_locale_language` | `cm_language.language_code` | 세 Table 내부 관계 |

외부 Table이 세 Table을 물리 FK로 참조하지 않는다. 따라서 내부 FK 2개를 제거하고 `cm_locale → cm_language → cm_country` 순서가 아니라, FK 제거 후 `cm_locale`, `cm_language`, `cm_country` 순서로 DROP할 수 있다.

### 논리 관계

| Column | 관련 Table | 이관 후 연결 |
|---|---|---|
| `country_code` | `cm_country`, `cm_locale` | `cm_common_code(group_code=COUNTRY)` |
| `language_code` | `cm_language`, `cm_locale` | `cm_common_code(group_code=LANGUAGE)` |
| `locale_code` | `cm_locale` 단독 | `cm_common_code(group_code=LOCALE)` |

`LOCALE.common_code_json.language_code`와 `country_code`가 각각 `LANGUAGE`, `COUNTRY` Group을 가리킨다. 물리 FK 대신 Repository Metadata가 관계를 표현하며 Analyzer가 값 존재 여부를 검증해야 한다.

## 4. 무손실 이관 Mapping

| Source Column | Target |
|---|---|
| `country_code` | `group_code=COUNTRY, code` |
| `country_name` | `code_name` |
| `cm_country.native_name` | `common_code_json.native_name` |
| `language_code` | `group_code=LANGUAGE, code` |
| `language_name` | `code_name` |
| `cm_language.native_name` | `common_code_json.native_name` |
| `locale_code` | `group_code=LOCALE, code` |
| `locale_name` | `code_name` |
| `cm_locale.native_name` | `common_code_json.native_name` |
| `cm_locale.language_code` | `common_code_json.language_code` + `language_group_code=LANGUAGE` |
| `cm_locale.country_code` | `common_code_json.country_code` + `country_group_code=COUNTRY` |
| `date_format` | `common_code_json.date_format` |
| `time_format` | `common_code_json.time_format` |
| `datetime_format` | `common_code_json.datetime_format` |
| `number_format` | `common_code_json.number_format` |
| `timezone_id` | `common_code_json.timezone_id` |
| Audit·상태 Column | `cm_common_code`의 대응 Audit·상태 Column |

Migration SQL은 원본 세 Table과 변경 전 `cm_common_code_group`, `cm_common_code` 전체를 별도 Backup Table에 보존한다. Source/Target Row Count와 JSON 유효성이 모두 맞아야만 DROP 단계로 진행한다.

## 5. 추가 통합 후보

| Object | Row | 관계·의미 | 판정 | 다음 조치 |
|---|---:|---|---|---|
| `cm_data_classification` | 5 | 안정적 분류 Code와 4개 정책 Flag, 외부 물리 FK 없음 | MERGE_CANDIDATE | `DATA_CLASSIFICATION` Group + JSON Flag로 흡수 검토 |
| `cm_consent_history` | 0 | 이력 Object이며 `cm_change_history`와 목적 중복, 물리 FK 없음 | MERGE_DESIGN | Consent Payload 표현을 설계한 뒤 `cm_change_history`로 통합 |
| `cm_audit_policy` | 3 | 단순 Code처럼 보이나 Generator의 Audit Column 구성 정책 | REVIEW | Engine 소비 경로 확인 전 유지 |
| `cm_data_type` | 19 | 분류·Storage·Retention 기본정책 보유 | HOLD | 기존 `CM_DATA_TYPE` 9개는 Repository 자료구분으로 의미가 달라 직접 흡수 금지 |
| `cm_business_domain` | 7 | `sp_business`, `sp_domain`과 분류 책임 중복 가능 | CONSOLIDATE_REVIEW | Master 책임과 Code 값 대조 후 하나의 SSOT로 통합 |
| `cm_role`, `cm_member_role` | 각 1 | DEPRECATED 검토 이력은 있으나 FK 3개 존재 | HOLD | `cm_role_rule`, `cm_member_role` 대체 경로 확정 후 처리 |

가장 가까운 다음 공통코드 흡수 후보는 `cm_data_classification`이다. 다만 이번 Migration에는 포함하지 않았다. 사용자가 지정한 세 Table과 달리 보안·AI 접근 정책 Flag를 Runtime이 소비할 수 있으므로, 소비 경로 확인과 JSON Contract 정의가 먼저다.

### 유지해야 하는 소형 Table

- `cm_sequence_format`, `cm_sequence_policy`: `cm_sequence_rule`이 실제 FK로 참조하며 Identifier Engine의 실행 규칙이다.
- `cm_storage_policy`, `cm_legal_retention_policy`: 기간·저장소·폐기 Action을 결합하는 운영 정책이다.
- `cm_storage_repository`: 실제 Repository 연결 정보를 가진다.
- `sp_business`, `sp_domain`: Story Metadata 계층의 공식 Object이며 단순 표시 Code가 아니다.

## 6. 등록 Query

`sql/runtime/register_repository_analysis_queries_20260720.sql`이 아래 두 Query를 `cm_verified_sql_query`에 등록했으며, 두 건 모두 `ACTIVE / verified_yn=Y / certified_level_code=A`로 재조회됐다.

| Query ID | 목적 |
|---|---|
| `SP_RP_SQL_QUERY_20260720_231939_00001` | 접두사와 `_CODE`를 제거한 Column 어근으로 공통코드 Group 후보 조회 |
| `SP_RP_SQL_QUERY_20260720_231939_00002` | 세 Repository의 실제 FK와 동일 `_id/_code` 기반 논리 관계 조회 |

두 번째 Query는 물리 DB명을 SQL 본문에 고정하지 않고 `:common_schema`, `:story_platform_schema`, `:health_companion_schema` Parameter를 받는다.

## 7. Migration 산출물과 실행 순서

| 순서 | 파일 | 역할 |
|---:|---|---|
| 1 | `sql/runtime/register_repository_analysis_queries_20260720.sql` | 분석 Query 2건 등록 |
| 2 | `sql/runtime/common_reference_code_consolidation_20260720.sql` | Backup → 14건 이관 → 검증 Guard → FK/3 Table 제거 |
| 3 | `sql/runtime/common_reference_code_consolidation_rollback_20260720.sql` | 세 Table과 FK 복원, 신규 Group 제거 |
| 4 | `tools/generate_repository_table_column_comment_patch_20260720.py` | 세 Code Column의 SSOT를 COUNTRY/LANGUAGE/LOCALE로 변경 |

등록 Batch 3개 Statement와 Migration Batch 44개 Statement가 모두 성공했다. Migration 후 실 DB를 재조회하여 결과를 확정했다.

### 완료 조건

- [x] `COUNTRY=5`, `LANGUAGE=4`, `LOCALE=5`
- [x] 14개 `common_code_json` 모두 유효
- [x] `cm_country`, `cm_language`, `cm_locale` 조회 결과 0 Tables
- [x] 대상 세 Table을 참조하는 FK 0건
- [x] 등록 Query 2건이 `ACTIVE / verified_yn=Y / certified_level_code=A`
- [x] Comment Generator에서 폐기 Table Master Reference 제거
- [ ] Schema Snapshot과 Analyzer 산출물 재생성

## 8. Migration 전 전체 실운영 Table Inventory

| Role | Schema | Table | Rows |
|---|---|---|---:|
| COMMON | te_common | cm_audit_policy | 3 |
| COMMON | te_common | cm_business_domain | 7 |
| COMMON | te_common | cm_change_history | 5 |
| COMMON | te_common | cm_code_inspection_result | 0 |
| COMMON | te_common | cm_common_code | 344 |
| COMMON | te_common | cm_common_code_group | 51 |
| COMMON | te_common | cm_consent_history | 0 |
| COMMON | te_common | cm_country | 5 |
| COMMON | te_common | cm_data_classification | 5 |
| COMMON | te_common | cm_data_lifecycle_index | 0 |
| COMMON | te_common | cm_data_type | 19 |
| COMMON | te_common | cm_language | 4 |
| COMMON | te_common | cm_legal_retention_policy | 4 |
| COMMON | te_common | cm_locale | 5 |
| COMMON | te_common | cm_login_history | 0 |
| COMMON | te_common | cm_member | 1 |
| COMMON | te_common | cm_member_private | 0 |
| COMMON | te_common | cm_member_role | 1 |
| COMMON | te_common | cm_repository | 3 |
| COMMON | te_common | cm_role | 1 |
| COMMON | te_common | cm_role_rule | 0 |
| COMMON | te_common | cm_sequence | 1 |
| COMMON | te_common | cm_sequence_definition | 0 |
| COMMON | te_common | cm_sequence_format | 4 |
| COMMON | te_common | cm_sequence_format_definition | 0 |
| COMMON | te_common | cm_sequence_policy | 4 |
| COMMON | te_common | cm_sequence_policy_definition | 0 |
| COMMON | te_common | cm_sequence_rule | 1 |
| COMMON | te_common | cm_storage_policy | 6 |
| COMMON | te_common | cm_storage_repository | 7 |
| COMMON | te_common | cm_verified_sql_query | 5 |
| COMMON | te_common | ev_evidence | 1 |
| COMMON | te_common | ev_evidence_reference | 1 |
| COMMON | te_common | ev_evidence_version | 1 |
| COMMON | te_common | health_report | 0 |
| COMMON | te_common | md_object | 0 |
| COMMON | te_common | md_relation | 0 |
| COMMON | te_common | rl_rule | 2 |
| COMMON | te_common | rl_rule_action | 3 |
| COMMON | te_common | rl_rule_condition | 1 |
| COMMON | te_common | rl_rule_evidence | 1 |
| COMMON | te_common | sp_policy_rule_candidate | 9 |
| COMMON | te_common | sp_policy_rule_keyword | 24 |
| COMMON | te_common | sql_guard_execution_log | 0 |
| COMMON | te_common | sql_guard_verification_log | 0 |
| COMMON | te_common | system_menu | 1 |
| COMMON | te_common | system_menu_button | 4 |
| COMMON | te_common | system_menu_button_crud_permission | 8 |
| COMMON | te_common | system_user | 2 |
| STORY_PLATFORM | te_story_platform | sp_attribute | 0 |
| STORY_PLATFORM | te_story_platform | sp_business | 5 |
| STORY_PLATFORM | te_story_platform | sp_domain | 6 |
| STORY_PLATFORM | te_story_platform | sp_entity | 0 |
| STORY_PLATFORM | te_story_platform | sp_erd | 0 |
| STORY_PLATFORM | te_story_platform | sp_execution_history | 12 |
| STORY_PLATFORM | te_story_platform | sp_identifier_blueprint | 5 |
| STORY_PLATFORM | te_story_platform | sp_identifier_sequence | 20 |
| STORY_PLATFORM | te_story_platform | sp_impact_analysis_result | 5 |
| STORY_PLATFORM | te_story_platform | sp_knowledge_hold | 79 |
| STORY_PLATFORM | te_story_platform | sp_knowledge_relationship_hold | 53 |
| STORY_PLATFORM | te_story_platform | sp_knowledge_type_hold | 15 |
| STORY_PLATFORM | te_story_platform | sp_metadata | 123 |
| STORY_PLATFORM | te_story_platform | sp_object | 9 |
| STORY_PLATFORM | te_story_platform | sp_object_execution_link | 0 |
| STORY_PLATFORM | te_story_platform | sp_object_lifecycle | 1 |
| STORY_PLATFORM | te_story_platform | sp_relationship | 4 |
| STORY_PLATFORM | te_story_platform | sp_relationship_attribute | 0 |
| STORY_PLATFORM | te_story_platform | sp_work_asset | 0 |
| STORY_PLATFORM | te_story_platform | sp_work_item | 0 |
| STORY_PLATFORM | te_story_platform | sp_work_session | 0 |
| HEALTH_COMPANION | te_health_companion | ac_action | 2 |
| HEALTH_COMPANION | te_health_companion | at_audit | 1 |
| HEALTH_COMPANION | te_health_companion | dc_decision | 1 |
| HEALTH_COMPANION | te_health_companion | dc_decision_detail | 1 |
| HEALTH_COMPANION | te_health_companion | fb_feedback | 1 |

## 9. Migration 전 전체 물리 FK 40건

| No | Source | Constraint | Target |
|---:|---|---|---|
| 1 | te_common.cm_common_code.group_code | fk_cm_common_code_group | te_common.cm_common_code_group.group_code |
| 2 | te_common.cm_locale.country_code | fk_cm_locale_country | te_common.cm_country.country_code |
| 3 | te_common.cm_locale.language_code | fk_cm_locale_language | te_common.cm_language.language_code |
| 4 | te_common.cm_login_history.member_id | fk_cm_login_history_member | te_common.cm_member.member_id |
| 5 | te_common.cm_member_private.member_id | fk_cm_member_private_member | te_common.cm_member.member_id |
| 6 | te_common.cm_member_role.member_id | fk_cm_member_role_member | te_common.cm_member.member_id |
| 7 | te_common.cm_member_role.role_id | fk_cm_member_role_role | te_common.cm_role.role_id |
| 8 | te_common.cm_role_rule.role_id | fk_cm_role_rule_role | te_common.cm_role.role_id |
| 9 | te_common.cm_role_rule.rule_id | fk_cm_role_rule_rule | te_common.rl_rule.rule_id |
| 10 | te_common.cm_sequence_definition.format_code | fk_cm_sequence_definition_format | te_common.cm_sequence_format_definition.format_code |
| 11 | te_common.cm_sequence_definition.policy_code | fk_cm_sequence_definition_policy | te_common.cm_sequence_policy_definition.policy_code |
| 12 | te_common.cm_sequence_rule.format_code | fk_cm_sequence_rule_format | te_common.cm_sequence_format.format_code |
| 13 | te_common.cm_sequence_rule.policy_code | fk_cm_sequence_rule_policy | te_common.cm_sequence_policy.policy_code |
| 14 | te_common.cm_storage_policy.repository_id | fk_storage_policy_repository | te_common.cm_storage_repository.repository_id |
| 15 | te_common.ev_evidence_reference.evidence_id | fk_ev_reference_evidence | te_common.ev_evidence.evidence_id |
| 16 | te_common.ev_evidence_version.evidence_id | fk_ev_version_evidence | te_common.ev_evidence.evidence_id |
| 17 | te_common.md_object.object_type_group_code | fk_md_object_type | te_common.cm_common_code.group_code |
| 18 | te_common.md_object.object_type_code | fk_md_object_type | te_common.cm_common_code.code |
| 19 | te_common.md_relation.source_md_object_id | fk_md_relation_source | te_common.md_object.md_object_id |
| 20 | te_common.md_relation.target_md_object_id | fk_md_relation_target | te_common.md_object.md_object_id |
| 21 | te_common.rl_rule_action.rule_id | fk_rl_action_rule | te_common.rl_rule.rule_id |
| 22 | te_common.rl_rule_condition.rule_id | fk_rl_condition_rule | te_common.rl_rule.rule_id |
| 23 | te_common.rl_rule_evidence.evidence_id | fk_rl_rule_evidence_evidence | te_common.ev_evidence.evidence_id |
| 24 | te_common.rl_rule_evidence.rule_id | fk_rl_rule_evidence_rule | te_common.rl_rule.rule_id |
| 25 | te_common.system_menu_button.menu_code | fk_system_menu_button_menu | te_common.system_menu.menu_code |
| 26 | te_common.system_menu_button_crud_permission.button_code | fk_button_permission_button | te_common.system_menu_button.button_code |
| 27 | te_common.system_menu_button_crud_permission.menu_code | fk_button_permission_menu | te_common.system_menu.menu_code |
| 28 | te_health_companion.ac_action.decision_id | fk_ac_action_decision | te_health_companion.dc_decision.decision_id |
| 29 | te_health_companion.dc_decision_detail.decision_id | fk_dc_detail_decision | te_health_companion.dc_decision.decision_id |
| 30 | te_health_companion.fb_feedback.action_id | fk_fb_feedback_action | te_health_companion.ac_action.action_id |
| 31 | te_health_companion.fb_feedback.decision_id | fk_fb_feedback_decision | te_health_companion.dc_decision.decision_id |
| 32 | te_story_platform.sp_knowledge_hold.knowledge_type_id | fk_sp_knowledge_type | te_story_platform.sp_knowledge_type_hold.knowledge_type_id |
| 33 | te_story_platform.sp_knowledge_relationship_hold.source_knowledge_id | fk_sp_knowledge_relationship_source | te_story_platform.sp_knowledge_hold.knowledge_id |
| 34 | te_story_platform.sp_knowledge_relationship_hold.target_knowledge_id | fk_sp_knowledge_relationship_target | te_story_platform.sp_knowledge_hold.knowledge_id |
| 35 | te_story_platform.sp_knowledge_type_hold.parent_knowledge_type_id | fk_sp_knowledge_type_parent | te_story_platform.sp_knowledge_type_hold.knowledge_type_id |
| 36 | te_story_platform.sp_object_execution_link.object_id | fk_sp_object_execution_attempt_object | te_story_platform.sp_object.object_id |
| 37 | te_story_platform.sp_work_asset.work_item_id | fk_work_asset_item | te_story_platform.sp_work_item.work_item_id |
| 38 | te_story_platform.sp_work_item.work_session_id | fk_work_item_session | te_story_platform.sp_work_session.work_session_id |
| 39 | te_story_platform.sp_work_session.parent_work_session_id | fk_work_session_parent | te_story_platform.sp_work_session.work_session_id |
| 40 | te_story_platform.sp_work_session.worker_object_id | fk_work_session_worker | te_story_platform.sp_object.object_id |

## 10. Migration 전 전체 논리 관계 43개

| No | Shared Column | Table Count | Related Tables |
|---:|---|---:|---|
| 1 | action_id | 3 | te_health_companion.ac_action, te_health_companion.at_audit, te_health_companion.fb_feedback |
| 2 | action_type_code | 2 | te_common.rl_rule_action, te_health_companion.ac_action |
| 3 | business_code | 6 | te_common.cm_repository, te_story_platform.sp_business, te_story_platform.sp_domain, te_story_platform.sp_entity, te_story_platform.sp_erd, te_story_platform.sp_object |
| 4 | business_domain_code | 2 | te_common.cm_business_domain, te_health_companion.at_audit |
| 5 | button_code | 3 | te_common.sql_guard_execution_log, te_common.system_menu_button, te_common.system_menu_button_crud_permission |
| 6 | classification_code | 2 | te_common.cm_data_classification, te_common.cm_sequence_rule |
| 7 | country_code | 2 | te_common.cm_country, te_common.cm_locale |
| 8 | data_type_code | 2 | te_common.cm_data_type, te_common.cm_repository |
| 9 | decision_id | 5 | te_health_companion.ac_action, te_health_companion.at_audit, te_health_companion.dc_decision, te_health_companion.dc_decision_detail, te_health_companion.fb_feedback |
| 10 | domain_code | 7 | te_common.cm_repository, te_common.cm_sequence_definition, te_common.cm_sequence_rule, te_story_platform.sp_domain, te_story_platform.sp_entity, te_story_platform.sp_erd, te_story_platform.sp_object |
| 11 | entity_id | 2 | te_story_platform.sp_attribute, te_story_platform.sp_entity |
| 12 | erd_id | 2 | te_story_platform.sp_erd, te_story_platform.sp_relationship |
| 13 | evidence_id | 7 | te_common.ev_evidence, te_common.ev_evidence_reference, te_common.ev_evidence_version, te_common.rl_rule_evidence, te_health_companion.at_audit, te_health_companion.dc_decision, te_health_companion.dc_decision_detail |
| 14 | format_code | 4 | te_common.cm_sequence_definition, te_common.cm_sequence_format, te_common.cm_sequence_format_definition, te_common.cm_sequence_rule |
| 15 | group_code | 3 | te_common.cm_code_inspection_result, te_common.cm_common_code, te_common.cm_common_code_group |
| 16 | identifier_target_code | 2 | te_story_platform.sp_identifier_sequence, te_story_platform.sp_object |
| 17 | knowledge_type_id | 2 | te_story_platform.sp_knowledge_hold, te_story_platform.sp_knowledge_type_hold |
| 18 | language_code | 2 | te_common.cm_language, te_common.cm_locale |
| 19 | lifecycle_id | 2 | te_common.cm_data_lifecycle_index, te_story_platform.sp_object |
| 20 | member_id | 4 | te_common.cm_login_history, te_common.cm_member, te_common.cm_member_private, te_common.cm_member_role |
| 21 | menu_code | 4 | te_common.sql_guard_execution_log, te_common.system_menu, te_common.system_menu_button, te_common.system_menu_button_crud_permission |
| 22 | object_code | 3 | te_common.md_object, te_story_platform.sp_execution_history, te_story_platform.sp_object |
| 23 | object_id | 4 | te_story_platform.sp_execution_history, te_story_platform.sp_object, te_story_platform.sp_object_execution_link, te_story_platform.sp_object_lifecycle |
| 24 | object_type_code | 2 | te_common.md_object, te_story_platform.sp_object |
| 25 | policy_code | 4 | te_common.cm_sequence_definition, te_common.cm_sequence_policy, te_common.cm_sequence_policy_definition, te_common.cm_sequence_rule |
| 26 | policy_id | 2 | te_common.cm_storage_policy, te_common.sp_policy_rule_candidate |
| 27 | prefix_code | 2 | te_common.cm_sequence_definition, te_common.cm_sequence_rule |
| 28 | query_id | 4 | te_common.cm_verified_sql_query, te_common.sql_guard_execution_log, te_common.sql_guard_verification_log, te_common.system_menu_button |
| 29 | relationship_id | 2 | te_story_platform.sp_relationship, te_story_platform.sp_relationship_attribute |
| 30 | relationship_type_code | 2 | te_story_platform.sp_knowledge_relationship_hold, te_story_platform.sp_relationship |
| 31 | repository_id | 4 | te_common.cm_data_lifecycle_index, te_common.cm_repository, te_common.cm_storage_policy, te_common.cm_storage_repository |
| 32 | role_id | 3 | te_common.cm_member_role, te_common.cm_role, te_common.cm_role_rule |
| 33 | rule_id | 8 | te_common.cm_role_rule, te_common.rl_rule, te_common.rl_rule_action, te_common.rl_rule_condition, te_common.rl_rule_evidence, te_health_companion.at_audit, te_health_companion.dc_decision, te_health_companion.dc_decision_detail |
| 34 | sequence_code | 3 | te_common.cm_sequence, te_common.cm_sequence_definition, te_common.cm_sequence_rule |
| 35 | sequence_scope_code | 2 | te_story_platform.sp_identifier_blueprint, te_story_platform.sp_object |
| 36 | target_object_id | 2 | te_story_platform.sp_object_execution_link, te_story_platform.sp_relationship |
| 37 | user_id | 6 | te_common.cm_consent_history, te_common.cm_data_lifecycle_index, te_common.sql_guard_execution_log, te_common.system_user, te_health_companion.dc_decision, te_health_companion.fb_feedback |
| 38 | user_role_code | 2 | te_common.system_menu_button_crud_permission, te_common.system_user |
| 39 | work_item_id | 2 | te_story_platform.sp_work_asset, te_story_platform.sp_work_item |
| 40 | work_result_code | 2 | te_story_platform.sp_work_item, te_story_platform.sp_work_session |
| 41 | work_session_id | 2 | te_story_platform.sp_work_item, te_story_platform.sp_work_session |
| 42 | work_status_code | 2 | te_story_platform.sp_work_item, te_story_platform.sp_work_session |
| 43 | work_type_code | 2 | te_common.cm_sequence_rule, te_story_platform.sp_work_session |

## 11. 최종 결정

- `cm_country`, `cm_language`, `cm_locale`: 공통코드 흡수와 REMOVE 완료.
- `LOCALE_CODE`라는 Group은 만들지 않는다. Group 명은 `LOCALE`로 통일한다.
- Locale의 상위 Language/Country 관계와 표시 형식은 JSON Metadata로 보존한다.
- 물리 FK가 사라진 관계는 Analyzer가 Group 및 값 존재 여부를 검증한다.
- 추가 후보는 증거 없이 함께 DROP하지 않는다.
- 실제 Migration과 실 DB 재조회는 완료했다. 남은 작업은 Schema Snapshot과 Analyzer 산출물 재생성 및 Git Commit이다.

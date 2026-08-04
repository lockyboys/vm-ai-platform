# Storage Separation Design

## File Story

MariaDB와 MongoDB의 책임을 데이터의 관계 무결성, 조회 방식, 변경성, 보존 책임을 기준으로 분리한다.

## Change History

- 20260730 | Codex | 실제 Repository inventory와 DDL을 기준으로 Storage Separation 설계를 작성한다.
- 20260730 | Codex | 임시 UI Permission Legacy Backup을 Storage 분리 대상에서 제외하고 판단 기준을 명확히 한다.

## 1. Separation Decision Rule

| 판단 기준 | MariaDB | MongoDB |
| --- | --- | --- |
| 관계 무결성 | FK·Unique·Transaction이 업무 정합성에 필요한 Master와 감사 이력 | Document 내부에 완결되고 교차 Transaction이 필요 없는 payload |
| 조회 방식 | 조건·조인·집계·상태 조회가 핵심인 Index와 운영 데이터 | 전문 본문·가변 JSON·원문·진단 payload 조회가 핵심인 데이터 |
| 변경성 | 현재 상태를 수정·승인·철회하는 업무 레코드 | Append-only Event, Log, Snapshot, 생성 결과 원문 |
| 보존 책임 | 법적·보안·동의 감사의 공식 증적 | 대용량 보관, Debug, 재현용 상세, Report 본문 |

- 접미사(history, log, report)만으로 저장소를 결정하지 않는다.
- 동일 payload를 두 저장소의 SSOT로 중복 저장하지 않는다.
- MariaDB Index는 MongoDB Document의 business identifier, 상태, 제목·요약만 보관한다.
- 임시 작업 Backup Table은 운영 Storage 대상이 아니며, 해당 작업 검증이 끝난 뒤 제거한다.

## 2. Current Candidate Classification

| Current Repository | Current Rows | Target SSOT | Why |
| --- | ---: | --- | --- |
| te_common.cm_change_history | 635 | MariaDB | Repository 변경의 공식 감사 증적이며 대상 DB·Table·Record 조건 조회가 필요하다. |
| te_common.cm_consent_history | 0 | MariaDB | 동의 획득·철회는 Member와 연결되는 법적 증적이다. |
| te_common.cm_login_history | 0 | MariaDB | Member FK와 보안 감사 조회가 필요하다. |
| te_story_platform.sp_execution_history | 12 | MariaDB Index | Runtime trace·상태의 상관관계 Index다. 상세 payload는 MongoDB Document로 분리한다. |
| te_common.sql_guard_execution_log | 0 | MongoDB | 실행 오류·결과 payload가 늘어나는 append-only 진단 Log다. |
| te_common.sql_guard_verification_log | 0 | MongoDB | 단계별 검증 message와 진단 payload를 Document로 보관한다. |
| te_common.health_report | 0 | MariaDB Index + MongoDB Document | 환자·제목·상태·일시는 MariaDB, 가변·대용량 report_content는 MongoDB 원본이다. |
| te_common.ui_menu_action_permission_legacy_20260730 | 8 | EXCLUDE | UI Permission 재설계 중 생성된 임시 Backup이며 운영 Storage 분리 대상이 아니다. |

## 3. MongoDB Collections

| Collection | Document Identifier | Source Responsibility |
| --- | --- | --- |
| runtime_execution_payload | execution_history_id | sp_execution_history의 가변 실행 상세·진단 payload |
| sql_guard_execution_log | execution_id | SQL Guard 실행 Log Document |
| sql_guard_verification_log | log_id | SQL Guard 검증 Log Document |
| health_report_document | health_report_id | health_report의 report_content 원문 |

## 4. Physical Separation Contract

- sp_execution_history에는 MongoDB Document 식별자와 요약 상태만 연결한다. 실행 payload를 MariaDB 열로 확장하지 않는다.
- health_report에는 report_content를 보관하지 않는다. MariaDB는 health_report_id, patient_id, report_title, 상태·일시와 MongoDB Document 식별자만 관리한다.
- MongoDB Log Document는 업무 식별자, 발생 일시, 실행 주체, 구조화 payload를 하나의 Document로 저장한다.
- cm_change_history, cm_consent_history, cm_login_history는 MongoDB로 이관하지 않는다.
- ui_menu_action_permission_legacy_20260730은 UI Permission 재설계 검증 완료 후 별도 정리 절차로 제거한다.

## 5. Migration Order

1. Storage Repository와 Storage Policy metadata를 등록한다.
2. MongoDB Collection Object metadata를 등록한다.
3. MariaDB retained index의 MongoDB Document reference를 설계한다.
4. 기존 행을 identifier 기준으로 멱등 이관한다.
5. source/target count, identifier set, payload checksum을 검증한다.
6. change history와 migration evidence를 등록한다.
7. 검증 완료 후에만 이관 대상 MariaDB payload를 제거한다.

## 6. Explicit Non-Decision

- Retention과 TTL은 migration code에 하드코딩하지 않는다.
- MongoDB TTL index와 disposal job은 cm_storage_policy에서 보존 정책을 확정한 뒤 생성한다.

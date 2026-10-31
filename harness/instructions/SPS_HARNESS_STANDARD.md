# SPS Harness Standard

## Core Principles

- Repository First
- Generator First
- Metadata Driven
- Single Source of Truth
- Hardcoding Prohibited

## Working Method

- Continue from the current checkpoint.
- Do not restart completed repository analysis.
- Inspect the current file and database state before modification.
- Show the file to modify.
- Show how to locate the modification point.
- Show the content before modification.
- Show the content after modification.
- Run tests after modification.
- Verify actual table structures and stored rows.
- Preserve migration evidence.

## Database Rules

- Do not hardcode physical database names in Engine code.
- Resolve logical database roles through Repository metadata.
- Use snake_case for database objects.
- Use `_dt` for datetime columns.
- Use `_no` for integer sequence numbers.
- Use `_num` for numeric values represented as strings.
- Use Object noun plus `_description`.
- Description columns use VARCHAR(2000).
- Audit columns use:
  - created_dt
  - created_by
  - updated_dt
  - updated_by
  - deleted_by
  - deleted_dt
  - program_id
  - client_ip

## Safety Rules

- Do not expose secrets.
- Do not print passwords or tokens.
- Do not modify production resources without explicit approval.
- Do not commit automatically unless explicitly requested.
- Do not perform destructive database operations without evidence and verification.

## Source Change and Regression Safety Procedure

This procedure reduces avoidable mistakes but does not guarantee defect-free code; tests cover only the executed scope.
1. **Inspect:** run `git_status`, then `source_search` and `source_read` for the target/callers/tests. Record and preserve staged/worktree changes; stop if requested work cannot be isolated.
2. **Plan:** design invalid-input and reproduction tests first; prepare the smallest patch.
3. **Dry-run/apply:** for existing files run `source_patch(dry_run=true)`; review applicability and hash, then apply only the same reviewed patch. For new files, review the change-set dry-run and require `source_write` approval. A dry-run is not a behavior test.
4. **Diff:** reread changed files and run `git_diff`; resolve unexpected changes before tests.
5. **Test before staging:** run focused tests and then the supported full regression (`run_full_test.sh` or full `pytest`). Report commands and counts. Failure blocks staging; unavailable full tests are partial/unverified.
6. **Stage:** after both test levels pass, `git_add` only explicit changed paths. Preserve unrelated staged/worktree changes and do not commit unless requested. PARTNER sets keep `stage_groups` empty until full regression passes.
7. **RELOAD/report:** reload only if runtime evidence shows the changed component is loaded by a running service. Report paths, hashes, diffs, tests, staging, RELOAD and unverified scope; never infer success from a plan, timeout, or partial run.
## MCP Response Timeout Policy

- The single MCP response-liveness limit is **150 seconds (2 minutes 30 seconds)**.
- If an MCP call returns no response within 150 seconds, stop the current MCP operation and report the tool, elapsed time, and last confirmed state. Do not silently extend or repeat the same call.
- An explicit connection or authentication failure may be reported immediately; waiting 150 seconds is not required.
- Shorter per-tool execution limits (for example, 120 seconds for source execution or an SSH request) remain valid and do not replace the 150-second client liveness limit.
- A returned job ID is a response, not proof of completion. Long jobs use their own execution budget and bounded status calls; each status call still follows this policy.
- A client timeout does not prove that a remote job stopped. Query its saved job state before submitting another job.

## MariaDB / MongoDB Payload and Execution Link Consistency

Purpose: prevent index-only saves, orphan payloads, incorrect collection routing, and false completion claims. This is a mandatory development and acceptance rule, not proof that all existing writers already comply.

### Shared implementation and boundary

- Reuse `CommonDatabase` and `MariaMongoWriteService` from `common/database.py`; do not introduce an independent dual-write implementation.
- `MariaMongoWriteService` coordinates a MariaDB transaction and compensating deletion of MongoDB documents inserted through it. It does NOT automatically create or validate `sp_object_execution_link`, resolve payload contracts, provide distributed ACID, or synchronize existing rows.
- The caller must write the source index, required execution history, MongoDB payload, and `sp_object_execution_link` through the same writer context and the same MariaDB connection. Resolve schema roles through Repository metadata.
- Where Level 4 document identifiers are required, reuse `reserve_document_master_id`. Never substitute the Level 3 MCM class identifier for a document instance identifier. Consumed identifiers are not recycled after failure.

### Required mapping baseline

The following user-supplied mapping is the required review baseline. Resolve actual roles, source keys, payload fields, cardinality, and MDB/MCO/MCM Objects from active Repository contracts plus table/column comments before execution. A name in this table alone does not prove a deployed contract or completed migration.

| MariaDB source | MariaDB retained area | MongoDB collection | Payload area |
|---|---|---|---|
| cm_verified_sql_query | Query identifiers and verification status | cm_verified_sql_query_payload | Description, SQL, verification details |
| $model_history | Model history identifiers | model_history_payload | features |
| health_report | Report basic metadata | health_report_payload | Report content and change reasons |
| cm_repository | Repository metadata | cm_repository_payload | JSON, Footer, code description |
| cm_storage_repository | Storage identifiers and policies | cm_storage_repository_payload | Change reasons and details |
| sql_guard_execution_log | Execution result index | sql_guard_execution_log_payload | Error messages |
| sql_guard_verification_log | Verification step index | sql_guard_verification_log_payload | Messages and change reasons |
| cron_logs | Cron execution metadata | cron_logs_payload | Execution messages |
| cm_code_inspection_result | Inspection result index | cm_code_inspection_result_payload | Related code and messages |
| harness_source_audit | Pipeline result index | harness_source_audit_payload | data_json |
| sp_impact_analysis_result | Impact analysis index | sp_impact_analysis_result_payload | Change and impact details |

- Preserve `$model_history` literally as supplied until metadata confirms whether it is a physical name or a family placeholder; do not expand or rename it by assumption.
- A disagreement between this baseline, Repository metadata, table comments, and physical storage blocks the affected write or migration. Report the exact disagreement; never silently route to a legacy collection or hardcode an override.
- Payload fields must not be reintroduced into the MariaDB index. Resolve the exact field list from the contract; do not infer columns from the descriptive areas above.

### Write and failure requirements

- Preflight must confirm the source primary key, active source/MDB/MCO/MCM Objects, identifier rules, collection routing, link semantics, and declared cardinality. Missing or ambiguous metadata is an error, not a fallback opportunity.
- Payload identity must be traceable to the source key and execution attempt. The link's database, collection, document identity, and target Object must resolve to the exact stored payload under the declared contract; never equate MongoDB `_id` with `mongodb_document_master_id` without a contract.
- Keep success status changes in the same MariaDB transaction. Check affected row counts and propagate source, payload, link, and commit failures; never return `saved=True` after partial success.
- Retry only with a contract-defined idempotency key. Reject conflicting content under the same key and prevent duplicate source, payload, or link records.
- Compensation may delete only the exact document created by the failed attempt, preferably by its inserted `_id`. Broad filters that can remove another attempt's documents are prohibited.
- The current shared writer compensates inserts only. UPDATE/DELETE, commit-outcome ambiguity, process crashes, rollback failure, and compensation failure require an explicitly verified recovery design before use; do not claim the context manager alone covers them.
- Preserve primary and compensation errors with attempt identifiers. Reconcile uncertain outcomes before retry; never delete original payload fields until read-back comparison and recoverable backup are verified.

### Mandatory evidence and completion gate

- Follow source_search/read -> preserved original -> patch dry-run -> hash-checked apply -> reread/diff -> focused tests and full regression -> explicit staging paths -> RELOAD decision.
- Test success, source/payload/link failure, MariaDB commit failure, compensation failure, repeated requests, and conflicting repeated content. Record unimplemented coverage explicitly.
- After saving, use SELECT and MongoDB read-back to compare source key, execution attempt, link identities, payload content/hash, expected multiplicity, missing links, orphan payloads, and duplicates. Counts alone are insufficient; optional/historical payload rules must come from metadata.
- Record command/query, time, code version/hash, dry-run/apply distinction, expected versus actual values, and raw evidence location. Completion requires zero unexplained mismatches for the declared scope and passing required tests.
- A rule document or unit test does not prove that all eleven writers, old records, migrations, or running services comply. Report those checks separately as verified or unverified.
- This mapping does not authorize historical `harness_source_audit` identifier allocation, metadata updates, or retrospective INSERTs. The user's existing exclusion remains in force.

## SPS 등록·실행 저장·실패 처리와 MongoDB 필드 규칙

목적: Repository 등록과 실행별 저장을 구분하고, MariaDB 색인·MongoDB Payload·실행 링크 및 감사 필드의 불일치를 방지한다. 기존 규칙과 기록은 유지하며 다음 절차를 추가 적용한다.

| 구분 | 순서대로 처리할 흐름 |
|---|---|
| 1회 등록 | ① Repository·table_schema·테이블/필드 COMMENT 확인 → ② IdentifierCoordinator로 object_id 생성 → ③ sp_object·sp_erd·sp_entity·sp_attribute 등록 → ④ sp_object_lifecycle 등록 → ⑤ sp_execution_history 기본 등록 → 필요 시 sp_relationship·sp_relationship_attribute·sp_metadata 등록 |
| 실행 저장 | ⑥ MariaMongoWriteService 시작 → ⑦ MariaDB cm_verified_sql_query 색인 + MongoDB SQL Payload 문서 + MariaDB sp_object_execution_link를 같은 writer 컨텍스트에서 입력 → ⑧ 세 저장 및 실행이력 결과 갱신 성공 시 MariaDB commit |
| 실행·실패 | ① object_id·Verified SQL 확인 → ② Gemini 실행 → ③ 동일 3중 저장 → ④ sp_execution_history 결과 갱신 → ⑤ 저장/commit 실패 시 MariaDB rollback 및 이번 시도에서 삽입한 MongoDB 문서 보상 삭제 |
| 증빙 | 실제 근거가 있을 때만 ev_evidence 등록. 세 저장의 재조회 일치와 실제 commit 성공 로그를 확인한 범위에서만 완료 판정 |

- 1회 등록은 Object/메타데이터 등록 흐름이다. 기존 등록 Object를 실행마다 다시 생성하지 않는다. IdentifierCoordinator와 활성 Repository 계약을 사용하며 임의 ID를 만들지 않는다.
- 등록 단계의 sp_execution_history 기본 기록과 실행별 이력은 구분한다. 각 실행 시도에는 계약상 실행 식별자와 상태를 기록하고, 해당 시도의 결과 갱신은 동일 MariaDB 저장 트랜잭션 안에서 commit 전에 완료한다.
- 위 표의 SQL Payload는 논리적 표현이다. 기존 COMMENT 매핑상 물리 컬렉션은 `cm_verified_sql_query_payload`이며, `verified_sql_payload`는 현재 문서의 payload 내부 항목이다. 컬렉션을 임의로 `verified_sql_payload`로 바꾸지 않고 활성 Repository 계약으로 확인한다.
- 같은 writer 컨텍스트의 3중 저장은 MariaDB 트랜잭션과 MongoDB 보상 삭제를 조율한다. 두 DB의 분산 ACID 트랜잭션을 뜻하지 않는다. 각 쓰기 결과·영향 행 수·링크 일치를 확인한다.
- Gemini 등 모델 실행 실패 시 성공 Payload/완료 이력을 만들지 않는다. 저장 트랜잭션이 시작된 경우 위 실패 처리를 적용한다. rollback 후 실패 이력을 남겨야 하면 별도 오류 기록 경로를 명시하고, rollback된 이력이 영구 보존됐다고 보고하지 않는다.
- commit 성공 여부가 불명확하거나 보상 삭제가 실패하면 `미확인/복구 필요`로 기록하고 저장 상태를 먼저 대조한다. 확인 없이 재시도하거나 다른 시도의 문서를 삭제하지 않는다.
- ev_evidence에는 확인된 근거만 넣으며, 문서 규칙 추가만으로 증거 행이나 실행 성공 로그를 생성하지 않는다.

### MongoDB 문서와 sp_object_execution_link 식별 필드

- sp_object_execution_link로 연결되는 MongoDB 문서에는 다음 세 필드를 최상위에 저장한다: `mongodb_database_id`, `mongodb_collection_id`, `mongodb_document_master_id`.
- 세 값은 해당 문서와 연결된 sp_object_execution_link 행의 동명 필드와 정확히 같아야 한다. 실제 DB/컬렉션 및 문서를 Repository 계약으로 해석하여 재조회로 대조한다.
- `mongodb_database_id`와 `mongodb_collection_id`에는 계약으로 해석한 식별자를 사용한다. 물리 DB명/컬렉션명을 식별자 대신 임의로 넣지 않는다.
- `mongodb_document_master_id`는 계약에 따른 Level 4 문서 인스턴스 식별자이다. Level 3 MCM 클래스 ID나 MongoDB `_id`를 임의로 대입하지 않는다.
- 링크 대상 문서는 세 필드의 필수 값이 없으면 저장 완료로 판정하지 않는다. 링크 대상이 아닌 문서에는 의미 없는 세 필드나 null 기본값을 일괄 추가하지 않는다.
- 기존 문서 보정은 별도 dry-run·백업·키별 대조 절차로 진행한다. 이 규칙 추가는 기존 문서 일괄 갱신을 의미하지 않는다.

### MongoDB 감사 필드: 실제 사건이 있을 때만 기록

| 발생 시점 | 기록할 필드 | 적용 규칙 |
|---|---|---|
| 생성 시 | created_dt, created_by, client_ip, program_id | 실제 생성 시각·실행 주체·요청 출처·프로그램을 기록하며 수정/삭제 필드를 null로 미리 넣지 않는다. |
| 실제 수정 시 | updated_dt, updated_by | 문서 내용이 실제 변경됐을 때만 기록한다. 단순 조회·동일 내용 재시도는 수정으로 보지 않으며 생성 필드는 보존한다. |
| 실제 삭제 처리 시 | deleted_dt, deleted_by | 실제 논리 삭제 처리 시 기록한다. 물리 삭제는 계약상 별도 이력에 삭제 사실을 보존한다. |

- 사건이 발생하지 않은 선택 감사 필드는 생략한다. MongoDB의 유연한 스키마를 이유로 의미 없는 null 필드를 모든 문서에 추가하지 않는다.
- 생성 감사값을 확인할 수 없으면 임의 사용자·시각·IP·프로그램 또는 null로 채우지 않는다. 계약상 필수 감사값 누락을 명시하고 처리한다.
- 시각 표현과 실행 주체는 Repository/프로젝트 계약을 따른다. 소급 보정 시 원래 생성 정보와 이번 변경 정보를 혼동하지 않는다.

이 절은 개발·검증 규칙이다. 실행 코드 반영, 전체 기존 문서 보정, 전체 서비스 적용 완료 여부는 각각 별도 증빙으로 확인한다.

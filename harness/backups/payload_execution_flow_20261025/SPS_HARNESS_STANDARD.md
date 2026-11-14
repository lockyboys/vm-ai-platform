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

# SPS 최종 증빙 전체 확인 — 2026-10-25 KST

## 결론

요청한 최종 증빙을 실제 파일·현재 Git·현재 전체 pytest·서비스 상태·스킬 검사 결과로 대조했다. **증빙이 전혀 없는 상태는 아니다. 다만 6단계 전체 완료 및 스킬 배포 완료로 판정할 수 없다.**
이번 요청은 확인 작업이므로 운영 소스·스킬 패키지·기존 테스트는 수정하지 않았고 서비스를 재기동하지 않았다. 감사용 스크립트·결과 파일만 추가했다. 사용자가 중단한 SOURCE_AUDIT 식별자 발급·메타데이터 변경·감사 행 입력은 수행하지 않았다.

감사 기준 HEAD: `92fa7bec050a89a62e503b0f4adf50ea27457dd6`. 현재 전체 회귀 전후 대상 7개 파일 해시가 동일하며, 각 대상의 작업 트리·index는 HEAD와 일치했다. 전체 저장소가 clean이라는 뜻은 아니다.

## 6단계 대조

| 단계 | 확인된 증빙 | 판정 |
|---|---|---|
| 1. 상태 파악 | 현재 source_read로 실제 구현·참조 문서·기존 증빙을 조회했다. 현재 Git·현재 해시도 확인했다. 최초 수정 당시 source_search→source_read 실행 전체 기록은 별도로 확보하지 못했다. | 현재 조회 확인 / 과거 전체 순서 미확인 |
| 2. 최소 패치·dry-run | change_set_evidence_fix_20261025.json에 역방향 확인용 post_apply_reverse_dry_run=true/applicable=true가 있다. 실행 전 정방향 dry-run을 모든 최초 변경에 연결한 완결된 기록은 확인하지 못했다. | 일부 증빙 확인 / 과거 전체 준수 미확인 |
| 3. 해시 확인·실제 반영 | patch_apply.applied=true 및 before/after SHA가 저장되어 있다. change_set_graph.py의 현재 SHA는 기록된 after_sha256과 일치한다. | 변경 세트 그래프 반영 확인 |
| 4. 재조회·diff | 저장 증빙에 diff_review가 있으며 graph 251줄/test 286줄·truncated=false다. 현재 대상 파일을 재조회했다. 현재 그래프 git diff는 비어 있고 대상 7개 파일이 HEAD와 일치한다. 과거 테스트 파일의 after SHA와 현재 SHA는 달라 이후 변경과 현재 회귀를 구분했다. | 현재 상태 확인 |
| 5. 단위·전체 회귀 | 과거 730 passed/0 failed/0 skipped의 개별 730 결과·raw_stdout·exit_code=0이 실제 존재한다. 현재 전체 재실행은 788 passed/4 failed/0 skipped다. | 과거 통과 확인 / 현재 전체 회귀 실패 |
| 6. staging·RELOAD | 핵심 변경은 c26b32b에 커밋되어 있고 현재 대상은 index/HEAD와 일치한다. Harness 기동은 PARTNER·변경 세트 소스 변경 이후이나 최신 Git 도구 변경 이전이다. Gemini는 현재 파일 변경 이전부터 실행 중이다. | 커밋 확인 / 최신 전체 RELOAD 완료 아님 |

초기 기록의 39건·17건 실행 전체 원문과 단일 실행 ID 연결은 이번 조사에서 별도로 확보하지 못했다. 현재 테스트 결과로 그 과거 실행 기록을 소급 생성하지 않았다.

## 현재 전체 회귀 원문 확인

실행: `pytest tests/`

- 결과: **788 passed, 4 failed, 5 warnings in 53.37s**, 종료 코드 1.
- skip: **0**.
- 백업이 아닌 테스트: **734건 전부 통과**.
- 파일명에 BACKUP 또는 _backup이 포함된 테스트: **54건 통과·4건 실패**.
- 위 구분은 같은 전체 실행 결과를 분류한 것이다. 백업을 제외하고 재실행하거나 실패를 숨긴 결과가 아니다.
- 감사 중 pytest 수집 설정·테스트 파일·백업을 변경하지 않았다.

실패 4건은 모두 다음 백업 파일에서 수집됐다.

`tests/harness/mcp/test_verified_sql_registration_tools_BACKUP_20261025_051403.py`

1. test_verified_sql_register_allocates_identifier_and_inserts_once
2. test_verified_sql_register_rolls_back_when_mcm_table_identifier_is_not_level4
3. test_verified_sql_register_inserts_supplied_evidence_in_same_transaction
4. test_verified_sql_register_link_failure_compensates_payload

공통 실패 경로: 현재 verified_sql_tools가 Repository Rule 계약을 조회하지만, 백업의 오래된 fetch_all 테스트 대역은 SQL에 FROM sp_object가 있어야 한다고 단정한다. 현재 정식 `test_verified_sql_registration_tools.py`의 **14건은 통과**했다.

요청 핵심 테스트:
- `tests/harness/mcp/test_source_partner_agent.py`: 7 passed
- `tests/harness/mcp/test_sps_change_set_tool.py`: 22 passed
- `tests/harness/mcp/test_mutation_tool_extensions.py`: 8 passed
- `tests/harness/mcp/test_verified_sql_registration_tools.py`: 14 passed

PARTNER·변경 세트·Git 확장 세 파일 합계는 **37건 통과**다. 정식 Verified SQL 등록 테스트 14건을 합치면 위 네 파일은 51건 통과다.

## 구현 연결 확인

- 단일 `_build_model()`이 config.py의 provider/model/base URL/timeout을 읽어 Gemini 또는 Ollama를 생성한다.
- 지원하지 않는 provider는 ValueError로 거부한다.
- `build_source_partner_graph`는 같은 MessagesState 그래프와 ToolNode 왕복 구조를 사용한다.
- 기존 `execute_change_set`가 `run_change_set`을 호출한다.
- 현재 변경 세트 그래프의 실제 경로: validate → patch_check → apply_patch → test → stage_apply → commit 또는 evidence. 테스트 실패는 rollback → evidence다.
- dry-run 경로는 stage_plan → evidence로 연결된다.
- evidence 노드는 patch_plan, source_before_sha256, source_after_sha256, patch_result, test_result, staged_groups, commit_result, activation을 저장한다.
- 이 연결과 현재 테스트 통과가 최초 수정 당시 6단계를 모두 순서대로 수행했다는 증거를 대신하지는 않는다.

## 현재 파일 해시와 커밋

| 파일 | SHA-256 | 최근 커밋 |
|---|---|---|
| `config.py` | `0010f705e8e1060388e52f04db343ba711c8f81e8ed792bd69b5827bb23f4c50` | f0c523a 2026-10-25T05:12:03+09:00 feat(stock): add evidence-based screening without trading operations |
| `haness/mcp/agents/source_partner_agent.py` | `181460da414213295740c4ec3c856b0c25f6b5983047e943eb8d4c2ea1319c22` | c26b32b 2026-10-25T05:11:26+09:00 feat(partner): select providers and verify change-set staging evidence |
| `haness/mcp/tools/change_set_graph.py` | `3e27676dfc25adfede3bb24dba90c7da97f14d411fed3e694a92303ff6ee38d9` | c26b32b 2026-10-25T05:11:26+09:00 feat(partner): select providers and verify change-set staging evidence |
| `harness/mcp/tools/git_mutation_tools.py` | `8c2b0eb0dc581bc943b63595e8111b694e0e981079fe3ca970951c0a70e4ab72` | 358a0a7 2026-10-25T06:17:26+09:00 feat(git): add keep_other_staged partial commit to git_commit for splitting accumulated stages (Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>) |
| `tests/harness/mcp/test_source_partner_agent.py` | `03c88fc146b5132eb1ea43c88ea304f77ae9a53d258a166adbe5cc9c3b8e4e70` | c26b32b 2026-10-25T05:11:26+09:00 feat(partner): select providers and verify change-set staging evidence |
| `tests/harness/mcp/test_sps_change_set_tool.py` | `46859ba41c929307e9f3d52d485c7d964db8c807d6de976c9473583821975725` | c26b32b 2026-10-25T05:11:26+09:00 feat(partner): select providers and verify change-set staging evidence |
| `tests/harness/mcp/test_mutation_tool_extensions.py` | `48c0a39eee35d3fa82c70f09cef92805d34c89f76cbb23a794a996c7c245efcf` | c26b32b 2026-10-25T05:11:26+09:00 feat(partner): select providers and verify change-set staging evidence |

모든 위 파일: worktree vs HEAD clean, index vs HEAD clean.
change_set_graph.py는 기존 반영 증빙의 after SHA와 일치한다.
test_sps_change_set_tool.py는 저장 당시 SHA와 현재 SHA가 다르며, 현재 c26b32b 버전은 이번 전체 실행에서 22건 통과했다. 단순 해시 차이만으로 변조나 결함으로 판단하지 않는다.

## RELOAD 실제 시각

| 서비스 | 현재 시작 시각(KST) | 관련 소스 변경 시각(KST) | 판단 |
|---|---|---|---|
| sps-harness.service | 2026-10-25 06:00:29 | source_partner_agent: 10-24 22:56:45 / change_set_graph: 10-25 03:13:54 | 기동 시각은 두 핵심 파일 변경 이후 |
| sps-harness.service | 2026-10-25 06:00:29 | git_mutation_tools: 10-25 06:16:06 | 최신 Git 도구 변경 이후 재기동 증빙 없음 |
| sps-gemini-agent.service | 2026-10-23 20:16:25 | sps_gemini_agent: 10-25 03:29:55 | 현재 프로세스는 파일 변경 이전부터 실행 중 |

두 서비스 모두 active/running이다. 기동 시각 비교는 관측 근거이며, 핫리로드나 개별 함수의 실제 메모리 코드 버전까지 입증하지 않는다. 최신 Git 도구·Gemini 소스의 운영 반영은 재기동 또는 별도 런타임 검증이 필요하다. 이번 감사에서는 재기동하지 않았다.

## 스킬 패키지 검사

대상: `/data/vm_project/outputs/sps-orchestrator`

- skill-creator의 실제 quick_validate.py를 실행한 결과: **Skill is valid!**
- SKILL.md, agents/openai.yaml, 본문에 선언된 architecture/delivery/assurance/operations 참조는 존재한다.
- 사용자 기록에 제시된 **references/mcp-change-set-contract.md는 없다**.
- references 디렉터리 목록에는 Python 공개용 소스 사본이 확인되지 않았다.
- 현재 SKILL.md 및 선언된 개발·검증·운영 참조는 일반적인 구현/검증 지침이며, 요청한 MCP 6단계·stage_patch_groups 계약을 연결해 강제하는 문구는 확인되지 않았다.
- 형식 검증 통과가 요청한 기능 계약 충족이나 공개용 소스 동기화 완료를 뜻하지 않는다.
- 현재 패키지의 이전 버전과 삭제/변경 경위는 미확인이다. 사용자 기록과 현재 패키지가 다르다는 사실만 확인했다.

## 완료 전에 남은 일

1. 백업 테스트 파일을 보존하면서 정식 pytest 수집 범위와 분리할 방식을 정하고 전체 회귀를 재검증한다.
2. 요청한 스킬 기능 범위를 확정한 뒤 6단계 계약 문서와 SKILL.md 연결, 필요한 공개용 참조 사본을 복구·동기화하고 다시 검증한다.
3. 최신 Git 도구와 Gemini 변경의 RELOAD 필요 여부를 확정하고 승인된 운영 범위에서 재기동·검증한다.
4. 최초 실행의 누락된 기록을 찾지 못하면 해당 과거 준수 여부는 미확인으로 유지한다. 현재 재검증 증빙과 구분한다.

## 서버 원문 증빙

- harness/memory/change_set_evidence_fix_20261025.json
- harness/memory/regression_verification_20261025.json
- harness/memory/final_change_set_evidence_audit_20261025.json
- harness/memory/final_full_regression_audit_20261025.json
- harness/memory/final_reload_evidence_audit_20261025.json

기존 증빙 파일을 덮어쓰거나 과거 실패 기록을 지우지 않았다.

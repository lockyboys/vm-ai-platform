# 스스로 고치는 소스 리뷰 앱 (Self-fixing Source Review App)

> 사람과 AI가 모두 읽고 그대로 따라 할 수 있도록 쓴 사용 설명서입니다. (2026-11-11, LuckyBoys 요청)
> 이 문서와 소스의 주석이 다르면 **소스가 기준**입니다. 바뀌면 이 문서도 함께 고칩니다.

## 1. 한 줄 요약

AI가 Python 소스를 리뷰해 **고친 전체 소스**를 내면, 앱이 **테스트로 더 나아졌는지 확인해 스스로 반영**하고,
아니면 **되돌린 뒤 실패한 테스트를 같은 AI에게 돌려줘 다시 고치게** 합니다. Git 커밋은 사람이 지시합니다.

## 2. 어디서나 쓰는 법 (대상 파일은 아무 Python 소스나 가능)

| 순서 | 할 일 | 예 |
|---|---|---|
| ① | 고칠 소스와, 그 소스의 **정답 동작을 확인하는 pytest 파일**을 준비한다 | `my/pkg/foo.py`, `harness/tests/test_foo.py` |
| ② | dry-run으로 계획만 확인한다(AI·Python 실행 없음) | `review_python_source(source_path="my/pkg/foo.py", test_paths=["harness/tests/test_foo.py"], provider="openai")` |
| ③ | 실행한다 → `job_id`를 받는다 | 위와 같고 `dry_run=False` |
| ④ | 같은 `source_path` + `job_id`로 결과를 조회한다 | `review_python_source(source_path=..., job_id=...)` |
| ⑤ | 결과를 사람이 보고 커밋 여부를 정한다 | `git_add` → `git_commit` (push 안 함) |

- `test_paths`는 `tests/` 또는 `harness/tests/` 안만 허용한다(그 밖은 실행 전에 거부).
- **테스트가 곧 명세다.** docstring에 없는 값(기본값·상수·모양)을 테스트가 요구하면 AI는 맞힐 수 없다.
  → 명세(docstring)에 정답 근거를 먼저 적는다(2026-11-11 테트리스 시험에서 확인).

## 3. 동작 순서 (job 하나)

| 단계 | 담당 모듈 | 하는 일 |
|---|---|---|
| 1 리뷰 | `FastAPI/LangGraph/multi_persona/multi_persona_agent_gemini.py` + `common/llm_provider.py` | 고른 AI(gemini·openai·claude·ollama)가 페르소나 순서로 진단하고 전체 수정 소스를 쓴다 |
| 2 계약 검사 | `FastAPI/LangGraph/multi_persona/review_contract.py` | 제목 3개·전체 코드 블록·문법·심볼 보존·import 실존 검사 → 통과 시 `proposed.py` |
| 3 적용 | `harness/mcp/tools/auto_apply.py` | 원본 백업 → 기준선 테스트 → 교체 → 컴파일 → 테스트 → 판정 |
| 4 판정(improve) | 같은 모듈 | **원래 통과하던 테스트를 하나도 깨지 않고 통과 수가 늘면 적용**(일부만이면 `partial=True`), 아니면 되돌림 |
| 5 피드백 재시도 | `harness/mcp/tools/multi_persona_tools.py` | 되돌려지거나 일부만 적용되면 실패 테스트(기대값·실제값)를 `round2/feedback.txt`로 만들어 같은 AI에게 직전 수정안과 함께 다시 리뷰 → 3·4 반복 |

## 4. 설정 (루트 `config.py`, 하드코딩 금지)

| 이름 | 현재 값 | 뜻 |
|---|---|---|
| `MULTI_PERSONA_REVIEW_AUTO_APPLY` | `True` | 자동 적용 기본값(호출 인자 `auto_apply`가 우선) |
| `MULTI_PERSONA_AUTO_APPLY_POLICY` | `"improve"` | `"all_pass"`(전부 통과해야 적용) 또는 `"improve"` |
| `MULTI_PERSONA_AUTO_APPLY_MAX_ROUNDS` | `2` | 1차 + 피드백 재시도 횟수(1 이하면 재시도 없음) |
| `MULTI_PERSONA_AUTO_APPLY_RETRY_MIN_SECONDS` | `180` | 재시도를 시작하려면 남아 있어야 하는 시간(초) |
| `MULTI_PERSONA_AUTO_APPLY_FEEDBACK_MAX_FAILURES` | `40` | 피드백에 넣는 실패 테스트 최대 개수 |
| `MULTI_PERSONA_REVIEW_TIMEOUT_SECONDS` | `3590` | job 하나의 전체 제한 시간(라운드 포함) |
| `MULTI_PERSONA_REVIEW_PROVIDERS` / `MULTI_PERSONA_LLM_PROVIDERS` | gemini·openai·claude·ollama | AI 선택과 모델·키 환경변수 이름 |

## 5. 결과 읽는 법 (`harness/memory/source_reviews/job_<id>/result.json`)

| 키 | 뜻 |
|---|---|
| `model_verified` | AI 검토 통과 + 출력 계약 통과 + `proposed.py` 생성 (형식 검증일 뿐, 정답 보증 아님) |
| `auto_apply_result.applied` / `partial` / `rolled_back` / `reason` | 최종 반영 여부와 이유 |
| `auto_apply_result.tests_passed_before` / `tests_passed_after` / `tests_total` | 적용 전·후 통과 테스트 수 |
| `auto_apply_rounds` | 라운드별 결과 목록(1차, 2차 …) |
| `final_proposed_path` | 마지막 라운드 수정안(채점·비교는 이 파일로) |
| 백업 | `job_<id>/original.py`, `job_<id>/round<N>/original.py` (원본 보존) |

## 6. 안전 규칙

- 원본은 항상 백업 후 교체하고, 실패하면 바이트 그대로 복원한다.
- 리뷰 도중 원본이 바뀌면(해시 불일치) 덮어쓰지 않는다.
- 비밀값은 출력·피드백 파일에 남기지 않는다(`_mask_secrets`).
- 테스트 없이 호출하면 문법만 맞아도 반영되므로 **중요 파일은 반드시 `test_paths`를 준다**.
- 자동 커밋·push는 하지 않는다.

## 7. 검증 기록 (2026-11-11)

| 항목 | 결과 |
|---|---|
| 어려운 시험(오류 100개 × 계산기·테트리스) | ChatGPT·Claude 모두 100/100 (Claude는 피드백 2차에서 마지막 1~2건 해결) |
| 과적합 점검(무작위 입력 차분 시험) | 다 고친 4개 파일, 계산기 12,900·테트리스 9,300 입력에서 정답과 불일치 0건 |
| 관련 단위 테스트 | 116 passed / 전체 회귀 1065 passed (실패 5건은 일부러 버그를 둔 데모 원본 테스트) |
| 미확인 | Gemini(크레딧 소진)·Ollama(터널 꺼짐) 재실행 |

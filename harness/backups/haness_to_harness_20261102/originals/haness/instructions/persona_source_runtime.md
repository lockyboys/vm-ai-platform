# SPS 동적 페르소나 소스 실행

기존 run_sps_orchestrator의 JSON mode=persona_source로 실행한다. 별도 MCP 서버를 만들지 않는다. 기존 검토·source_agent·change_set 경로는 보존한다.

## 입력과 계획

입력은 target_path(현재 haness/apps 아래 Node/JS 앱), goal, source_write_confirmed이다. 오류 위치·원인·수정식을 입력할 필요가 없다. ORCHESTRATOR가 기존 13개 역할 프롬프트 중 필요한 역할과 순서를 JSON으로 선택한다. 고정 순서·전원 호출·실패 시 고정 대체 계획은 없다. PROMPT_ENGINEER는 사용자 요청에 LangChain/LangGraph가 포함될 때만 선택 가능하다. 호출 수·시간·출력 길이 제한은 루트 config.py의 SPS_PERSONA_SOURCE에 있다.

시작 요청:
```json
{"mode":"persona_source","target_path":"haness/apps/scientific_calculator_20261025","goal":"정상·오류·경계 조건을 조사하고 직접 테스트하며 발견 결함을 최소 수정 후 재검증하라","source_write_confirmed":true}
```

조회 요청은 같은 도구에 {"mode":"persona_source","job_id":"발급된32자리job_id"}를 전달한다. dry_run=true는 모델·테스트·쓰기를 시작하지 않는다.

## 도구 연결과 증빙

선택 역할들은 한 LangGraph 메시지 상태를 공유한다. 도구 결과는 같은 역할로 돌아가며 재계획 노드로 되돌아가지 않는다. 다음 역할 호출 전에 명시적 인계 사용자 턴을 추가하여 Gemini API의 메시지 계약을 지킨다. TESTER만 새 tests/*.test.cjs를 추가하고 PARTNER만 기존 앱 js/html/css를 패치한다. 기존 테스트는 수정할 수 없고 원본 해시로 검증한다. 원본 소스와 unified diff를 저장하며 공통 source_patch의 dry-run→적용→전체 Node 테스트를 수행한다. 실패하면 해당 소스 바이트를 복구한다. 임의 셸 명령·서비스 재시작·업무 DB·Git commit/push 도구는 제공하지 않는다.

verified는 실제 모델 도구 실행으로 테스트가 수행되고 마지막 성공 테스트의 파일 해시와 현재 파일 해시가 같을 때만 참이다. autonomous_repair_proven은 여기에 실제 실패·적용된 패치·재검증 성공이 모두 있을 때만 참이다. 말로만 완료했다고 해도 통과가 아니다. Node 프로세스 종료 코드 기반 검증이며 실제 Chromium UI 검증을 자동 실행했다고 주장하지 않는다.

## 서비스 중단 없는 실행

기존 MCP 프로세스가 이전 공개 함수를 보유해도 최신 별도 워커가 persona_source 요청을 중계한다. 실행 워커는 기존 _systemd_command의 계정·환경을 재사용한 독립 transient unit에서 실행한다. setsid만으로 부모의 systemd cgroup을 벗어났다고 간주하지 않는다. 중계 워커 종료 후에도 별도 작업은 계속된다. MCP 서비스 재시작이 필요하지 않다.

새 작업은 최신 Python 소스를 import한다. 진행 중인 Python 프레임 자체를 제자리에서 갈아끼우는 기능은 아니다. 계산기 소스 패치 후 테스트는 새 Node 프로세스를 실행하므로 같은 그래프 작업 안에서 최신 소스로 재검증하고 다음 역할로 진행한다.

개별 도구 예외는 ToolNode 오류 결과로 반환되어 모델이 확인한다. 역할 마지막 호출은 도구를 닫고 증빙 인계를 위해 예약한다. 모델 타임아웃·전체 LLM 예산 초과는 해당 작업 실패 결과로 저장되며 MCP 서비스를 종료하지 않는다. 시스템 제한으로 워커가 결과를 쓰지 못하고 종료돼도 조회는 FAILED/STATUS_UNAVAILABLE를 반환하여 영구 RUNNING으로 숨기지 않는다.

요청·기동 메타·역할 계획·모델 도구 호출·실제 테스트 출력·패치 전 원본·최종 판정은 harness/memory/persona_source_jobs/<job_id>/에 보존한다. 기존 테스트 및 서비스 상태를 유지하는 연결 기능의 격리 테스트와, 실제 계산기에 대한 자율 결함 발견/수정 증빙은 구분한다.

## 실패 후 재계획과 자기 테스트 정정

마지막 실제 검증이 실패하면 원래 목표와 실제 실패 로그를 보고 ORCHESTRATOR가 다시 역할·순서를 선택한다. config.SPS_PERSONA_SOURCE.max_plan_rounds(현재 2)와 전체 호출 예산 안에서만 재계획하며, 고정된 수정 역할 목록을 강제로 넣지 않는다.

원래 존재하던 사용자 테스트는 계속 해시로 보호한다. TESTER가 이 작업에서 생성한 새 테스트의 잘못된 가정을 발견하면 revise_test가 생성 이력·현재 해시·정정 이유를 검사하고 수정 전후 파일과 이유를 보존한다. 원본 사용자 테스트, 다른 세션이 변경한 테스트, 소유 증빙 없는 파일은 정정할 수 없다. 새 테스트 실패를 제품 결함으로 단정해 제품을 잘못 고치지 않도록 실패 원인을 구분한다.

실패로 종료된 작업은 동일 앱의 resume_job_id로 이어갈 수 있다. 기존 요청·검증 스냅샷·test_created/test_revised 증빙과 현재 해시가 일치해야 생성 테스트 소유권을 이어받는다. 실행 중인 작업이나 검증 완료 작업을 복제하여 재시작하지 않는다.

역할 도구 예산에 도달하면 모델의 중지 지시 준수에 의존하지 않고 실행기가 증빙을 인계한다. budget_handoffs에 조사 한도에 걸린 역할을 표시하며, 해당 역할이 모든 조사를 끝냈다는 뜻으로 해석하지 않는다.

상태 조회는 역할·이벤트 등 작은 메타정보만 반환한다. 긴 테스트 소스·모델 응답·로그는 trace.jsonl에 보존하므로 MCP 미리보기 길이 때문에 상태 JSON이 잘리지 않는다.

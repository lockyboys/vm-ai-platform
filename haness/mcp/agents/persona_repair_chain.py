"""자기 수리용 페르소나 체인 (2026-10-25 LuckyBoys 승인: SPS ORCHESTRATOR 실행 방식 + 원문 프롬프트 그대로).

라운드별 실행 방식 (LuckyBoys 2026-10-25: "고정 순서 체인은 처음 한 번만, 두 번째는 ORCHESTRATOR 자율, 마지막만 지정")
    1라운드(fixed)      : ORCHESTRATOR(계획 표) → BUG_HUNTER → PARTNER → REVIEWER → TESTER → PARTNER(통합)
                          순서는 config first_round_plan으로 고정. ORCHESTRATOR는 계획 표만 쓴다.
    2라운드~(autonomous): ORCHESTRATOR가 13개 원문 프롬프트 중(자신 제외) 필요한 페르소나와 '순서'를 직접 정한다.
                          마지막 줄 'PLAN: A, B, C'. 프로그램이 정하는 것은 마지막 PARTNER(통합) 하나뿐이다.
    공통: ORCHESTRATOR 제외 호출 수는 config max_personas(스킬 기본 5) 이하(마지막 PARTNER 포함).
          PLAN 줄이 없으면 PLAN_INVALID(추측 실행 금지), PARTNER가 없으면 NO_CHANGE(고칠 담당 없음).
    각 단계 시스템 프롬프트 = config persona_dir/<이름>.md 원문(변경 없음). 단계 지시는 사람 메시지에 넣는다.

단계별 도구 권한 (호출 경계에서 고정 — 모델 출력으로 바꿀 수 없음)
    PARTNER(수정, 계획 안 첫 PARTNER) : 읽기 도구 + read_repair_source/repair_source(haness/source_repair.py 하나로 통일,
                                        2026-10-25). allowed_paths 밖은 엔진 호출 전 거부, dry_run=False 고정, git add까지만
    TESTER·ORCHESTRATOR·PARTNER(통합): 도구 없음(판단·정리만). TESTER는 프로그램이 실행한 회귀 결과로 판정
    그 밖의 페르소나(BUG_HUNTER·REVIEWER·ARCHITECT 등): 읽기 도구만(search/read/git status/diff)

판정 (프로그램이 결정, LLM 말만 믿지 않음)
    PLAN_INVALID / NO_CHANGE / REVIEW_BLOCKED(REVIEWER 'VERDICT: HOLD') /
    TEST_FAILED(변경 후 회귀 테스트 실패 또는 TESTER 'VERDICT: PASS' 아님) / PASS

설정: 루트 config.py / 공통 함수: common/common_function.py (일반 지침 4). DB 사용 없음.
"""
from __future__ import annotations

import asyncio
import json
import re
import subprocess
import sys
from pathlib import Path
from typing import Any, Callable, TypedDict

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import config  # noqa: E402 - 루트 공통 설정(일반 지침 4)
# 공통 함수(일반 지침 4). web_search: Tavily 웹 검색 공통 함수(20261025 | 요청: LuckyBoys | 작성: Claude)
from common.common_function import (WebSearchUnavailable, now_kst_iso,  # noqa: E402
                                    web_search)
from common.persona_source import PersonaSource  # noqa: E402 - 페르소나 공통 기능(2026-10-25 common으로 분리)

_SETTINGS = config.AUTODISCOVER_SELF_REPAIR
# 프롬프트 로드·계획·판정 해석은 persona_source_runtime과 같은 공통 클래스를 쓴다(중복 구현 제거).
_PERSONAS = PersonaSource(_SETTINGS["persona_dir"])
MAX_CARRY_CHARS = 3000    # 다음 단계로 넘기는 앞 단계 산출물 길이 상한(토큰·지연 억제)

# 사람 메시지에 붙이는 단계 지시(페르소나 원문 프롬프트는 건드리지 않는다).
STEP_INSTRUCTIONS = {
    "ORCHESTRATOR_FIXED": "1라운드는 순서가 고정이다: {fixed} → PARTNER(통합). 이 순서로 각 단계의 입력·출력·실패 처리를 "
                          "표로 계획하라.",
    "ORCHESTRATOR_AUTO": "앞 라운드가 실패했다(아래 이전 시도 참고). 이번에는 네가 직접 설계·계획한다. 페르소나 {all} 중 "
                         "꼭 필요한 것만 골라 실행 순서까지 정하라(코드 수정이 필요하면 PARTNER 포함, 최대 {cap}개). "
                         "최종 통합 PARTNER는 자동으로 붙는다. 단계·담당·입출력·실패 처리를 표로 쓰고, "
                         "마지막 줄은 반드시 PLAN: 페르소나1, 페르소나2 형식으로(쓴 순서대로 실행된다).",
    "BUG_HUNTER": "읽기 도구로 원인을 코드에서 확인하라(소스 변경 도구 없음). haness/tests/ 아래 새 파일로 넣을 "
                  "재현 테스트(잘못된 입력 포함, 네트워크·브라우저 없이) 전체 코드를 ```python 블록 하나로 제시하라.",
    "PARTNER_FIX": "read_repair_source로 대상 파일과 sha256을 읽고, 재현 unittest(앞 단계 산출물이 있으면 그것, 없으면 직접 "
                   "작성, SOURCE_PATH 후보 대상·원본에서 실패)를 regression_test로, 원인 수정은 old_code(정확히 한 번 나오는 "
                   "원문)→new_code로 넣어 repair_source를 한 번 실행하라. 고칠 수 있는 소스: {allowed}. 적용되면 git add까지만 "
                   "되고 프로그램이 {tests}를 실행한다. PRE_COMMIT_REQUIRED면 그대로 보고하라. 도구 결과에 없는 성공은 주장하지 마라.",
    "REVIEWER": "get_git_diff(staged=true)로 실제 staged 변경을 읽고 진단만 하라(수정 금지). 사이트 이름·URL 하드코딩, "
                "무관한 수정, 주석 누락, 테스트 약화를 확인하라. 마지막 줄은 반드시 VERDICT: APPROVE | CONDITIONAL | HOLD.",
    "TESTER": "아래 회귀 테스트 실행 결과(프로그램이 실제 실행)를 증거로 판정하라. 표: 항목·기대값·실제값·증거·판정. "
              "마지막 줄은 반드시 VERDICT: PASS | FAIL.",
    "GENERIC": "네 역할 범위에서 이 실패 해결에 필요한 분석·설계를 하라. 읽기 도구만 있고 소스는 바꿀 수 없다. "
               "결과는 다음 단계(특히 PARTNER)가 바로 쓸 수 있게 구체적으로.",
    "PARTNER_FINAL": "앞 단계 결과를 통합해 변경·검증·남은 위험을 3~4줄 + 표로 보고하라. 실행하지 않은 것은 미확인으로.",
}


def load_persona_prompt(persona: str) -> str:
    """페르소나 원문 프롬프트를 그대로 읽는다(공통 PersonaSource.load — 없으면 예외, 대체 없음)."""
    return _PERSONAS.load(persona)


def available_personas() -> list[str]:
    """persona_dir에 원문 파일이 있는 페르소나(ORCHESTRATOR 제외). 자율 계획의 선택지."""
    return _PERSONAS.available()


def parse_verdict(text: str) -> str:
    """산출물의 마지막 'VERDICT: X'를 읽는다. 없으면 '미확인'(공통 PersonaSource.parse_verdict)."""
    return _PERSONAS.parse_verdict(text)


def parse_plan(text: str, allowed: list[str]) -> tuple[list[str] | None, list[str]]:
    """ORCHESTRATOR 마지막 'PLAN:' 줄 → (쓴 순서대로 고른 페르소나, 무시된 이름). PLAN 줄이 없으면 (None, []).

    - 순서는 ORCHESTRATOR가 쓴 순서 그대로(자율 설계). 중복은 첫 번째만 남긴다.
    - 마지막 통합 PARTNER 1회를 포함해 max_personas 이하로 자른다(앞쪽 우선).
    """
    # 상한은 호출 시점 설정을 읽는다(테스트·운영에서 바꿀 수 있게). 해석 규칙은 공통 클래스에 있다.
    return _PERSONAS.parse_plan_line(text, allowed, int(_SETTINGS["max_personas"]))


def _human_message(task: str, carried: list[tuple[str, str]], instruction: str) -> str:
    """원래 실패 작업문 + 앞 단계 산출물(길이 제한) + 이번 단계 지시를 한 메시지로 만든다."""
    parts = [f"[실패 작업]\n{task}"]
    parts += [f"[{persona} 산출물]\n{text[:MAX_CARRY_CHARS]}" for persona, text in carried]
    parts.append(f"[이번 단계 지시]\n{instruction}")
    return "\n\n".join(parts)


# ---------------------------------------------------------------------------
# PARTNER 수정 도구 = haness/source_repair.py (2026-10-25 LuckyBoys: "source_repair.py 하나로 통일, git add까지만")
# ---------------------------------------------------------------------------
REPAIR_TOOL_NAMES = ("read_repair_source", "repair_source")
_REPAIR_REQUIRED = ("old_code", "new_code", "regression_test", "expected_sha256")


def source_repair_tool_call(name: str, arguments: dict, repair: Any = None) -> str:
    """PARTNER가 부르는 수정 도구 한 번을 실행하고 결과를 JSON 문자열로 돌려준다(예외를 던지지 않음).

    입력: name(read_repair_source | repair_source), arguments(모델이 준 인자), repair(테스트용 대역, 기본 haness.source_repair)
    출력: 엔진 보고서 JSON, 또는 {"success": false, "error_code": ..., "error": ...}
    호출 경계에서 고정하는 것(모델이 바꿀 수 없음):
      - 경로: config AUTODISCOVER_SELF_REPAIR['allowed_paths']에 정확히 있는 것만(엔진 허용 목록의 부분집합) → 아니면 PATH_NOT_ALLOWED
      - dry_run: 항상 False(검증 통과 시 백업 → 적용 → git add, 커밋은 사람이)
    오류 코드: UNKNOWN_TOOL / PATH_NOT_ALLOWED / INVALID_REQUEST(인자·검증 실패) / PRE_COMMIT_REQUIRED(대상 미커밋)
              / APPLY_ROLLED_BACK(적용 후 재검증 실패로 원복) / REPAIR_LOCKED(다른 수정 진행 중)
    """
    def fail(code: str, message: str) -> str:
        return json.dumps({"success": False, "error_code": code, "error": message}, ensure_ascii=False)

    if name not in REPAIR_TOOL_NAMES:
        return fail("UNKNOWN_TOOL", f"허용되지 않은 수정 도구: {name}")
    args = arguments if isinstance(arguments, dict) else {}
    path = args.get("file_path")
    if not isinstance(path, str) or path not in list(_SETTINGS["allowed_paths"]):
        return fail("PATH_NOT_ALLOWED", "자율 수리 허용 목록 밖 파일입니다")
    if name == "repair_source" and any(not isinstance(args.get(k), str) or not args.get(k).strip()
                                       for k in _REPAIR_REQUIRED):
        return fail("INVALID_REQUEST", "old_code·new_code·regression_test·expected_sha256가 모두 필요합니다")
    if repair is None:
        from haness import source_repair as repair   # 실제 엔진(지연 import: 테스트는 대역 주입)
    try:
        if name == "read_repair_source":
            result = repair.read_repair_source(path)
        else:
            result = repair.repair_source(path, args["old_code"], args["new_code"], args["regression_test"],
                                          args["expected_sha256"], dry_run=False)
    except repair.PreCommitRequired as error:      # ValueError 하위 → 먼저 잡는다
        return fail("PRE_COMMIT_REQUIRED", str(error))
    except BlockingIOError as error:               # repair.lock을 다른 수정이 잡고 있음
        return fail("REPAIR_LOCKED", str(error) or "다른 수정이 진행 중입니다")
    except ValueError as error:
        return fail("INVALID_REQUEST", str(error)[:800])
    except RuntimeError as error:                  # 적용 후 재검증 실패 → 엔진이 원본으로 복구함
        return fail("APPLY_ROLLED_BACK", str(error)[:800])
    return json.dumps(result, ensure_ascii=False, default=str)


def build_source_repair_tools() -> list:
    """PARTNER(수정) 단계에만 붙이는 LangChain 도구 2개(read_repair_source, repair_source)."""
    from langchain_core.tools import StructuredTool

    def read_repair_source(file_path: str) -> str:
        """허용 소스 한 파일의 내용·sha256·Git 기준 상태를 JSON으로 읽는다(수정 전 반드시 호출)."""
        return source_repair_tool_call("read_repair_source", {"file_path": file_path})

    def repair_source(file_path: str, old_code: str, new_code: str, regression_test: str, expected_sha256: str) -> str:
        """old_code(정확히 한 번)→new_code 수정을 재현 unittest로 검증(원본 실패·후보 통과)한 뒤 백업·적용·git add 한다."""
        return source_repair_tool_call("repair_source", {
            "file_path": file_path, "old_code": old_code, "new_code": new_code,
            "regression_test": regression_test, "expected_sha256": expected_sha256})

    return [StructuredTool.from_function(read_repair_source), StructuredTool.from_function(repair_source)]


def web_search_tool_call(query: str, search_fn: Any = None) -> str:
    """페르소나가 부르는 웹 검색 한 번을 JSON 문자열로 돌려준다(예외를 던지지 않아 그래프가 끊기지 않음).

    20261025 | 요청: LuckyBoys | 작성: Claude | "Tavily 툴로 웹 검색"(체인 도구에도)
    입력: query, search_fn(테스트용 대역) / 출력: {"success": true, "query", "results": [...]} 또는
          {"success": false, "error_code": INVALID_REQUEST | WEB_SEARCH_UNAVAILABLE, "error"}
    """
    def fail(code: str, message: str) -> str:
        return json.dumps({"success": False, "error_code": code, "error": message}, ensure_ascii=False)

    try:
        results = web_search(query, search_fn=search_fn)
    except ValueError as error:
        return fail("INVALID_REQUEST", str(error))
    except WebSearchUnavailable as error:
        return fail("WEB_SEARCH_UNAVAILABLE", str(error))
    return json.dumps({"success": True, "query": query, "results": results}, ensure_ascii=False)


def build_web_search_tool():
    """읽기·쓰기 단계 페르소나에 붙이는 LangChain 웹 검색 도구(이름: web_search, 공통 함수 = Tavily)."""
    from langchain_core.tools import StructuredTool

    def web_search_tool(query: str) -> str:
        """웹을 검색해 제목·URL·요약을 JSON으로 돌려준다(공식 사이트 구조·문서 위치 확인용, 읽기 전용)."""
        return web_search_tool_call(query)

    return StructuredTool.from_function(web_search_tool, name="web_search")


# ---------------------------------------------------------------------------
# 실제 LLM 단계 실행 (테스트에서는 step_fn 주입)
# ---------------------------------------------------------------------------
def run_step(persona: str, system_prompt: str, human_text: str, tools_mode: str) -> dict:
    """한 페르소나 단계를 실행한다. tools_mode: none | read | write."""
    from langchain_core.messages import HumanMessage, SystemMessage, ToolMessage

    from haness.mcp.agents import source_partner_agent as agent

    model = agent._build_model()
    timeout = int(_SETTINGS["agent_timeout_seconds"])   # 단계마다 시간 상한(멈춘 LLM 호출이 체인을 막지 않게)
    # 13개 페르소나 모두 같은 SPS MCP Client/tools/list를 사용한다.
    mcp_tools = asyncio.run(agent._load_sps_mcp_tools(source_write_confirmed=False))
    tools = list(mcp_tools)
    if tools_mode != "none":
        local_tools = agent.build_partner_tools(
            dry_run=False,
            source_write_confirmed=False,
            commit_confirmed=False,
            allowed_source_paths=list(_SETTINGS["allowed_paths"]),
        )
        tools.extend(t for t in local_tools if t.name != "execute_change_set")
        tools.append(build_web_search_tool())                            # read/write 단계 공통 웹 검색
    if tools_mode == "write":
        tools += build_source_repair_tools()                             # PARTNER만 로컬 수정 도구를 받는다
    graph = agent.build_source_partner_graph(model=model, tools=tools, system_prompt=system_prompt)
    state = asyncio.run(asyncio.wait_for(
        graph.ainvoke({"messages": [HumanMessage(content=human_text)]},
                      config={"recursion_limit": int(_SETTINGS["agent_recursion_limit"])}), timeout))
    messages = state.get("messages", [])
    return {"output": _PERSONAS.content_text(messages[-1].content) if messages else "",
            "mcp_tools_loaded": [mcp_tool.name for mcp_tool in mcp_tools],
            "tool_evidence": [{"tool_call_id": m.tool_call_id, "content": m.content}
                              for m in messages if isinstance(m, ToolMessage)]}


def run_regression(tests: list[str]) -> dict:
    """회귀 테스트를 새 프로세스로 실제 실행한다(TESTER 판정과 최종 판정의 증거)."""
    existing = [t for t in tests if (ROOT / t).is_file()]
    done = subprocess.run([sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider", *existing],
                          capture_output=True, text=True, cwd=ROOT, timeout=int(_SETTINGS["regression_timeout_seconds"]))
    return {"ok": done.returncode == 0, "tests": existing, "tail": done.stdout[-1500:]}


# ---------------------------------------------------------------------------
# 체인 = LangGraph StateGraph (2026-10-25 LuckyBoys: "add_node/add_edge/compile이 빠졌다. agent가 아니다!!!")
#   예전 run_chain의 for 루프(원본: persona_repair_chain_BACKUP_20261025_215433.py)를 노드·엣지로 옮겼다.
#   판정 규칙(PLAN_INVALID/NO_CHANGE/REVIEW_BLOCKED/TEST_FAILED/PASS)과 호출 순서는 그대로다.
#
#   START → orchestrator → dispatch ─(route_next: 계획 큐 맨 앞)→ partner_fix | reviewer | tester | persona
#                              ↑                                          │ (각 노드 실행 후 다시 dispatch)
#                              └──────────────────────────────────────────┘
#           dispatch ─(큐가 비면)→ final_regression ─(통과)→ partner_final → END
#           어느 노드든 verdict가 정해지면 dispatch/final_regression의 조건부 엣지가 END로 보낸다.
# ---------------------------------------------------------------------------
class ChainState(TypedDict, total=False):
    """그래프 상태. 노드는 바뀐 키만 돌려주고(LangGraph가 덮어씀), 리스트는 항상 새 리스트로 만든다."""
    task: str                      # 실패 작업문(autodiscover_self_repair.build_repair_task)
    round_no: int                  # 라운드 번호(autonomous_from_round 이상이면 자율 계획)
    mode: str                      # fixed | autonomous
    started_kst: str
    queue: list                    # 아직 실행하지 않은 페르소나(계획 순서 그대로)
    plan: dict                     # {"selected": [...] | None, "ignored": [...]}
    steps: list                    # 단계 기록 {persona, key, mode, output, verdict?}
    carried: list                  # 다음 단계로 넘기는 [이름, 산출물] 목록
    tool_evidence: list            # PARTNER(수정) 도구 결과(ToolMessage 내용)
    sets: list                     # staged_fn이 인정한 실제 변경 세트
    regression: Any                # 마지막 회귀 테스트 결과(None = 아직 실행 안 함)
    regression_after_change: Any   # 위 결과가 변경 후 실행된 것인지(None = 미실행)
    verdict: str                   # "" = 진행 중, 그 밖 = 최종 판정
    output: str                    # PASS일 때 PARTNER(통합) 보고


def initial_state(task: str, round_no: int) -> ChainState:
    """입력을 검사하고 그래프 시작 상태를 만든다(잘못된 입력은 ValueError — 그래프를 시작하지 않음)."""
    if not isinstance(task, str) or not task.strip():
        raise ValueError("task must be non-empty text")
    if not isinstance(round_no, int) or round_no < 1:
        raise ValueError("round_no must be a positive integer")
    autonomous = round_no >= int(_SETTINGS["autonomous_from_round"])
    return {"task": task, "round_no": round_no, "mode": "autonomous" if autonomous else "fixed",
            "started_kst": now_kst_iso(), "queue": [], "plan": {}, "steps": [], "carried": [],
            "tool_evidence": [], "sets": [], "regression": None, "regression_after_change": None,
            "verdict": "", "output": ""}


def build_repair_chain_graph(step_fn: Callable[..., dict], regression_fn: Callable[[list], dict],
                             staged_fn: Callable[[dict], list[dict]]):
    """페르소나 수리 체인을 LangGraph StateGraph로 만들어 compile()한 그래프를 돌려준다.

    step_fn      : (persona, system_prompt, human_text, tools_mode) → {"output", "tool_evidence"} (운영: run_step)
    regression_fn: (tests) → {"ok", ...} 회귀 테스트 실제 실행(운영: run_regression)
    staged_fn    : PARTNER 결과에서 실제 staged 변경 세트를 고르는 함수(autodiscover_self_repair.staged_change_sets)
    """
    for label, fn in (("step_fn", step_fn), ("regression_fn", regression_fn), ("staged_fn", staged_fn)):
        if not callable(fn):
            raise ValueError(f"{label} must be callable")
    from langgraph.graph import END, START, StateGraph   # 지연 import: 모듈 import만으로 langgraph를 요구하지 않음

    fixed_plan = list(_SETTINGS["first_round_plan"])
    allowed = available_personas()

    # --- 공통 도우미 (노드 안에서만 쓰임) --------------------------------------
    def run_persona(state: ChainState, persona: str, key: str, mode: str) -> tuple[dict, dict]:
        """원문 프롬프트로 한 페르소나를 실행하고 (결과, 상태 갱신분[steps·carried])을 돌려준다."""
        instruction = STEP_INSTRUCTIONS[key].format(
            allowed=json.dumps(_SETTINGS["allowed_paths"]), tests=json.dumps(_SETTINGS["regression_tests"]),
            fixed=" → ".join(fixed_plan), all=", ".join(allowed), cap=int(_SETTINGS["max_personas"]) - 1)
        carried = [(name, text) for name, text in state["carried"]]
        result = step_fn(persona, load_persona_prompt(persona), _human_message(state["task"], carried, instruction), mode)
        steps = state["steps"] + [{"persona": persona, "key": key, "mode": mode, "output": result["output"][:4000]}]
        return result, {"steps": steps, "carried": state["carried"] + [[persona, result["output"]]]}

    def regression_update(state: ChainState) -> dict:
        """회귀 테스트는 '현재 변경 상태'로 한 번만 실행한다(변경 전 결과를 변경 후 판정에 재사용하지 않음)."""
        after_change = bool(state["sets"])
        if state["regression"] is not None and state["regression_after_change"] == after_change:
            return {}
        new_tests = sorted({p for cs in state["sets"] for p in cs["staged_groups"].get("tests", [])})
        regression = regression_fn(list(_SETTINGS["regression_tests"]) + new_tests)
        return {"regression": regression, "regression_after_change": after_change,
                "carried": state["carried"] + [["REGRESSION(프로그램 실행)", json.dumps(regression, ensure_ascii=False)]]}

    # --- 노드 ----------------------------------------------------------------
    def orchestrator(state: ChainState) -> dict:
        """계획 노드: 1라운드는 고정 순서, 이후 라운드는 ORCHESTRATOR가 쓴 PLAN 줄 순서."""
        autonomous = state["mode"] == "autonomous"
        result, update = run_persona(state, "ORCHESTRATOR",
                                     "ORCHESTRATOR_AUTO" if autonomous else "ORCHESTRATOR_FIXED", "none")
        selected, ignored = parse_plan(result["output"], allowed) if autonomous else (fixed_plan, [])
        update["plan"] = {"selected": selected, "ignored": ignored}
        if selected is None:
            update["verdict"] = "PLAN_INVALID"      # 계획 없이 추측 실행하지 않는다
        elif "PARTNER" not in selected:
            update["verdict"] = "NO_CHANGE"         # 수정 담당이 없으면 고친 것도 없다
        else:
            update["queue"] = list(selected)
        return update

    def dispatch(state: ChainState) -> dict:
        """분기 지점 노드. 상태는 바꾸지 않고, 다음 노드 선택은 route_next 조건부 엣지가 한다."""
        return {}

    def route_next(state: ChainState) -> str:
        """판정이 났으면 END, 큐가 비면 최종 회귀, 아니면 큐 맨 앞 페르소나 담당 노드로."""
        if state.get("verdict"):
            return END
        if not state["queue"]:
            return "final_regression"
        return {"PARTNER": "partner_fix", "REVIEWER": "reviewer", "TESTER": "tester"}.get(state["queue"][0], "persona")

    def partner_fix(state: ChainState) -> dict:
        """PARTNER(수정): 쓰기 도구(read_repair_source/repair_source)를 가진 유일한 단계."""
        result, update = run_persona(state, "PARTNER", "PARTNER_FIX", "write")
        sets = staged_fn(result)
        update.update(queue=state["queue"][1:], tool_evidence=result.get("tool_evidence", []), sets=sets)
        if not sets:
            update["verdict"] = "NO_CHANGE"         # 실제 적용·stage된 변경이 없음
        return update

    def reviewer(state: ChainState) -> dict:
        """REVIEWER(진단만): 마지막 줄 VERDICT가 HOLD면 REVIEW_BLOCKED."""
        result, update = run_persona(state, "REVIEWER", "REVIEWER", "read")
        update["steps"][-1]["verdict"] = parse_verdict(result["output"])
        update["queue"] = state["queue"][1:]
        if update["steps"][-1]["verdict"] == "HOLD":
            update["verdict"] = "REVIEW_BLOCKED"
        return update

    def tester(state: ChainState) -> dict:
        """TESTER: 프로그램이 회귀 테스트를 먼저 실제 실행하고, 그 결과를 증거로 판정한다(PASS 아니면 TEST_FAILED)."""
        regression = regression_update(state)
        result, update = run_persona({**state, **regression}, "TESTER", "TESTER", "none")
        update = {**regression, **update, "queue": state["queue"][1:]}   # update.carried가 회귀 결과까지 포함
        update["steps"][-1]["verdict"] = parse_verdict(result["output"])
        if update["steps"][-1]["verdict"] != "PASS":
            update["verdict"] = "TEST_FAILED"
        return update

    def persona(state: ChainState) -> dict:
        """그 밖의 페르소나(BUG_HUNTER·ARCHITECT 등): 읽기 도구만으로 분석."""
        name = state["queue"][0]
        _result, update = run_persona(state, name, "BUG_HUNTER" if name == "BUG_HUNTER" else "GENERIC", "read")
        update["queue"] = state["queue"][1:]
        return update

    def final_regression(state: ChainState) -> dict:
        """TESTER를 안 골랐어도 변경 후 실행 증거 없이 통과시키지 않는다."""
        update = regression_update(state)
        if not (update.get("regression") or state["regression"] or {}).get("ok"):
            update["verdict"] = "TEST_FAILED"
        return update

    def partner_final(state: ChainState) -> dict:
        """프로그램이 지정하는 유일한 단계: 마지막 PARTNER(통합) 보고."""
        result, update = run_persona(state, "PARTNER", "PARTNER_FINAL", "none")
        update.update(output=result["output"], verdict="PASS")
        return update

    # --- 그래프 조립 -----------------------------------------------------------
    graph = StateGraph(ChainState)
    graph.add_node("orchestrator", orchestrator)
    graph.add_node("dispatch", dispatch)
    graph.add_node("partner_fix", partner_fix)
    graph.add_node("reviewer", reviewer)
    graph.add_node("tester", tester)
    graph.add_node("persona", persona)
    graph.add_node("final_regression", final_regression)
    graph.add_node("partner_final", partner_final)
    graph.add_edge(START, "orchestrator")
    graph.add_edge("orchestrator", "dispatch")
    graph.add_conditional_edges("dispatch", route_next,
                                ["partner_fix", "reviewer", "tester", "persona", "final_regression", END])
    for node in ("partner_fix", "reviewer", "tester", "persona"):
        graph.add_edge(node, "dispatch")            # 각 페르소나 실행 후 다음 페르소나 선택으로 돌아간다
    graph.add_conditional_edges("final_regression", lambda s: END if s.get("verdict") else "partner_final",
                                ["partner_final", END])
    graph.add_edge("partner_final", END)
    return graph.compile()


def run_chain(task: str, staged_fn: Callable[[dict], list[dict]], step_fn: Callable[..., dict] = None,
              regression_fn: Callable[[list], dict] = None, round_no: int = 1) -> dict:
    """한 라운드의 페르소나 체인 그래프를 실행하고 {mode, plan, verdict, steps, tool_evidence, regression, output}을 돌려준다.

    staged_fn: PARTNER 결과에서 실제 staged 변경 세트를 고르는 함수(autodiscover_self_repair.staged_change_sets).
    round_no : config autonomous_from_round 미만이면 고정 순서, 이상이면 ORCHESTRATOR 자율 계획.
    반환 형식은 예전 for 루프 버전과 같다(autodiscover_self_repair가 그대로 읽음).
    """
    state = initial_state(task, round_no)
    graph = build_repair_chain_graph(step_fn=step_fn or run_step, regression_fn=regression_fn or run_regression,
                                     staged_fn=staged_fn)
    final = graph.invoke(state, config={"recursion_limit": int(_SETTINGS["agent_recursion_limit"])})
    out: dict[str, Any] = {key: final.get(key) for key in
                           ("started_kst", "mode", "plan", "steps", "tool_evidence", "regression", "verdict")}
    out["round"] = round_no
    if final.get("output"):
        out["output"] = final["output"]
    return out

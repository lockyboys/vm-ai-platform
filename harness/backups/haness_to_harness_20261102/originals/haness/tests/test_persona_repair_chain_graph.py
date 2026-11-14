"""페르소나 수리 체인이 실제 LangGraph agent(StateGraph: add_node/add_edge/compile)인지 검증한다.

2026-10-25 LuckyBoys: "persona_repair_chain.py에는 graph.add_node / graph.add_edge / return graph.compile()이
빠졌다!!! agent가 아니다!!!" → 순수 파이썬 for 루프였던 run_chain을 StateGraph로 바꾼다.

검증 항목 (실제 LLM 없이 step_fn·regression_fn 주입)
1. build_repair_chain_graph가 CompiledStateGraph를 돌려주고, 노드
   orchestrator·dispatch·partner_fix·reviewer·tester·persona·final_regression·partner_final을 가진다
2. run_chain이 그 그래프를 실제로 거쳐 실행된다(빌더를 감싸 호출 여부 확인)
3. 그래프를 직접 invoke해도 기존 판정과 같다(1라운드 고정 순서 PASS / PLAN 없음 → PLAN_INVALID)
4. 잘못된 입력: 빌더에 호출 불가능한 함수를 주면 ValueError
"""
from __future__ import annotations

import json

import pytest

from haness.mcp.agents import persona_repair_chain as chain

STAGED = {"change_set_id": "fix1", "success": True, "dry_run": False,
          "staged_groups": {"source": ["a.py"], "tests": []}}
NODES = {"orchestrator", "dispatch", "partner_fix", "reviewer", "tester", "persona",
         "final_regression", "partner_final"}


def _staged(result: dict) -> list[dict]:
    """PARTNER(수정) 결과에 도구 증빙이 있으면 변경 1건으로 본다."""
    return [STAGED] if result.get("tool_evidence") else []


def _steps(plan: str = "PLAN: PARTNER"):
    """페르소나별 가짜 LLM 출력. 호출 순서를 calls에 기록한다."""
    calls = []

    def step(persona, system_prompt, human_text, mode):
        calls.append((persona, mode))
        if persona == "PARTNER" and mode == "write":
            return {"output": "fixed", "tool_evidence": [{"content": json.dumps(STAGED)}]}
        outputs = {"ORCHESTRATOR": f"| 단계 |\n{plan}", "REVIEWER": "VERDICT: APPROVE", "TESTER": "VERDICT: PASS"}
        return {"output": outputs.get(persona, "analysis"), "tool_evidence": []}
    step.calls = calls
    return step


def _ok(tests):
    return {"ok": True, "tests": tests}


def test_builder_returns_compiled_state_graph_with_nodes():
    from langgraph.graph.state import CompiledStateGraph

    graph = chain.build_repair_chain_graph(step_fn=_steps(), regression_fn=_ok, staged_fn=_staged)
    assert isinstance(graph, CompiledStateGraph)
    assert NODES <= set(graph.get_graph().nodes)


def test_run_chain_executes_through_langgraph(monkeypatch):
    built = []
    original = chain.build_repair_chain_graph

    def spy(**kwargs):
        built.append(kwargs)
        return original(**kwargs)
    monkeypatch.setattr(chain, "build_repair_chain_graph", spy)
    out = chain.run_chain("task", staged_fn=_staged, step_fn=_steps(), regression_fn=_ok, round_no=1)
    assert len(built) == 1 and out["verdict"] == "PASS"


def test_graph_invoke_fixed_round_order_and_pass():
    step = _steps()
    graph = chain.build_repair_chain_graph(step_fn=step, regression_fn=_ok, staged_fn=_staged)
    state = graph.invoke(chain.initial_state("task", 1), config={"recursion_limit": 64})
    assert state["verdict"] == "PASS"
    assert step.calls == [("ORCHESTRATOR", "none"), ("BUG_HUNTER", "read"), ("PARTNER", "write"),
                          ("REVIEWER", "read"), ("TESTER", "none"), ("PARTNER", "none")]


def test_graph_invoke_without_plan_line_is_plan_invalid():
    step = _steps(plan="계획만 있고 PLAN 줄 없음")
    graph = chain.build_repair_chain_graph(step_fn=step, regression_fn=_ok, staged_fn=_staged)
    state = graph.invoke(chain.initial_state("task", 2), config={"recursion_limit": 64})
    assert state["verdict"] == "PLAN_INVALID" and step.calls == [("ORCHESTRATOR", "none")]


@pytest.mark.parametrize("bad", [None, "step", 3])
def test_builder_rejects_non_callable(bad):
    with pytest.raises(ValueError):
        chain.build_repair_chain_graph(step_fn=bad, regression_fn=_ok, staged_fn=_staged)

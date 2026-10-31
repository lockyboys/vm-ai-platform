"""자동 탐색 자기 수리 루프 테스트(2026-10-25 LuckyBoys: "자동 적용 + add만 하기").

흐름: auto → NEEDS_NEW_RULE → 수리 에이전트(PARTNER) → 변경 세트 staged → 범위·회귀 테스트 확인
      → 새 프로세스로 auto 재실행. 커밋은 하지 않는다(add만).
실제 LLM·브라우저·git은 쓰지 않고 함수 주입으로 검증한다.
"""
from __future__ import annotations

import asyncio
import importlib.util
import inspect
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
PFDS = ROOT / "FastAPI/LangGraph/Agent_Import_PFDs"
ALLOWED = "FastAPI/LangGraph/Agent_Import_PFDs/profile_autodiscover.py"


def _load(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture()
def sr(tmp_path, monkeypatch):
    # 수리 루프는 Harness 소스라 haness/mcp/agents에 있다(일반 지침 10).
    module = _load("autodiscover_self_repair_t", ROOT / "haness/mcp/agents/autodiscover_self_repair.py")
    # 증빙 파일은 임시 폴더에만 쓴다(실제 출력 폴더 오염 방지).
    monkeypatch.setattr(module, "_work_dir", lambda name: tmp_path)
    return module


def _needs_rule(evidence: str = "") -> dict:
    return {"result": "NEEDS_NEW_RULE",
            "failure": {"category": "systematic", "error": "ValueError: brand-new rule", "evidence": evidence}}


def _staged_agent(paths: list[str], verdict: str = "PASS") -> dict:
    """페르소나 체인이 실제로 적용·stage했을 때의 결과 모양(verdict는 체인 판정)."""
    change_set = {"change_set_id": "fix1", "dry_run": False, "success": True, "state": "STAGED",
                  "staged_groups": {"source": paths}}
    return {"verdict": verdict, "output": "고침", "steps": [{"persona": "ORCHESTRATOR"}, {"persona": "PARTNER"}],
            "tool_evidence": [
        {"tool_call_id": "a", "content": "not json"},
        {"tool_call_id": "b", "content": json.dumps(change_set)}]}


class Calls:
    """주입 함수 호출 기록."""

    def __init__(self, auto_results, agent_result=None, agent_results=None):
        self.auto_results = list(auto_results)
        self.agent_result = agent_result if agent_result is not None else _staged_agent([ALLOWED])
        self.agent_results = agent_results     # 라운드별 결과(있으면 우선)
        self.rounds: list[int] = []
        self.tasks: list[str] = []
        self.auto = 0
        self.partner = 0
        self.restored = []

    def kwargs(self):
        def auto_fn(request):
            self.auto += 1
            return self.auto_results[min(self.auto - 1, len(self.auto_results) - 1)]

        def partner_fn(task, round_no):
            self.partner += 1
            self.rounds.append(round_no)
            self.tasks.append(task)
            if self.agent_results:
                return self.agent_results[min(round_no - 1, len(self.agent_results) - 1)]
            return self.agent_result

        return {"auto_fn": auto_fn, "partner_fn": partner_fn,
                "backup_fn": lambda paths: {p: p + ".bak" for p in paths},
                "restore_fn": lambda backups: self.restored.append(backups)}


# --- 잘못된 입력 ---------------------------------------------------------------
@pytest.mark.parametrize("request_value", [{}, {"name": "Bad-Name"}, {"name": ""}, "text"])
def test_invalid_request_is_rejected(sr, request_value):
    with pytest.raises(ValueError):
        sr.auto_with_repair(request_value, **Calls([{"result": "FAILED"}]).kwargs())


def test_build_task_is_bounded_and_has_evidence(sr, tmp_path):
    evidence = tmp_path / "failure.json"
    evidence.write_text(json.dumps({"error": "E" * 50000}), encoding="utf-8")
    task = sr.build_repair_task("site_a", _needs_rule(str(evidence)))
    assert len(task) <= 12000
    assert "brand-new rule" in task and ALLOWED in task and "tests/" in task


# --- 정상/실패 경로 -------------------------------------------------------------
def test_no_repair_when_not_new_rule(sr):
    calls = Calls([{"result": "DISCOVERED_AND_VALID_SAVED"}])
    out = sr.auto_with_repair({"name": "site_a"}, **calls.kwargs())
    assert out["result"] == "DISCOVERED_AND_VALID_SAVED" and calls.partner == 0 and out["repairs"] == []


def test_repair_staged_then_rediscover(sr):
    calls = Calls([_needs_rule(), {"result": "DISCOVERED_AND_VALID_SAVED"}])
    out = sr.auto_with_repair({"name": "site_a", "apply": True}, **calls.kwargs())
    assert out["result"] == "DISCOVERED_AND_VALID_SAVED"
    assert calls.partner == 1 and calls.auto == 2 and calls.restored == []
    assert out["repairs"][0]["result"] == "STAGED" and out["repairs"][0]["paths"] == [ALLOWED]
    assert Path(out["evidence"]).exists()


def test_run_partner_uses_persona_chain(sr, monkeypatch):
    """수리는 PARTNER 단독이 아니라 페르소나 체인으로 실행되고, 체인 예외는 ERROR로 보고된다."""
    from haness.mcp.agents import persona_repair_chain as chain
    seen = {}
    monkeypatch.setattr(chain, "run_chain", lambda task, staged_fn, round_no:
                        seen.update(staged_fn=staged_fn, round_no=round_no) or {"verdict": "PASS"})
    assert sr.run_partner("task", 2)["verdict"] == "PASS" and seen["staged_fn"] is sr.staged_change_sets
    assert seen["round_no"] == 2

    def boom(task, staged_fn, round_no):
        raise RuntimeError("llm down")

    monkeypatch.setattr(chain, "run_chain", boom)
    assert sr.run_partner("task")["verdict"] == "ERROR"


@pytest.mark.parametrize("verdict", ["TEST_FAILED", "REVIEW_BLOCKED", "미확인"])
def test_chain_not_pass_is_restored(sr, verdict):
    calls = Calls([_needs_rule()], agent_result=_staged_agent([ALLOWED], verdict))
    out = sr.auto_with_repair({"name": "site_a"}, **calls.kwargs())
    # 1라운드 실패 → 원복 → 2라운드(ORCHESTRATOR 자율)도 실패 → 원복 → REPAIR_FAILED
    assert out["result"] == "REPAIR_FAILED" and [r["result"] for r in out["repairs"]] == [verdict, verdict]
    assert len(calls.restored) == 2 and calls.auto == 1 and calls.rounds == [1, 2]


def test_second_round_gets_previous_attempt_and_can_fix(sr):
    """1라운드(고정) 실패 증빙이 2라운드 작업문에 붙고, 2라운드에서 고치면 재탐색까지 간다."""
    first = _staged_agent([ALLOWED], "TEST_FAILED")
    first["steps"] = [{"persona": "TESTER", "mode": "none", "output": "VERDICT: FAIL 재현 안 됨"}]
    calls = Calls([_needs_rule(), {"result": "DISCOVERED_AND_VALID_SAVED"}], agent_results=[first, _staged_agent([ALLOWED])])
    out = sr.auto_with_repair({"name": "site_a"}, **calls.kwargs())
    assert out["result"] == "DISCOVERED_AND_VALID_SAVED" and calls.rounds == [1, 2] and calls.auto == 2
    assert "이전 시도 1라운드" in calls.tasks[1] and "재현 안 됨" in calls.tasks[1]
    assert len(calls.restored) == 1 and out["repairs"][1]["result"] == "STAGED"


def test_agent_without_change_set_fails(sr):
    calls = Calls([_needs_rule()], agent_result={"verdict": "NO_CHANGE", "error": "timeout", "tool_evidence": []})
    out = sr.auto_with_repair({"name": "site_a"}, **calls.kwargs())
    assert out["result"] == "REPAIR_FAILED" and [r["result"] for r in out["repairs"]] == ["NO_CHANGE", "NO_CHANGE"]


def test_repair_rounds_are_limited(sr, monkeypatch):
    monkeypatch.setitem(sr._SETTINGS, "max_repair_rounds", 2)
    calls = Calls([_needs_rule()])
    out = sr.auto_with_repair({"name": "site_a"}, **calls.kwargs())
    assert calls.partner == 2 and out["result"] == "NEEDS_NEW_RULE"


def test_disabled_setting_skips_repair(sr, monkeypatch):
    monkeypatch.setitem(sr._SETTINGS, "enabled", False)
    calls = Calls([_needs_rule()])
    out = sr.auto_with_repair({"name": "site_a"}, **calls.kwargs())
    assert calls.partner == 0 and out["result"] == "NEEDS_NEW_RULE"


def test_staged_change_sets_ignore_dry_run_and_failures(sr):
    items = [{"change_set_id": "a", "dry_run": True, "success": True, "staged_groups": {"source": ["x"]}},
             {"change_set_id": "b", "dry_run": False, "success": False, "staged_groups": {}},
             {"change_set_id": "c", "dry_run": False, "success": True, "staged_groups": {"tests": ["tests/t.py"]}}]
    agent = {"tool_evidence": [{"content": json.dumps(i)} for i in items] + [{"content": "[1]"}]}
    assert [c["change_set_id"] for c in sr.staged_change_sets(agent)] == ["c"]


# --- 수집기 연결: NEEDS_NEW_RULE를 성공으로 오인하던 문제 재현 -----------------------
@pytest.fixture(scope="module")
def collector():
    return _load("collector_self_repair_t", PFDS / "public_document_catalog_collector.py")


@pytest.mark.parametrize("result", ["NEEDS_NEW_RULE", "REPAIR_FAILED", "REPAIR_OUT_OF_SCOPE", "FAILED"])
def test_run_probe_raises_when_heal_not_fixed(collector, result):
    def bad_probe(profile):
        raise ValueError("site changed")

    with pytest.raises(RuntimeError):
        collector.run_probe("site_a", True, load=lambda n: {"name": n}, probe_fn=bad_probe,
                            heal_fn=lambda n: {"result": result})


@pytest.mark.parametrize("result", ["NEEDS_NEW_RULE", "REPAIR_FAILED"])
def test_ensure_healthy_raises_when_heal_not_fixed(collector, result):
    def bad_probe(profile):
        raise ValueError("site changed")

    with pytest.raises(RuntimeError):
        collector.ensure_healthy({"name": "site_a", "autodiscover": {"start_urls": []}}, probe_fn=bad_probe,
                                 heal_fn=lambda n: {"result": result}, load=lambda n: None)


# --- PARTNER 에이전트: 도구 오류로 전체 실행이 죽던 문제(attempt4) 재현 ---------------
def test_partner_graph_survives_tool_error():
    from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
    from langchain_core.tools import tool

    from haness.mcp.agents import source_partner_agent as agent

    @tool("boom")
    def boom() -> str:
        """항상 실패하는 도구."""
        raise ValueError("path is not an allowed text source file")

    class FakeModel:
        def __init__(self):
            self.n = 0

        def bind_tools(self, tools):
            return self

        async def ainvoke(self, messages):
            self.n += 1
            if self.n == 1:
                return AIMessage(content="", tool_calls=[{"name": "boom", "args": {}, "id": "c1"}])
            return AIMessage(content="done")

    graph = agent.build_source_partner_graph(model=FakeModel(), tools=[boom])
    state = asyncio.run(graph.ainvoke({"messages": [HumanMessage(content="x")]}))
    tool_messages = [m for m in state["messages"] if isinstance(m, ToolMessage)]
    assert state["messages"][-1].content == "done"
    assert "not an allowed" in tool_messages[0].content


def test_partner_accepts_recursion_limit():
    from haness.mcp.agents import source_partner_agent as agent

    assert inspect.signature(agent.run_source_partner_agent).parameters["recursion_limit"].default == 18

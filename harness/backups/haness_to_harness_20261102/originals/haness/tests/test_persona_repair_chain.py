"""페르소나 수리 체인 테스트(2026-10-25 LuckyBoys: 고정 순서는 1라운드만, 2라운드는 ORCHESTRATOR 자율, 마지막만 지정).

실제 LLM 없이 step_fn 주입으로 검증한다.
- 1라운드: 고정 순서 BUG_HUNTER → PARTNER → REVIEWER → TESTER → PARTNER(통합)
- 2라운드: ORCHESTRATOR가 13개 원문 중 고른 페르소나를 '쓴 순서대로' 실행, 마지막 PARTNER만 프로그램이 붙임
- 각 단계 시스템 프롬프트가 haness/personas/references/<이름>.md 원문과 byte 단위로 같은지
- PLAN 없음/PARTNER 없음/변경 없음/REVIEWER HOLD/회귀 실패/TESTER 비통과 판정
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from haness.mcp.agents import persona_repair_chain as chain

ROOT = Path(__file__).resolve().parents[2]
PERSONA_DIR = ROOT / "haness/personas/references"
# 스킬 references 원문 sha256(동기화 스크립트 검증값과 같음). 13개 전부.
ORIGINAL_SHA256 = {
    "orchestrator.md": "6dd5f247838e07dff2c4597ab9c02e70de17bdd88eae308ee53aafdd7d216bb9",
    "bug_hunter.md": "5bc9a00e789dfa03a37619181c740f1b40dca52e43c3d0f7ced4b6464081d7d7",
    "partner.md": "34e6b5c91c30aadd6c20741ddfcac0fd1e1a5ef42e8a18e806324507908fcb18",
    "reviewer.md": "bf7c49193a172ec6f78e50d1bd97585a0b29e5ca8fe72c93a07f122faa04c6bd",
    "tester.md": "913cf9b388898adf99f754456817575a569e0c2e86c1c9798f7bf414aa1e118f",
    "architect.md": "a23a9e21231d093debd552282012a4954140605e7b6df4cd54e95bc9f8ff2d4f",
    "sql_expert.md": "768c93588707aa064617f0f63d90722433b744ae6f940277e6c3da667f69f922",
    "prompt_engineer.md": "20c00cde6c690bef3127167bfbeff4709e97ea6eb2c342040739c5806bc98a3f",
    "strategist.md": "bf7baaadcf8ec721fab0d4e23c784a55b496c8e9ea062c7ee665b04e84df5fe6",
    "security.md": "7da94c89e1090412a5f5c05e3955eb92206e037b311ce1200a1b8c117eb08b21",
    "devops.md": "b2e345e823ad47a09d459e89c3bb248b5fa54bd0dbcb1eeb7fd683f662e84422",
    "documenter.md": "502896b18f6cb430481d512dcbba73047e9bcd30fdb49b88b89ea874ec6bc864",
    "tutor.md": "79adbbe04247c4a25fe041f4d2bdfc055014ec9e98edcf5745a2dfcf29b90d97",
}
STAGED = {"change_set_id": "fix1", "success": True, "dry_run": False,
          "staged_groups": {"source": ["a.py"], "tests": ["haness/tests/test_new_fix.py"]}}


def _staged(result: dict) -> list[dict]:
    return [STAGED] if result.get("tool_evidence") else []


class Steps:
    """페르소나별 가짜 출력과 호출 기록."""

    def __init__(self, plan="PLAN: PARTNER", reviewer="VERDICT: APPROVE", tester="VERDICT: PASS", change=True):
        self.outputs = {"ORCHESTRATOR": f"| 단계 |\n{plan}", "BUG_HUNTER": "```python\ndef test_x(): pass\n```",
                        "REVIEWER": reviewer, "TESTER": tester}
        self.change = change
        self.calls: list[tuple[str, str, str]] = []
        self.messages: list[str] = []

    def __call__(self, persona, system_prompt, human_text, mode):
        self.calls.append((persona, mode, system_prompt))
        self.messages.append(human_text)
        if persona == "PARTNER" and mode == "write":
            return {"output": "fixed", "tool_evidence": [{"content": json.dumps(STAGED)}] if self.change else []}
        return {"output": self.outputs.get(persona, "analysis"), "tool_evidence": []}


def _run(steps, regression_ok=True, round_no=2):
    return chain.run_chain("task", staged_fn=_staged, step_fn=steps, round_no=round_no,
                           regression_fn=lambda tests: {"ok": regression_ok, "tests": tests})


def _order(steps):
    return [(p, m) for p, m, _ in steps.calls]


# --- 원문 프롬프트 -------------------------------------------------------------
@pytest.mark.parametrize("name,sha", ORIGINAL_SHA256.items())
def test_persona_prompt_is_verbatim_original(name, sha):
    assert hashlib.sha256((PERSONA_DIR / name).read_bytes()).hexdigest() == sha


@pytest.mark.parametrize("bad", ["", "partner", "../x", "A" * 40, None])
def test_invalid_persona_name_rejected(bad):
    with pytest.raises(ValueError):
        chain.load_persona_prompt(bad)


def test_available_personas_are_twelve_without_orchestrator():
    names = chain.available_personas()
    assert len(names) == 12 and "ORCHESTRATOR" not in names and {"ARCHITECT", "PARTNER", "TESTER"} <= set(names)


def test_system_prompt_is_file_text_unchanged():
    steps = Steps(plan="PLAN: ARCHITECT, PARTNER")
    _run(steps)
    for persona, _mode, system_prompt in steps.calls:
        assert system_prompt == (PERSONA_DIR / f"{persona.lower()}.md").read_text(encoding="utf-8")


# --- 1라운드: 고정 순서 ---------------------------------------------------------
def test_first_round_is_fixed_order_and_ignores_plan():
    steps = Steps(plan="PLAN: ARCHITECT")       # 1라운드는 PLAN을 따르지 않는다
    out = _run(steps, round_no=1)
    assert out["mode"] == "fixed" and out["verdict"] == "PASS"
    assert _order(steps) == [("ORCHESTRATOR", "none"), ("BUG_HUNTER", "read"), ("PARTNER", "write"),
                             ("REVIEWER", "read"), ("TESTER", "none"), ("PARTNER", "none")]


# --- 2라운드: ORCHESTRATOR 자율 --------------------------------------------------
def test_parse_plan_keeps_orchestrator_order_and_ignores_unknown():
    allowed = chain.available_personas()
    assert chain.parse_plan("x\nPLAN: TESTER, partner → ARCHITECT, HACKER, TESTER", allowed) == (
        ["TESTER", "PARTNER", "ARCHITECT"], ["HACKER"])
    assert chain.parse_plan("계획 없음", allowed) == (None, [])


def test_autonomous_round_runs_only_planned_personas_in_written_order():
    steps = Steps(plan="PLAN: ARCHITECT, PARTNER, SECURITY")
    out = _run(steps)
    assert out["mode"] == "autonomous" and out["verdict"] == "PASS"
    # 마지막 PARTNER(통합)만 프로그램이 붙인다. 나머지는 ORCHESTRATOR가 쓴 순서·종류 그대로.
    assert _order(steps) == [("ORCHESTRATOR", "none"), ("ARCHITECT", "read"), ("PARTNER", "write"),
                             ("SECURITY", "read"), ("PARTNER", "none")]


def test_autonomous_orchestrator_sees_all_personas():
    steps = Steps()
    _run(steps)
    assert "ARCHITECT" in steps.messages[0] and "TUTOR" in steps.messages[0] and "PLAN:" in steps.messages[0]


def test_plan_is_capped(monkeypatch):
    monkeypatch.setitem(chain._SETTINGS, "max_personas", 3)
    steps = Steps(plan="PLAN: ARCHITECT, BUG_HUNTER, PARTNER, TESTER")
    out = _run(steps)
    assert out["plan"]["selected"] == ["ARCHITECT", "BUG_HUNTER"] and out["verdict"] == "NO_CHANGE"


def test_tester_before_partner_does_not_count_as_post_change_evidence():
    seen = []
    steps = Steps(plan="PLAN: TESTER, PARTNER")
    out = chain.run_chain("task", staged_fn=_staged, step_fn=steps, round_no=2,
                          regression_fn=lambda tests: seen.append(tests) or {"ok": True})
    assert out["verdict"] == "PASS" and len(seen) == 2   # 변경 전 1회 + 변경 후 1회(최종 판정용)
    assert "haness/tests/test_new_fix.py" in seen[1]


# --- 실패 판정 -----------------------------------------------------------------
@pytest.mark.parametrize("steps,regression_ok,verdict", [
    (Steps(plan="계획만 있고 PLAN 줄 없음"), True, "PLAN_INVALID"),
    (Steps(plan="PLAN: BUG_HUNTER, ARCHITECT"), True, "NO_CHANGE"),
    (Steps(change=False), True, "NO_CHANGE"),
    (Steps(plan="PLAN: PARTNER, REVIEWER", reviewer="VERDICT: HOLD"), True, "REVIEW_BLOCKED"),
    (Steps(plan="PLAN: PARTNER"), False, "TEST_FAILED"),
    (Steps(plan="PLAN: PARTNER, TESTER", tester="VERDICT: FAIL"), True, "TEST_FAILED"),
    (Steps(plan="PLAN: PARTNER, TESTER", tester="판정 줄 없음"), True, "TEST_FAILED"),
])
def test_failures_are_reported(steps, regression_ok, verdict):
    assert _run(steps, regression_ok)["verdict"] == verdict


@pytest.mark.parametrize("task,round_no", [("  ", 1), ("task", 0), ("task", "2")])
def test_invalid_input_rejected(task, round_no):
    with pytest.raises(ValueError):
        chain.run_chain(task, staged_fn=_staged, step_fn=Steps(), round_no=round_no)

"""페르소나 수리 체인 테스트(2026-10-25 LuckyBoys: 고정 순서는 1라운드만, 2라운드는 ORCHESTRATOR 자율, 마지막만 지정).

실제 LLM 없이 step_fn 주입으로 검증한다.
- 1라운드: 고정 순서 BUG_HUNTER → PARTNER → REVIEWER → TESTER → PARTNER(통합)
- 2라운드: ORCHESTRATOR가 13개 원문 중 고른 페르소나를 '쓴 순서대로' 실행, 마지막 PARTNER만 프로그램이 붙임
- 각 단계 시스템 프롬프트가 harness/personas/references/<이름>.md 원문과 byte 단위로 같은지
- PLAN 없음/PARTNER 없음/변경 없음/REVIEWER HOLD/회귀 실패/TESTER 비통과 판정
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from harness.mcp.agents import persona_repair_chain as chain

ROOT = Path(__file__).resolve().parents[2]
PERSONA_DIR = ROOT / "harness/personas/references"
# 스킬 references 원문 sha256(동기화 스크립트 검증값과 같음). 13개 전부.
ORIGINAL_SHA256 = {
    "orchestrator.md": "3da54525ec5e9fcd40f506a1ebeccb03155a1d8425a53596ed47247c24075667",
    "bug_hunter.md": "74e708ef1f202daad6e36562495abce18937ad79a2eab2b16da1a45634d37606",
    "partner.md": "0cca0b167095d2d630bc2f26a9ae4afa5ee7da8c6e0e0a627114f533c3067153",
    "reviewer.md": "52d9ca8d70a97ab7f92e11b335ea3eaefce1e5f9e17fcc4396ccc15cbf644078",
    "tester.md": "a311a946cb9fb470966b73ae12c74bbe63f12942ddaeb87cea3a1b6f43191c4d",
    "architect.md": "aa33443ccc0147171291727645b15e8e8cd2d9c62eab7ba69d9ae94b9c716bb1",
    "sql_expert.md": "d3d1f6703bd0155ecf225eb662adcd368c916508ea5c69786916a48ea0340e91",
    "prompt_engineer.md": "7586821a273b384a1c907901feae6da5ccccd0fea8487fd2b50203be93c9ef84",
    "strategist.md": "46aa5cc16b5f5521b385ed32b670f020425119ff89442a4ee684ba5bf684207f",
    "security.md": "f3dd2eb59eb61380828a67fbbb20b7ef1c763b92c839f4a5362ded65ce7a5750",
    "devops.md": "c386bd3d87942c10924f1a69419d8d30b0b7d4f32154f560fa280cd248e3795d",
    "documenter.md": "4925c98292b59776343f13cb5a84efcf087387fa1a6decafd979bf279a8f245e",
    "tutor.md": "8381ed82edbeb9b5b145fcfe9ea6f2d46edd69c96c009e1bdd1abf72b48de8bf",
}
STAGED = {"change_set_id": "fix1", "success": True, "dry_run": False,
          "staged_groups": {"source": ["a.py"], "tests": ["harness/tests/test_new_fix.py"]}}


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
    assert "harness/tests/test_new_fix.py" in seen[1]


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

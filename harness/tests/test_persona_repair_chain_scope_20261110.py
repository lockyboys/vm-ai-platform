"""대상별 수리 범위(scope) 주입 및 하위 호환성 검증 (2026-11-10 LuckyBoys 일반화).

검증 항목:
(a) scope 미지정 시 regression_fn 이 받은 목록 == config 기본 regression_tests(+new_tests) — 하위 호환
(b) scope 지정 시 regression_fn 이 scope['regression_tests'] 를 받고,
    step_fn 에 넘어간 지시문(human_text)에 scope['allowed_paths'] 가 들어가며 기본 allowed_paths 는 들어가지 않음
(c) resolve_scope 잘못된 입력 ValueError: 빈 목록, 절대경로, '..', 역슬래시, 비문자열, 키 누락, 중복
(d) 4개 인자만 받는 기존 형식 step_fn 주입 시에도 동작
"""
from __future__ import annotations

import json
import pytest

from harness.mcp.agents import persona_repair_chain as chain

STAGED_MOCK = {
    "change_set_id": "scope_fix1",
    "success": True,
    "dry_run": False,
    "staged_groups": {"source": ["custom/module.py"], "tests": ["harness/tests/test_new_custom.py"]},
}


def _dummy_staged(result: dict) -> list[dict]:
    return [STAGED_MOCK] if result.get("tool_evidence") else []


def test_scope_omitted_uses_default_settings_backward_compatibility():
    """(a) scope 미지정 시 regression_fn 이 받은 목록 == config 기본 regression_tests(+new_tests) — 하위 호환."""
    recorded_tests = []

    def fake_regression(tests):
        recorded_tests.append(list(tests))
        return {"ok": True, "tests": tests}

    def fake_step(persona, system_prompt, human_text, mode, allowed_paths=None):
        if persona == "PARTNER" and mode == "write":
            return {"output": "fixed", "tool_evidence": [{"content": json.dumps(STAGED_MOCK)}]}
        outputs = {
            "ORCHESTRATOR": "| 단계 |\nPLAN: BUG_HUNTER, PARTNER, TESTER",
            "REVIEWER": "VERDICT: APPROVE",
            "TESTER": "VERDICT: PASS",
        }
        return {"output": outputs.get(persona, "analysis"), "tool_evidence": []}

    out = chain.run_chain("fix task", staged_fn=_dummy_staged, step_fn=fake_step,
                          regression_fn=fake_regression, round_no=1)
    assert out["verdict"] == "PASS"
    assert len(recorded_tests) >= 1
    expected_default_tests = list(chain._SETTINGS["regression_tests"]) + ["harness/tests/test_new_custom.py"]
    assert recorded_tests[-1] == expected_default_tests


def test_scope_provided_overrides_allowed_paths_and_regression_tests():
    """(b) scope 지정 시 regression_fn 이 scope['regression_tests'] 를 받고,
    step_fn 에 넘어간 지시문(human_text)에 scope['allowed_paths'] 가 들어가며 기본 allowed_paths 는 들어가지 않음.
    """
    custom_scope = {
        "allowed_paths": ["custom/app/feature.py"],
        "regression_tests": ["harness/tests/test_custom_feature.py"],
    }
    recorded_tests = []
    recorded_human_texts = []
    received_allowed_paths = []

    def fake_regression(tests):
        recorded_tests.append(list(tests))
        return {"ok": True, "tests": tests}

    def fake_step(persona, system_prompt, human_text, mode, allowed_paths=None):
        recorded_human_texts.append((persona, human_text))
        received_allowed_paths.append((persona, allowed_paths))
        if persona == "PARTNER" and mode == "write":
            return {"output": "fixed", "tool_evidence": [{"content": json.dumps(STAGED_MOCK)}]}
        outputs = {
            "ORCHESTRATOR": "| 단계 |\nPLAN: BUG_HUNTER, PARTNER, TESTER",
            "REVIEWER": "VERDICT: APPROVE",
            "TESTER": "VERDICT: PASS",
        }
        return {"output": outputs.get(persona, "analysis"), "tool_evidence": []}

    out = chain.run_chain("fix custom scope", staged_fn=_dummy_staged, step_fn=fake_step,
                          regression_fn=fake_regression, round_no=1, scope=custom_scope)
    assert out["verdict"] == "PASS"

    assert len(recorded_tests) >= 1
    expected_tests = list(custom_scope["regression_tests"]) + ["harness/tests/test_new_custom.py"]
    assert recorded_tests[-1] == expected_tests
    for default_test in chain._SETTINGS["regression_tests"]:
        assert default_test not in recorded_tests[-1]

    partner_texts = [text for persona, text in recorded_human_texts if persona == "PARTNER"]
    assert len(partner_texts) >= 1
    assert "custom/app/feature.py" in partner_texts[0]
    for default_path in chain._SETTINGS["allowed_paths"]:
        assert default_path not in partner_texts[0]

    partner_allowed = [paths for persona, paths in received_allowed_paths if persona == "PARTNER"]
    assert partner_allowed[0] == custom_scope["allowed_paths"]


@pytest.mark.parametrize("bad_scope", [
    "not_a_dict",
    None,
    {},
    {"allowed_paths": ["a.py"]},
    {"regression_tests": ["tests/t.py"]},
    {"allowed_paths": [], "regression_tests": ["tests/t.py"]},
    {"allowed_paths": ["a.py"], "regression_tests": []},
    {"allowed_paths": ["/abs/path.py"], "regression_tests": ["tests/t.py"]},
    {"allowed_paths": ["a.py"], "regression_tests": ["/abs/test.py"]},
    {"allowed_paths": ["../escape.py"], "regression_tests": ["tests/t.py"]},
    {"allowed_paths": ["sub/../../escape.py"], "regression_tests": ["tests/t.py"]},
    {"allowed_paths": ["a\\b.py"], "regression_tests": ["tests/t.py"]},
    {"allowed_paths": ["a.py"], "regression_tests": ["tests\\t.py"]},
    {"allowed_paths": [123], "regression_tests": ["tests/t.py"]},
    {"allowed_paths": ["a.py"], "regression_tests": [None]},
    {"allowed_paths": ["a.py", "a.py"], "regression_tests": ["tests/t.py"]},
    {"allowed_paths": ["a.py"], "regression_tests": ["tests/t.py", "tests/t.py"]},
])
def test_resolve_scope_invalid_inputs(bad_scope):
    """(c) resolve_scope 잘못된 입력 ValueError: 빈 목록, 절대경로, '..', 역슬래시, 비문자열, 키 누락, 중복."""
    if bad_scope is None:
        return
    with pytest.raises(ValueError):
        chain.resolve_scope(bad_scope)


def test_resolve_scope_none_returns_defaults():
    """resolve_scope(None) 호출 시 기본 설정 복사본 반환."""
    resolved = chain.resolve_scope(None)
    assert resolved["allowed_paths"] == list(chain._SETTINGS["allowed_paths"])
    assert resolved["regression_tests"] == list(chain._SETTINGS["regression_tests"])
    resolved["allowed_paths"].append("extra.py")
    assert "extra.py" not in chain._SETTINGS["allowed_paths"]


def test_legacy_step_fn_with_four_positional_args_works():
    """(d) 4개 인자만 받는 기존 형식 step_fn 주입 시에도 동작."""
    calls = []

    def legacy_step(persona, system_prompt, human_text, mode):
        calls.append((persona, mode))
        if persona == "PARTNER" and mode == "write":
            return {"output": "fixed", "tool_evidence": [{"content": json.dumps(STAGED_MOCK)}]}
        outputs = {
            "ORCHESTRATOR": "| 단계 |\nPLAN: BUG_HUNTER, PARTNER, TESTER",
            "REVIEWER": "VERDICT: APPROVE",
            "TESTER": "VERDICT: PASS",
        }
        return {"output": outputs.get(persona, "analysis"), "tool_evidence": []}

    def fake_regression(tests):
        return {"ok": True, "tests": tests}

    custom_scope = {
        "allowed_paths": ["legacy/target.py"],
        "regression_tests": ["harness/tests/test_legacy.py"],
    }
    out = chain.run_chain("fix with legacy step", staged_fn=_dummy_staged, step_fn=legacy_step,
                          regression_fn=fake_regression, round_no=1, scope=custom_scope)
    assert out["verdict"] == "PASS"
    assert len(calls) >= 1

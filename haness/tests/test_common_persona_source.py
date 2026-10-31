"""common/persona_source.py 테스트(2026-10-25: persona_source 공통 기능을 common으로 분리).

- 원문 프롬프트를 그대로 읽는지(13개, sha256은 test_persona_repair_chain에서 검증)
- 잘못된 이름·없는 파일·잘못된 계획은 예외/None으로 실패하고 대체하지 않는지
- Gemini 블록 응답도 텍스트로 해석하는지
"""
from __future__ import annotations

from pathlib import Path

import pytest

from common.persona_source import PERSONA_NAMES, PersonaSource

ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture()
def ps():
    return PersonaSource()


def test_default_dir_is_config_and_all_13_load_verbatim(ps):
    assert ps.persona_dir == ROOT / "haness/personas/references"
    prompts = ps.load_all()
    assert set(prompts) == set(PERSONA_NAMES) and len(prompts) == 13
    assert prompts["PARTNER"] == (ROOT / "haness/personas/references/partner.md").read_text(encoding="utf-8")


@pytest.mark.parametrize("bad", ["", "partner", "../x", "A" * 40, None, 3])
def test_invalid_name_rejected(ps, bad):
    with pytest.raises(ValueError):
        ps.load(bad)


def test_missing_file_is_error_not_substitute(tmp_path):
    with pytest.raises(FileNotFoundError):
        PersonaSource(tmp_path).load("PARTNER")


def test_available_excludes_orchestrator(ps):
    names = ps.available()
    assert len(names) == 12 and "ORCHESTRATOR" not in names


def test_content_text_handles_gemini_blocks(ps):
    blocks = [{"type": "text", "text": "PLAN: "}, {"type": "signature", "data": "x"}, {"type": "text", "text": "PARTNER"}]
    assert ps.content_text(blocks) == "PLAN: PARTNER"
    with pytest.raises(ValueError):
        ps.content_text(123)


@pytest.mark.parametrize("text", ["{}", '{"personas":[]}', '{"personas":["UNKNOWN"]}', '{"personas":[1]}',
                                  "not json", '["PARTNER"]', '{"personas":["A","B","C","D","E","F"]}'])
def test_plan_json_invalid_has_no_fallback(ps, text):
    with pytest.raises((ValueError, TypeError)):
        ps.parse_plan_json(text, PERSONA_NAMES, 5)


def test_plan_json_keeps_order_and_repeats(ps):
    assert ps.parse_plan_json('```json\n{"personas":["REVIEWER","PARTNER","TESTER","TESTER"]}\n```',
                              PERSONA_NAMES, 5) == ["REVIEWER", "PARTNER", "TESTER", "TESTER"]


def test_plan_line(ps):
    allowed = ps.available()
    assert ps.parse_plan_line("x\nPLAN: TESTER, partner → ARCHITECT, HACKER, TESTER", allowed, 5) == (
        ["TESTER", "PARTNER", "ARCHITECT"], ["HACKER"])
    assert ps.parse_plan_line("계획 없음", allowed, 5) == (None, [])
    assert ps.parse_plan_line("PLAN: A_X, PARTNER, TESTER", allowed, 2) == (["PARTNER"], ["A_X"])


def test_verdict(ps):
    assert ps.parse_verdict("VERDICT: FAIL\n...\nVERDICT: PASS") == "PASS"
    assert ps.parse_verdict("판정 없음") == "미확인"
    assert ps.parse_verdict([{"type": "text", "text": "VERDICT: HOLD"}]) == "HOLD"

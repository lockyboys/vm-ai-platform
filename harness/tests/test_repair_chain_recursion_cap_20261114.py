"""수리 체인 LangGraph recursion_limit 상한 20 검증 (LuckyBoys 2026-11-14 지시).

배경
    메리츠 document_collect 수리 중 체인이 같은 자리를 맴돌았다(이전에는 GraphRecursionError(64)까지 감).
    지시: "수리 체인 LLM 호출 단계는 LangGraph recursion_limit 으로 제한되며 최대 20까지로 한다".
검증 내용
    1) 공통 설정(config.AUTODISCOVER_SELF_REPAIR['agent_recursion_limit'])이 1~20 범위인지
    2) persona_repair_chain 이 그 설정값을 그대로 읽어 쓰는지(별도 하드코딩 값이 없는지)
    3) 잘못된 값(0, 음수, 21 이상)은 상한 검사에서 거부되는지 — 아래 _is_valid_cap 기준
"""
from pathlib import Path

import pytest

import config as project_config  # 루트 공통 설정(일반 지침 4)

CAP = 20  # LuckyBoys 지시 상한
CHAIN_PATH = Path(project_config.BASE_DIR) / "harness/mcp/agents/persona_repair_chain.py"


def _is_valid_cap(value) -> bool:
    """recursion_limit 값이 '양의 정수이면서 20 이하'인지 판정한다(bool 은 정수로 보지 않음)."""
    return isinstance(value, int) and not isinstance(value, bool) and 1 <= value <= CAP


def test_config_recursion_limit_is_capped_at_20():
    """공통 설정값이 상한 20 이하여야 한다(수정 전 64 → 이 테스트가 실패해 문제를 재현)."""
    value = project_config.AUTODISCOVER_SELF_REPAIR["agent_recursion_limit"]
    assert _is_valid_cap(value), f"agent_recursion_limit={value!r} 는 1~{CAP} 범위가 아님"


def test_chain_reads_recursion_limit_from_config():
    """체인 소스가 설정값을 읽어 쓰고, 숫자를 직접 박아 넣지 않았는지 확인한다."""
    text = CHAIN_PATH.read_text(encoding="utf-8")
    assert text.count('int(_SETTINGS["agent_recursion_limit"])') >= 2  # run_step·graph.invoke 두 곳
    assert '"recursion_limit": 64' not in text


@pytest.mark.parametrize("bad", [0, -1, 21, 64, True, "20", None, 20.0])
def test_invalid_caps_are_rejected(bad):
    """잘못된 입력(0·음수·상한 초과·bool·문자열·None·실수)은 모두 거부되어야 한다."""
    assert not _is_valid_cap(bad)


@pytest.mark.parametrize("good", [1, 10, 20])
def test_valid_caps_are_accepted(good):
    """1~20 정수는 허용된다."""
    assert _is_valid_cap(good)

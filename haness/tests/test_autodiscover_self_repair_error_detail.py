"""run_partner 오류 기록 테스트 — 묶인 오류(ExceptionGroup)의 실제 원인을 보고서에 남긴다.

20261030 | 요청: LuckyBoys | 작성: Claude
재현: 2026-10-30 00:26 samsung_fire_terms2 수리 보고서에 "ExceptionGroup: unhandled errors in a TaskGroup
      (1 sub-exception)"만 남고 안쪽 실제 원인이 빠졌다(asyncio TaskGroup이 원인을 묶어 던짐).
기대: run_partner의 error에 안쪽 오류 종류·메시지·발생 위치(파일:줄)가 들어간다. 일반 오류는 예전처럼 기록.
"""
from __future__ import annotations

import pytest

from haness.mcp.agents import autodiscover_self_repair as sr
from haness.mcp.agents import persona_repair_chain as chain


def _raise_inner():
    raise ConnectionError("model endpoint refused")


def _group() -> BaseException:
    """asyncio TaskGroup과 같은 모양: 바깥 묶음 안에 또 묶음, 그 안에 실제 원인."""
    try:
        _raise_inner()
    except ConnectionError as inner:
        cause = inner
    return ExceptionGroup("unhandled errors in a TaskGroup", [ExceptionGroup("nested", [cause])])


def test_describe_error_unwraps_nested_group_with_location():
    text = sr.describe_error(_group())
    assert "ConnectionError: model endpoint refused" in text
    assert "test_autodiscover_self_repair_error_detail.py:" in text      # 원인이 난 파일:줄
    assert text.startswith("ExceptionGroup")                              # 바깥 묶음 이름도 남김


def test_describe_error_keeps_plain_error_format():
    assert sr.describe_error(ValueError("bad input")) == "ValueError: bad input"


def test_describe_error_is_bounded():
    group = ExceptionGroup("many", [RuntimeError("x" * 5000) for _ in range(50)])
    assert len(sr.describe_error(group)) <= sr.MAX_ERROR_DETAIL_CHARS


@pytest.mark.parametrize("bad", [None, "text", 3])
def test_describe_error_rejects_non_exception(bad):
    with pytest.raises(TypeError):
        sr.describe_error(bad)


def test_run_partner_reports_inner_cause(monkeypatch):
    def boom(*args, **kwargs):
        raise _group()
    monkeypatch.setattr(chain, "run_chain", boom)
    out = sr.run_partner("task", 1)
    assert out["verdict"] == "ERROR" and "ConnectionError: model endpoint refused" in out["error"]

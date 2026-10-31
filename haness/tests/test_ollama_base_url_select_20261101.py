"""PARTNER Ollama 주소 자동 선택 검증 (2026-11-01, LuckyBoys 선택 ①).

배경: 프로브가 붙는 127.0.0.1:11434는 개발 서버의 CPU 전용 Ollama였다(GPU 0%, 로딩 18~30초).
      GPU 서버(켤 때마다 IP 변경)·노트북 터널(11435)을 켜 두면 그쪽을 먼저 쓰게 한다.
규칙:
  - SPS_SOURCE_PARTNER_OLLAMA_BASE_URL(또는 OLLAMA_BASE_URL)을 직접 지정하면 그 주소만 쓴다(수동 고정, 확인 호출 없음).
  - 지정이 없으면 SPS_SOURCE_PARTNER_OLLAMA_CANDIDATES 순서대로 /api/version을 확인해 처음 응답하는 주소를 쓴다.
  - 기본 순서: GPU 서버(SPS_GPU_SSH_HOST):11434 → 노트북 터널 127.0.0.1:11435 → 개발 서버 127.0.0.1:11434.
이 테스트는 실제 네트워크를 쓰지 않는다(probe_fn 대역 사용).
"""
import importlib
import math

import pytest

import config
from common import common_function
from haness.mcp.agents import source_partner_agent

GPU, TUNNEL, LOCAL = "http://10.0.0.9:11434", "http://127.0.0.1:11435", "http://127.0.0.1:11434"


def _probe(alive):
    """alive에 든 주소만 응답하는 가짜 확인 함수. 호출 순서를 calls에 남긴다."""
    calls = []

    def probe(url, timeout):
        calls.append((url, timeout))
        if url not in alive:
            raise ConnectionError("refused")

    return probe, calls


# ───────────── 정상 동작 ─────────────

def test_pinned_url_is_used_without_probing():
    probe, calls = _probe(alive=set())
    out = common_function.resolve_ollama_base_url(LOCAL, [GPU, TUNNEL], 3, probe_fn=probe)
    assert out == {"base_url": LOCAL, "mode": "pinned", "tried": []}
    assert calls == []  # 수동 고정이면 확인 호출을 하지 않는다


def test_first_responsive_candidate_wins_in_order():
    probe, calls = _probe(alive={TUNNEL, LOCAL})
    out = common_function.resolve_ollama_base_url("", [GPU, TUNNEL, LOCAL], 3, probe_fn=probe)
    assert out["base_url"] == TUNNEL and out["mode"] == "auto"
    assert [c[0] for c in calls] == [GPU, TUNNEL]  # 찾으면 뒤 후보는 확인하지 않는다
    assert out["tried"][0]["ok"] is False and "ConnectionError" in out["tried"][0]["error"]


def test_gpu_server_preferred_when_on():
    probe, _ = _probe(alive={GPU, TUNNEL, LOCAL})
    assert common_function.resolve_ollama_base_url("", [GPU, TUNNEL, LOCAL], 3, probe_fn=probe)["base_url"] == GPU


def test_all_candidates_down_raises_with_evidence():
    probe, _ = _probe(alive=set())
    with pytest.raises(RuntimeError) as info:
        common_function.resolve_ollama_base_url("", [GPU, LOCAL], 3, probe_fn=probe)
    assert GPU in str(info.value) and LOCAL in str(info.value)  # 무엇을 시도했는지 오류에 남긴다


def test_trailing_slash_is_normalized():
    probe, _ = _probe(alive={TUNNEL})
    assert common_function.resolve_ollama_base_url("", [TUNNEL + "/"], 3, probe_fn=probe)["base_url"] == TUNNEL


# ───────────── 잘못된 입력 ─────────────

@pytest.mark.parametrize("bad", [[], (), None, "http://x:1", [""], ["ftp://x:1"], ["127.0.0.1:11434"], [123]])
def test_invalid_candidates_rejected(bad):
    probe, calls = _probe(alive={LOCAL})
    with pytest.raises(ValueError):
        common_function.resolve_ollama_base_url("", bad, 3, probe_fn=probe)
    assert calls == []  # 검증 실패 시 네트워크를 건드리지 않는다


@pytest.mark.parametrize("bad", [0, -1, math.nan, math.inf, "3", None, True])
def test_invalid_probe_timeout_rejected(bad):
    probe, _ = _probe(alive={LOCAL})
    with pytest.raises(ValueError):
        common_function.resolve_ollama_base_url("", [LOCAL], bad, probe_fn=probe)


@pytest.mark.parametrize("bad", ["ftp://x:1", "localhost:11434", 5])
def test_invalid_pinned_url_rejected(bad):
    with pytest.raises(ValueError):
        common_function.resolve_ollama_base_url(bad, [LOCAL], 3, probe_fn=_probe({LOCAL})[0])


# ───────────── 설정 기본값 ─────────────

def test_config_default_candidate_order(monkeypatch):
    """기본 순서는 GPU(SPS_GPU_SSH_HOST) → 노트북 터널 → 개발 서버. IP는 환경변수 하나로 바뀐다."""
    monkeypatch.delenv("SPS_SOURCE_PARTNER_OLLAMA_CANDIDATES", raising=False)
    monkeypatch.setenv("SPS_GPU_SSH_HOST", "10.0.0.9")
    try:
        c = importlib.reload(config)
        assert c.SPS_SOURCE_PARTNER_OLLAMA_CANDIDATES == (GPU, TUNNEL, LOCAL)
        assert c.SPS_SSH_TARGETS["gpu"]["host"] == "10.0.0.9"  # ssh와 같은 값을 쓴다
        assert c.SPS_SOURCE_PARTNER_OLLAMA_PROBE_TIMEOUT_SECONDS == 3.0
    finally:
        monkeypatch.delenv("SPS_GPU_SSH_HOST", raising=False)
        importlib.reload(config)


def test_config_candidates_env_override(monkeypatch):
    monkeypatch.setenv("SPS_SOURCE_PARTNER_OLLAMA_CANDIDATES", f" {TUNNEL} , ,{LOCAL} ")
    try:
        assert importlib.reload(config).SPS_SOURCE_PARTNER_OLLAMA_CANDIDATES == (TUNNEL, LOCAL)
    finally:
        monkeypatch.delenv("SPS_SOURCE_PARTNER_OLLAMA_CANDIDATES", raising=False)
        importlib.reload(config)


def test_config_base_url_empty_means_auto(monkeypatch):
    """주소를 지정하지 않으면 빈 값(=자동 선택)이어야 한다. 예전 기본값 11434 고정을 없앤다."""
    monkeypatch.delenv("SPS_SOURCE_PARTNER_OLLAMA_BASE_URL", raising=False)
    monkeypatch.delenv("OLLAMA_BASE_URL", raising=False)
    try:
        assert importlib.reload(config).SPS_SOURCE_PARTNER_OLLAMA_BASE_URL == ""
    finally:
        importlib.reload(config)


# ───────────── PARTNER 연결 ─────────────

def test_build_model_uses_auto_selected_url(monkeypatch):
    captured = {}

    class FakeOllama:
        def __init__(self, **kwargs):
            captured.update(kwargs)

    cfg = source_partner_agent.project_config
    monkeypatch.setattr(cfg, "SPS_SOURCE_PARTNER_MODEL_PROVIDER", "ollama", raising=False)
    monkeypatch.setattr(cfg, "SPS_SOURCE_PARTNER_OLLAMA_BASE_URL", "", raising=False)
    monkeypatch.setattr(cfg, "SPS_SOURCE_PARTNER_OLLAMA_CANDIDATES", (GPU, TUNNEL), raising=False)
    monkeypatch.setattr(cfg, "SPS_SOURCE_PARTNER_OLLAMA_PROBE_TIMEOUT_SECONDS", 3.0, raising=False)
    monkeypatch.setattr(source_partner_agent, "ChatOllama", FakeOllama, raising=False)
    seen = {}

    def fake_resolve(pinned, candidates, timeout):
        seen["args"] = (pinned, tuple(candidates), timeout)
        return {"base_url": TUNNEL, "mode": "auto", "tried": []}

    monkeypatch.setattr(source_partner_agent, "resolve_ollama_base_url", fake_resolve)
    source_partner_agent._build_model()
    assert captured["base_url"] == TUNNEL
    assert seen["args"] == ("", (GPU, TUNNEL), 3.0)

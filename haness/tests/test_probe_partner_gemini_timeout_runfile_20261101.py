"""작업 ②(제공자별 대기 시간)·③(run_id 결과 파일) 검증 (2026-11-01, LuckyBoys 요청).

② 배경: 프로브가 Gemini에도 Ollama용 대기 시간(SPS_SOURCE_PARTNER_OLLAMA_TIMEOUT_SECONDS)을 썼다.
   → config.py에 SPS_SOURCE_PARTNER_GEMINI_TIMEOUT_SECONDS(환경변수로 변경 가능, 기본 300초)를 두고
     프로브가 제공자에 맞는 값을 쓰게 한다(timeout_for).
③ 배경: MCP 연결이 끊기면 프로브 결과를 받을 길이 없었다(결과 파일 이름이 끝날 때 정해졌기 때문).
   → run_id로 파일 이름을 미리 정하고(evidence_path), 시작 시 state=running 기록 → 끝나면 같은 파일을
     최종 결과로 교체한다(_run_with_result_file).
LuckyBoys 결정(2026-11-01): 함수 이름은 test_probe_partner_timeout_20261031.py의 계약
(timeout_for / evidence_path / EVIDENCE_DIR)에 맞춘다. 이 파일은 그 계약을 더 촘촘히 검사한다.

이 테스트는 실제 LLM·네트워크를 호출하지 않는다(가짜 작업 함수와 임시 폴더만 사용).
"""
import importlib
import json
import math
from types import SimpleNamespace

import pytest

import config
from haness.scripts import probe_partner_providers_20261025 as probe


# ───────────────────────── ② 제공자별 대기 시간 ─────────────────────────

def test_config_has_gemini_timeout_default_300(monkeypatch):
    """환경변수가 없으면 기존 동작과 같은 300초가 기본값이어야 한다(LuckyBoys 결정)."""
    monkeypatch.delenv("SPS_SOURCE_PARTNER_GEMINI_TIMEOUT_SECONDS", raising=False)
    reloaded = importlib.reload(config)
    assert reloaded.SPS_SOURCE_PARTNER_GEMINI_TIMEOUT_SECONDS == 300.0


def test_config_gemini_timeout_env_override(monkeypatch):
    """환경변수로 값을 바꿀 수 있어야 한다(코드 수정 없이 조정)."""
    monkeypatch.setenv("SPS_SOURCE_PARTNER_GEMINI_TIMEOUT_SECONDS", "45")
    try:
        assert importlib.reload(config).SPS_SOURCE_PARTNER_GEMINI_TIMEOUT_SECONDS == 45.0
    finally:
        # 다른 테스트에 영향을 주지 않도록 기본값으로 되돌린다.
        monkeypatch.delenv("SPS_SOURCE_PARTNER_GEMINI_TIMEOUT_SECONDS", raising=False)
        importlib.reload(config)


def _fake_config(gemini, ollama):
    """제공자별 값이 서로 다른 가짜 설정. 어느 값을 골랐는지 구분하기 위해 다르게 준다."""
    return SimpleNamespace(SPS_SOURCE_PARTNER_GEMINI_TIMEOUT_SECONDS=gemini,
                           SPS_SOURCE_PARTNER_OLLAMA_TIMEOUT_SECONDS=ollama)


def test_timeout_for_selects_gemini_value():
    assert probe.timeout_for(_fake_config(11, 222), "gemini") == 11.0


def test_timeout_for_selects_ollama_value():
    assert probe.timeout_for(_fake_config(11, 222), "ollama") == 222.0


@pytest.mark.parametrize("bad", [0, -1, math.nan, math.inf, "abc", None])
def test_timeout_for_rejects_invalid_value(bad):
    """잘못된 대기 시간(0·음수·NaN·무한·숫자 아님)은 실행 전에 거부해야 한다."""
    with pytest.raises(ValueError):
        probe.timeout_for(_fake_config(bad, 300), "gemini")


def test_timeout_for_rejects_unknown_provider():
    with pytest.raises(ValueError):
        probe.timeout_for(_fake_config(300, 300), "openai")


# ───────────────────────── ③ run_id 결과 파일 ─────────────────────────

@pytest.mark.parametrize("bad", [None, "", "../x", "a/b", "a b", "x" * 65, 123])
def test_evidence_path_rejects_invalid_run_id(bad):
    """run_id는 파일 이름에 들어가므로 영숫자·_·-만, 1~64자만 허용(경로 이탈 차단)."""
    with pytest.raises(ValueError):
        probe.evidence_path("gemini", bad)


def test_evidence_path_is_fixed_by_run_id(tmp_path, monkeypatch):
    """같은 run_id면 실행 전에 항상 같은 경로가 나와야 연결이 끊겨도 찾아 읽을 수 있다."""
    monkeypatch.setattr(probe, "EVIDENCE_DIR", tmp_path)
    assert probe.evidence_path("gemini", "20261101_x") == tmp_path / "provider_live_probe_gemini_20261101_x.json"


def test_existing_run_id_is_rejected(tmp_path):
    """이미 쓰인 run_id는 거부해 기존 증빙을 덮어쓰지 않는다."""
    path = tmp_path / "provider_live_probe_gemini_dup.json"
    path.write_text("{}", encoding="utf-8")
    with pytest.raises(FileExistsError):
        probe._run_with_result_file(path, {"run_id": "dup"}, lambda result: None)
    assert path.read_text(encoding="utf-8") == "{}"


def test_running_state_is_written_before_work_and_replaced_after(tmp_path):
    """작업 도중 파일을 읽으면 running, 끝나면 같은 파일이 completed 최종 결과여야 한다."""
    path = tmp_path / "provider_live_probe_ollama_flow_ok.json"
    seen = {}

    def work(result):
        # 작업 도중(=MCP 연결이 끊긴 상황)에 다른 쪽이 파일을 읽는 것을 흉내 낸다.
        seen["during"] = json.loads(path.read_text(encoding="utf-8"))
        result["answer"] = "42"

    final = probe._run_with_result_file(path, {"run_id": "flow_ok"}, work)
    stored = json.loads(path.read_text(encoding="utf-8"))
    assert seen["during"]["state"] == "running"
    assert stored["state"] == "completed" and stored["answer"] == "42"
    assert stored == json.loads(json.dumps(final, default=str))
    assert "finished_kst" in stored and "elapsed_seconds" in stored
    assert not path.with_suffix(".tmp").exists()  # 임시 파일이 남지 않아야 한다


def test_failure_is_recorded_as_failed_not_left_running(tmp_path):
    """작업이 예외로 끝나도 running으로 방치하지 않고 failed와 오류를 남겨야 한다."""
    path = tmp_path / "provider_live_probe_ollama_flow_fail.json"

    def work(result):
        raise TimeoutError("model did not answer")

    probe._run_with_result_file(path, {"run_id": "flow_fail"}, work)
    stored = json.loads(path.read_text(encoding="utf-8"))
    assert stored["state"] == "failed"
    assert stored["error_type"] == "TimeoutError"
    assert "model did not answer" in stored["error"]

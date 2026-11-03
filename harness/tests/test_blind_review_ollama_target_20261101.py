"""블라인드 리뷰 실행 대상(ollama_target)·모델(ollama_model) 선택 검증 (2026-11-01, LuckyBoys: GPU 서버 12b 실험).

규칙:
  - 대상 주소는 config.BLIND_REVIEW_OLLAMA_ENDPOINTS(laptop|gpu), 모델별 기대 지문은 config.BLIND_REVIEW_MODEL_DIGESTS.
    목록에 없는 대상·모델은 거부한다(임의 URL·임의 모델로 82건을 돌리지 않게).
  - 기본값: 대상 laptop, 모델 config.OLLAMA_MODEL → 기존 실행과 동일.
  - 워커는 고른 모델의 지문으로 확인한다(예전 고정 DIGEST와 같은 값이 e4b/latest에 들어 있어야 함).
  - submit 은 대상·모델을 워커 stdin과 request.json에 기록하고, 이어서 실행은 이전 값을 쓰며 다른 값은 거부한다.
"""
import importlib.util
import json
from pathlib import Path

import pytest

import config
from harness.mcp.tools import blind_review_jobs_v2 as jobs

_spec = importlib.util.spec_from_file_location(
    "blind_worker_target_test", Path(config.PROJECT_ROOT) / "harness/apps/blind_review_20261027/blind_worker.py")
worker = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(worker)

E4B_DIGEST = "dc35e8d9c6061baa6f0fa870975ab6932e2542b579b13ea0f199fa4bb7300c9c"  # 노트북·GPU 서버 공통(실측)
OLD = "c" * 32


# ───────────── 설정 ─────────────

def test_config_targets_and_digests():
    assert config.BLIND_REVIEW_OLLAMA_ENDPOINTS["laptop"] == config.OLLAMA_ENDPOINT
    assert config.BLIND_REVIEW_OLLAMA_ENDPOINTS["gpu"].startswith("http://")
    assert config.BLIND_REVIEW_MODEL_DIGESTS["gemma4:e4b"] == E4B_DIGEST
    assert config.BLIND_REVIEW_MODEL_DIGESTS["gemma4:latest"] == E4B_DIGEST
    d12 = config.BLIND_REVIEW_MODEL_DIGESTS["gemma4:12b-it-q4_K_M"]
    assert d12.startswith("6114515d63c1") and len(d12) == 64  # GPU 서버 ollama list 실측 앞 12자리


def test_legacy_worker_digest_matches_e4b():
    """예전 고정값(DIGEST)이 e4b 지문과 같아야 기본 동작이 바뀌지 않는다."""
    assert worker.DIGEST == E4B_DIGEST


# ───────────── 워커 ─────────────

def test_worker_resolves_gpu_12b():
    endpoint, model, digest = worker.resolve_ollama("gpu", "gemma4:12b-it-q4_K_M")
    assert endpoint == config.BLIND_REVIEW_OLLAMA_ENDPOINTS["gpu"]
    assert model == "gemma4:12b-it-q4_K_M" and digest.startswith("6114515d63c1")


def test_worker_default_is_previous_behavior():
    assert worker.resolve_ollama("laptop", config.OLLAMA_MODEL) == (config.OLLAMA_ENDPOINT, config.OLLAMA_MODEL, E4B_DIGEST)


def test_worker_options_per_target():
    """노트북(6GB)은 num_gpu·num_batch 를 config 값 그대로 보낸다(기존 실행과 동일).
    GPU 서버(L4 24GB)는 num_gpu(전 층 GPU)·num_batch 를 보내지 않는다.
    2026-11-01 실측: GPU 서버 gemma4:12b-it-q4_K_M 은 num_batch=32 를 주면 CLIP(비전) 로딩 실패로 HTTP 500,
    num_batch 를 빼면 정상(curl A/B 시험). num_ctx 8192 는 문제없음."""
    laptop = worker.options_for("laptop")
    assert laptop["num_gpu"] == config.OLLAMA_NUM_GPU
    assert laptop["num_batch"] == config.OLLAMA_NUM_BATCH
    gpu = worker.options_for("gpu")
    assert "num_gpu" not in gpu and "num_batch" not in gpu
    # 출력 길이·문맥·온도(num_ctx·num_predict·temperature)는 두 대상이 같아야 비교가 공정하다
    assert {k: v for k, v in laptop.items() if k not in ("num_gpu", "num_batch")} == gpu


@pytest.mark.parametrize("target,model", [
    ("cloud", "gemma4:e4b"), ("", "gemma4:e4b"), (None, "gemma4:e4b"), ("http://evil:11434", "gemma4:e4b"),
    ("gpu", "llama3:70b"), ("gpu", ""), ("gpu", None), ("gpu", 7)])
def test_worker_rejects_unknown_target_or_model(target, model):
    with pytest.raises(ValueError):
        worker.resolve_ollama(target, model)


# ───────────── 제출 도구 ─────────────

@pytest.fixture
def env(tmp_path, monkeypatch):
    monkeypatch.setattr(jobs, "JOB_ROOT", tmp_path)
    calls = []

    class FakePopen:
        def __init__(self, cmd, **kwargs):
            self.pid = 888
            self.sent = []
            self.stdin = type("S", (), {"write": lambda s, d: self.sent.append(d), "close": lambda s: None})()
            calls.append(self)

    monkeypatch.setattr(jobs.subprocess, "Popen", FakePopen)
    monkeypatch.setattr(jobs, "_alive", lambda pid: False)
    return tmp_path, calls


def _sent(call):
    return json.loads(b"".join(call.sent).decode())


def test_submit_defaults_to_laptop_and_config_model(env):
    _, calls = env
    req = jobs.submit("ollama")
    sent = _sent(calls[0])
    assert sent["ollama_target"] == "laptop" and sent["ollama_model"] == config.OLLAMA_MODEL
    assert req["ollama_target"] == "laptop"


def test_submit_gpu_12b_bug_focus(env):
    root, calls = env
    req = jobs.submit("ollama", prompt_variant="bug_focus", ollama_target="gpu", ollama_model="gemma4:12b-it-q4_K_M")
    sent = _sent(calls[0])
    assert (sent["ollama_target"], sent["ollama_model"], sent["prompt_variant"]) == ("gpu", "gemma4:12b-it-q4_K_M", "bug_focus")
    saved = json.loads((root / req["job_id"] / "request.json").read_text())
    assert saved["ollama_model"] == "gemma4:12b-it-q4_K_M"


@pytest.mark.parametrize("kwargs", [{"ollama_target": "cloud"}, {"ollama_model": "llama3:70b"},
                                    {"ollama_target": 1}, {"ollama_model": ["gemma4:e4b"]}])
def test_submit_rejects_unknown_before_launch(env, kwargs):
    _, calls = env
    with pytest.raises(ValueError):
        jobs.submit("ollama", **kwargs)
    assert calls == []


def _old_job(root, **extra):
    d = root / OLD
    d.mkdir()
    (d / "request.json").write_text(json.dumps({"job_id": OLD, "provider": "ollama", "pid": 1, **extra}), encoding="utf-8")


def test_resume_keeps_previous_target_and_model(env):
    root, calls = env
    _old_job(root, ollama_target="gpu", ollama_model="gemma4:12b-it-q4_K_M", prompt_variant="review")
    jobs.submit("ollama", resume_job_id=OLD)
    sent = _sent(calls[0])
    assert (sent["ollama_target"], sent["ollama_model"]) == ("gpu", "gemma4:12b-it-q4_K_M")


def test_resume_of_legacy_job_uses_laptop_default(env):
    root, calls = env
    _old_job(root)
    jobs.submit("ollama", resume_job_id=OLD)
    sent = _sent(calls[0])
    assert (sent["ollama_target"], sent["ollama_model"]) == ("laptop", config.OLLAMA_MODEL)


def test_resume_with_different_model_rejected(env):
    root, calls = env
    _old_job(root, ollama_target="gpu", ollama_model="gemma4:e4b")
    with pytest.raises(ValueError, match="ollama_model"):
        jobs.submit("ollama", resume_job_id=OLD, ollama_model="gemma4:12b-it-q4_K_M")
    assert calls == []

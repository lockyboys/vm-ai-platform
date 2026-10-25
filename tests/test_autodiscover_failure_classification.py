"""자동 탐색 실패 유형 구분 테스트(2026-10-25 LuckyBoys: "새 유형이면 3번 재시도 없이 바로 보고").

규칙:
- retryable(다른 항목으로 다시 하면 풀릴 수 있음: 시간 초과·네트워크·빈 목록·문서 손상 등) → 다음 항목으로 재탐색
- systematic(처음 보는 유형: 규칙·비교 방식·인코딩 문제 등) → 즉시 중단, NEEDS_NEW_RULE + 증빙 파일
- retryable이라도 같은 오류가 연속 2번이면 항목 문제가 아니므로 즉시 중단(헛된 반복 금지)
"""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def ad():
    spec = importlib.util.spec_from_file_location(
        "autodiscover_classify", ROOT / "FastAPI/LangGraph/Agent_Import_PFDs/profile_autodiscover.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.mark.parametrize("message", [
    "TimeoutError: Page.goto: Timeout 45000ms exceeded",
    "URLError: <urlopen error [Errno 104] Connection reset by peer>",
    "HTTPError: HTTP Error 503: Service Unavailable",
    "ValueError: empty list at /goods/getList2.do for seed {'a': 1}",
    "ValueError: no valid document for seed {'a': 1}: []",
])
def test_retryable_errors(ad, message):
    assert ad.classify_failure(message) == "retryable"


@pytest.mark.parametrize("message", [
    "ValueError: cannot link request value: step 1 _r_='0.55'",
    "ValueError: document button for 'x.pdf' was not on screen; chain=[...]",
    "ValueError: not a complete PDF (header/EOF)",
    "ValueError: download request does not contain the file name",
    "KeyError: 'list3'",
])
def test_unknown_or_rule_errors_are_systematic(ad, message):
    assert ad.classify_failure(message) == "systematic"


def test_signature_ignores_numbers_and_quoted_values(ad):
    a = ad.failure_signature("ValueError: cannot link request value: step 1 _r_='0.5566'")
    b = ad.failure_signature("ValueError: cannot link request value: step 1 _r_='0.8633'")
    assert a == b


def _patch(ad, monkeypatch, tmp_path, errors):
    """discover가 차례로 errors를 던지게 하고, 호출 횟수를 센다."""
    calls = {"n": 0}

    def fake_discover(name, start_urls, keyword, choice):
        calls["n"] += 1
        error = errors[min(choice, len(errors) - 1)]
        if error is None:
            return {"name": name, "steps": []}
        raise error

    monkeypatch.setattr(ad, "discover", fake_discover)
    monkeypatch.setattr(ad, "validate_live", lambda profile: {"ok": True})
    monkeypatch.setattr(ad, "_profile_path", lambda name: tmp_path / "p.json")
    monkeypatch.setattr(ad, "_work_dir", lambda name: tmp_path)
    return calls


def test_systematic_error_stops_after_first_attempt(ad, monkeypatch, tmp_path):
    calls = _patch(ad, monkeypatch, tmp_path, [ValueError("not a complete PDF (header/EOF)")])
    report = ad.auto({"name": "p", "start_urls": [{"url": "https://x.org/a"}]})
    assert calls["n"] == 1                                   # 3번 돌지 않음
    assert report["result"] == "NEEDS_NEW_RULE"
    assert report["failure"]["category"] == "systematic"
    evidence = json.loads(Path(report["failure"]["evidence"]).read_text(encoding="utf-8"))
    assert "not a complete PDF" in evidence["error"]


def test_retryable_error_tries_next_item_and_succeeds(ad, monkeypatch, tmp_path):
    calls = _patch(ad, monkeypatch, tmp_path, [ValueError("empty list at /a.do for seed {}"), None])
    report = ad.auto({"name": "p", "start_urls": [{"url": "https://x.org/a"}]})
    assert calls["n"] == 2 and report["result"].startswith("DISCOVERED_AND_VALID")


def test_same_retryable_error_twice_stops(ad, monkeypatch, tmp_path):
    error = ValueError("empty list at /a.do for seed {}")
    calls = _patch(ad, monkeypatch, tmp_path, [error, error, error])
    report = ad.auto({"name": "p", "start_urls": [{"url": "https://x.org/a"}]})
    assert calls["n"] == 2                                   # 같은 오류 반복 → 3번째 없음
    assert report["result"] == "NEEDS_NEW_RULE" and report["failure"]["category"] == "repeated"

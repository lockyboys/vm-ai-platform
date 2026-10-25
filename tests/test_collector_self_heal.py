"""수집기 self_heal 테스트(2026-10-25 LuckyBoys: "probe가 실패하면 다시 탐색해 에이전트가 스스로").

흐름: probe 실패 → profile_autodiscover.auto(apply=True)로 재탐색·실검증·저장 → 프로파일 다시 읽어 재probe.
네트워크·브라우저 없이 가짜 probe/heal 함수로 흐름만 검증한다.
"""
from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
PKG = ROOT / "FastAPI/LangGraph/Agent_Import_PFDs"


def _load(name: str, file: str):
    spec = importlib.util.spec_from_file_location(name, PKG / file)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def mod():
    return _load("collector_self_heal", "public_document_catalog_collector.py")


@pytest.fixture(scope="module")
def ad():
    return _load("autodiscover_self_heal", "profile_autodiscover.py")


def test_probe_ok_does_not_heal(mod):
    calls = []
    result = mod.run_probe("p", True, load=lambda n: {"name": n},
                           probe_fn=lambda p: {"ok": 1}, heal_fn=lambda n: calls.append(n))
    assert result == {"ok": 1} and calls == []


def test_probe_failure_heals_then_reprobes(mod):
    state = {"version": 1}

    def probe_fn(profile):
        if profile["version"] == 1:
            raise ValueError("list path not found: result")   # 사이트 구조가 바뀐 상황 재현
        return {"seed_count": 2}

    def heal_fn(name):
        state["version"] = 2                                  # 재탐색이 새 프로파일을 저장
        return {"result": "DISCOVERED_AND_VALID_SAVED"}

    result = mod.run_probe("p", True, load=lambda n: {"name": n, "version": state["version"]},
                           probe_fn=probe_fn, heal_fn=heal_fn)
    assert result["probe"] == {"seed_count": 2}
    assert result["self_heal"]["result"] == "DISCOVERED_AND_VALID_SAVED"
    assert "list path not found" in result["first_error"]


def test_probe_failure_without_self_heal_raises(mod):
    def probe_fn(profile):
        raise ValueError("blocked")
    with pytest.raises(ValueError, match="blocked"):
        mod.run_probe("p", False, load=lambda n: {"name": n}, probe_fn=probe_fn, heal_fn=lambda n: None)


def test_heal_failure_is_reported_not_hidden(mod):
    def probe_fn(profile):
        raise ValueError("blocked")
    with pytest.raises(RuntimeError, match="self_heal failed"):
        mod.run_probe("p", True, load=lambda n: {"name": n}, probe_fn=probe_fn,
                      heal_fn=lambda n: {"result": "FAILED"})


@pytest.mark.parametrize("value", ["yes", 1, None])
def test_self_heal_option_must_be_bool(mod, value):
    with pytest.raises(ValueError):
        mod.parse_options({"mode": "probe", "profile": "p", "self_heal": value})


def test_self_heal_option_accepted(mod):
    assert mod.parse_options({"mode": "probe", "profile": "p", "self_heal": True})["self_heal"] is True


def test_auto_reuses_saved_start_urls(ad, monkeypatch, tmp_path):
    # 사람이 시작 URL을 다시 주지 않아도, 저장된 프로파일의 autodiscover 정보로 재탐색해야 한다.
    import json
    path = tmp_path / "p.json"
    path.write_text(json.dumps({"name": "p", "autodiscover": {
        "start_urls": [{"url": "https://x.org/a", "vars": {"sale_label": "on"}}], "document_keyword": "약관"}}),
        encoding="utf-8")
    seen = {}
    monkeypatch.setattr(ad, "_profile_path", lambda name: path)
    monkeypatch.setattr(ad, "validate_live", lambda profile: (_ for _ in ()).throw(ValueError("changed"))
                        if "steps" not in profile else {"ok": True})

    def fake_discover(name, start_urls, keyword, choice):
        seen.update(start_urls=start_urls, keyword=keyword)
        return {"name": name, "steps": []}

    monkeypatch.setattr(ad, "discover", fake_discover)
    report = ad.auto({"name": "p", "apply": True})
    assert seen == {"start_urls": [{"url": "https://x.org/a", "vars": {"sale_label": "on"}}], "keyword": "약관"}
    saved = json.loads(path.read_text(encoding="utf-8"))
    assert saved["autodiscover"]["document_keyword"] == "약관"   # 다음 재탐색을 위해 정보 보존
    assert report["result"] == "DISCOVERED_AND_VALID_SAVED"


def test_auto_without_any_start_urls_is_error(ad, monkeypatch, tmp_path):
    monkeypatch.setattr(ad, "_profile_path", lambda name: tmp_path / "none.json")
    report = ad.auto({"name": "p", "apply": True})
    assert report["result"] == "FAILED" and "start_urls" in report["attempts"][0]["error"]

"""새 보험사 온보딩 테스트(2026-10-25 LuckyBoys: "보험사 정보 주면 프로그램이 알아서", MCP 150초 안에).

onboard 모드는 입력만 검증하고 별도 systemd 작업을 띄운 뒤 바로 돌아온다(MCP 호출은 몇 초).
별도 작업(--onboard)은 시간 제한 없이 자동 탐색(+자기 수리) → 프로파일 저장 → 수집 워커까지 이어서 한다.
실제 브라우저·LLM·systemd는 쓰지 않고 함수 주입으로 검증한다.
"""
from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture()
def col(tmp_path, monkeypatch):
    spec = importlib.util.spec_from_file_location(
        "collector_onboard_t", ROOT / "FastAPI/LangGraph/Agent_Import_PFDs/public_document_catalog_collector.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    monkeypatch.setattr(module, "PROFILE_DIR", tmp_path / "profiles")
    (tmp_path / "profiles").mkdir()
    monkeypatch.setattr(module, "output_dir", lambda profile: (tmp_path / "out" / profile["name"]).mkdir(
        parents=True, exist_ok=True) or tmp_path / "out" / profile["name"])
    return module


def _req(**over):
    base = {"mode": "onboard", "profile": "kb_life_terms", "document_keyword": "약관",
            "start_urls": [{"url": "https://www.example-life.co.kr/disclosure/a.do", "vars": {"sale_label": "판매중"}},
                           {"url": "https://www.example-life.co.kr/disclosure/b.do", "vars": {"sale_label": "판매중지"}}]}
    base.update(over)
    return base


# --- 잘못된 입력 ---------------------------------------------------------------
@pytest.mark.parametrize("bad", [
    {"profile": "KB-Life"}, {"start_urls": []}, {"start_urls": "https://x.kr"},
    {"start_urls": [{"url": "ftp://x.kr/a"}]}, {"start_urls": [{"url": "/relative"}]},
    {"start_urls": [{"url": "https://a.kr/x"}, {"url": "https://b.kr/y"}]},
    {"start_urls": [{"url": "https://a.kr/x", "vars": "판매중"}]},
    {"document_keyword": ""}, {"document_keyword": "x" * 21}, {"time_limit_seconds": 0},
])
def test_invalid_onboard_request_rejected(col, bad):
    with pytest.raises(ValueError):
        col.parse_onboard(_req(**bad))


def test_existing_profile_is_not_overwritten(col, tmp_path):
    (tmp_path / "profiles/kb_life_terms.json").write_text("{}", encoding="utf-8")
    with pytest.raises(ValueError, match="already exists"):
        col.parse_onboard(_req())


# --- 시작: 바로 반환 ------------------------------------------------------------
def test_onboard_start_launches_unit_and_returns(col, tmp_path):
    calls = []

    class Done:
        returncode, stdout, stderr = 0, "", ""

    result = col.onboard_start(col.parse_onboard(_req()), run=lambda cmd, **k: calls.append(cmd) or Done())
    assert result["started"] is True and result["unit"] == "sps-collector-kb-life-terms"
    assert calls[0][:3] == list(col._SETTINGS["systemd_run_command"])[:3] and "--onboard" in calls[0]
    saved = json.loads((tmp_path / "out/kb_life_terms/onboard_request.json").read_text(encoding="utf-8"))
    assert saved["start_urls"][1]["vars"]["sale_label"] == "판매중지"
    assert json.loads((tmp_path / "out/kb_life_terms/status.json").read_text(encoding="utf-8"))["phase"] == "DISCOVER"


def test_onboard_start_reports_systemd_failure(col):
    class Fail:
        returncode, stdout, stderr = 1, "", "sudo: a password is required"

    with pytest.raises(RuntimeError, match="systemd-run failed"):
        col.onboard_start(col.parse_onboard(_req()), run=lambda cmd, **k: Fail())


# --- 별도 작업: 탐색(+수리) → 수집 ------------------------------------------------
def _prepare(col, tmp_path):
    request = col.parse_onboard(_req())
    out = tmp_path / "out/kb_life_terms"
    out.mkdir(parents=True, exist_ok=True)
    (out / "onboard_request.json").write_text(json.dumps(request, ensure_ascii=False), encoding="utf-8")
    return out


def test_onboard_worker_discovers_then_collects(col, tmp_path):
    out = _prepare(col, tmp_path)
    seen = {}
    report = col.onboard_worker("kb_life_terms", 600,
                                heal_fn=lambda req: seen.update(req=req) or {"result": "DISCOVERED_AND_VALID_SAVED"},
                                load=lambda name: {"name": name, "loaded": True},
                                worker_fn=lambda profile, limit: seen.update(profile=profile, limit=limit))
    assert report["result"] == "DISCOVERED_AND_VALID_SAVED"
    assert seen["req"]["apply"] is True and seen["req"]["start_urls"][0]["url"].endswith("a.do")
    assert seen["profile"]["loaded"] is True and seen["limit"] == 600
    assert (out / "onboard_report.json").exists()


@pytest.mark.parametrize("result", ["NEEDS_NEW_RULE", "REPAIR_FAILED", "FAILED"])
def test_onboard_worker_stops_when_not_fixed(col, tmp_path, result):
    out = _prepare(col, tmp_path)
    called = []
    col.onboard_worker("kb_life_terms", 600, heal_fn=lambda req: {"result": result},
                       load=lambda name: called.append("load"), worker_fn=lambda p, l: called.append("worker"))
    status = json.loads((out / "status.json").read_text(encoding="utf-8"))
    assert status["state"] == "FAILED" and status["phase"] == "DISCOVER" and status["result"] == result
    assert called == []

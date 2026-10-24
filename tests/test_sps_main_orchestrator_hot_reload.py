"""sps_main_orchestrator.py의 핫스왑(재시작 없는 자율 수정 반영) 회귀 테스트.

검증 의도:
- 크롤러 모듈이 아직 import된 적 없으면 importlib.import_module로 처음 가져오는지 확인한다.
- 이미 import된 상태면 importlib.reload로 다시 실행해 최신 함수를 가져오는지 확인한다.
기대 결과: 두 경우 모두 반환값은 (reload/import된) 모듈의 explore_unknown_site 함수다.
"""

import importlib
import os
import sys
import types
import importlib.util
from pathlib import Path

import pytest

os.environ.setdefault("GOOGLE_API_KEY", "offline-test-placeholder")
os.environ.setdefault("GEMINI_API_KEY", "offline-test-placeholder")

SOURCE_PATH = (
    Path(__file__).resolve().parents[1]
    / "FastAPI"
    / "LangGraph"
    / "sps_main_orchestrator.py"
)
SPEC = importlib.util.spec_from_file_location("sps_main_orchestrator_hotreload_under_test", SOURCE_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def _fake_sniffer_module(marker: str) -> types.ModuleType:
    """실제 Playwright/Gemini 의존성 없이 explore_unknown_site만 있는 가짜 모듈을 만든다."""
    fake = types.ModuleType(MODULE._SNIFFER_MODULE_NAME)

    async def explore_unknown_site(start_url: str) -> str:  # pragma: no cover - 호출되지 않음
        return f"{marker}:{start_url}"

    fake.explore_unknown_site = explore_unknown_site
    fake.explore_unknown_site._marker = marker  # type: ignore[attr-defined]
    return fake


def test_load_latest_imports_when_not_already_loaded(monkeypatch):
    """모듈이 sys.modules에 없으면 import_module로 새로 가져와야 한다."""
    monkeypatch.delitem(sys.modules, MODULE._SNIFFER_MODULE_NAME, raising=False)
    fake_module = _fake_sniffer_module("first-import")
    imported_names = []

    def fake_import_module(name):
        imported_names.append(name)
        return fake_module

    monkeypatch.setattr(importlib, "import_module", fake_import_module)

    func = MODULE._load_latest_explore_unknown_site()

    assert imported_names == [MODULE._SNIFFER_MODULE_NAME]
    assert func is fake_module.explore_unknown_site
    assert func._marker == "first-import"


def test_load_latest_reloads_when_already_loaded(monkeypatch):
    """이미 로드된 모듈이 있으면 reload로 최신 코드를 다시 실행해야 한다."""
    stale_module = _fake_sniffer_module("stale")
    monkeypatch.setitem(sys.modules, MODULE._SNIFFER_MODULE_NAME, stale_module)
    fresh_module = _fake_sniffer_module("reloaded")
    reloaded_targets = []

    def fake_reload(module):
        reloaded_targets.append(module)
        return fresh_module

    monkeypatch.setattr(importlib, "reload", fake_reload)

    func = MODULE._load_latest_explore_unknown_site()

    assert reloaded_targets == [stale_module]
    assert func is fresh_module.explore_unknown_site
    assert func._marker == "reloaded"

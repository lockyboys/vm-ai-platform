"""워커 내부 자가 복구 테스트(2026-10-25, P0).

목적: 사람이 없어도 (1) 수집 시작 전 점검이 실패하거나 (2) 수집 중 모든 시드가 실패하면
      워커(systemd 유닛, MCP 120초 제한 없음)가 스스로 재탐색하고 새 프로파일로 이어서 수집한다.
네트워크·브라우저 없이 가짜 함수로 판단 로직만 검증한다.
"""
from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def mod():
    spec = importlib.util.spec_from_file_location(
        "collector_worker_heal", ROOT / "FastAPI/LangGraph/Agent_Import_PFDs/public_document_catalog_collector.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


AUTO = {"autodiscover": {"start_urls": [{"url": "https://x.org/a"}], "document_keyword": "약관"}}


def test_healthy_profile_is_kept(mod):
    profile = {"name": "p", "v": 1, **AUTO}
    result, report = mod.ensure_healthy(profile, probe_fn=lambda p: {"ok": 1},
                                        heal_fn=lambda n: pytest.fail("must not heal"), load=lambda n: None)
    assert result is profile and report is None


def test_broken_profile_is_healed_and_reloaded(mod):
    def probe_fn(p):
        if p["v"] == 1:
            raise ValueError("list path not found")   # 사이트 구조 변경 재현
        return {"ok": 1}

    result, report = mod.ensure_healthy({"name": "p", "v": 1, **AUTO}, probe_fn=probe_fn,
                                        heal_fn=lambda n: {"result": "DISCOVERED_AND_VALID_SAVED"},
                                        load=lambda n: {"name": n, "v": 2, **AUTO})
    assert result["v"] == 2 and report["result"].startswith("DISCOVERED")
    assert "list path not found" in report["first_error"]


def test_profile_without_autodiscover_cannot_heal(mod):
    # 재탐색 입력이 없는 수동 프로파일은 추측하지 않고 원래 오류를 그대로 올린다.
    def probe_fn(p):
        raise ValueError("blocked")
    with pytest.raises(ValueError, match="blocked"):
        mod.ensure_healthy({"name": "p"}, probe_fn=probe_fn, heal_fn=lambda n: {}, load=lambda n: None)


def test_heal_failure_stops_worker(mod):
    def probe_fn(p):
        raise ValueError("blocked")
    with pytest.raises(RuntimeError, match="self_heal failed"):
        mod.ensure_healthy({"name": "p", **AUTO}, probe_fn=probe_fn,
                           heal_fn=lambda n: {"result": "FAILED"}, load=lambda n: None)


@pytest.mark.parametrize("state, healed, expected", [
    ({"seeds_total": 10, "seed_failures": 10}, False, True),    # 전부 실패 → 구조 변경으로 보고 재탐색
    ({"seeds_total": 10, "seed_failures": 3}, False, False),    # 일부 실패 → 일시 오류, 다음 실행에서 재시도
    ({"seeds_total": 10, "seed_failures": 10}, True, False),    # 이미 한 번 재탐색 → 무한 반복 금지
    ({"seeds_total": 0, "seed_failures": 0}, False, False),     # 시드 없음
])
def test_should_heal_after_catalog(mod, state, healed, expected):
    assert mod.should_heal_after_catalog(state, healed) is expected

"""수집기 systemd 작업이 키 파일(EnvironmentFile)을 받는지 테스트.

20261030 | 요청: LuckyBoys | 작성: Claude | "1번 설정 수정(dry-run → 테스트 → 적용) 승인"
재현: 2026-10-25 20:49, 2026-10-29 17:14 삼성화재 온보딩 수리가 모두
      "API key required for Gemini"로 실패 — systemd-run 작업에 EnvironmentFile이 없어 키가 전달되지 않았다.
기대: systemd_run_command에 프로젝트 공용 방식(multi_persona_agent_gemini.py 실행 예시)과 같은
      EnvironmentFile 두 개(/data/vm_project/.env, /etc/sps-harness/secrets.env)가 들어간다. 키 값은 읽지 않는다.
"""
from __future__ import annotations

import importlib.util
from pathlib import Path

import config

ROOT = Path(__file__).resolve().parents[2]
EXPECTED = [f"EnvironmentFile={config.BASE_DIR / '.env'}", "EnvironmentFile=/etc/sps-harness/secrets.env"]


def _pairs(command: list[str]) -> list[str]:
    """명령에서 '-p 값' 쌍의 값만 모은다."""
    return [command[i + 1] for i, part in enumerate(command[:-1]) if part == "-p"]


def test_systemd_run_command_has_both_environment_files():
    command = list(config.PUBLIC_DOCUMENT_COLLECTOR["systemd_run_command"])
    assert command[:3] == ["sudo", "-n", "systemd-run"]           # 기존 앞부분 유지(sudo -n: 비밀번호 묻지 않음)
    assert [p for p in _pairs(command) if p.startswith("EnvironmentFile=")] == EXPECTED


def test_onboard_unit_command_passes_environment_files(tmp_path, monkeypatch):
    spec = importlib.util.spec_from_file_location(
        "collector_env_t", ROOT / "FastAPI/LangGraph/Agent_Import_PFDs/public_document_catalog_collector.py")
    col = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(col)
    monkeypatch.setattr(col, "PROFILE_DIR", tmp_path / "profiles")
    (tmp_path / "profiles").mkdir()
    monkeypatch.setattr(col, "output_dir", lambda p: (tmp_path / p["name"]).mkdir(parents=True, exist_ok=True)
                        or tmp_path / p["name"])
    calls = []

    class Done:
        returncode, stdout, stderr = 0, "", ""

    request = col.parse_onboard({"profile": "env_check_terms", "company_name": "예시화재"})
    col.onboard_start(request, run=lambda cmd, **k: calls.append(cmd) or Done())
    assert [p for p in _pairs(calls[0]) if p.startswith("EnvironmentFile=")] == EXPECTED
    assert calls[0].index("--onboard") > max(i for i, part in enumerate(calls[0]) if part == "-p")

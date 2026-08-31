"""Regression coverage for the remaining legacy-web P0 security controls."""

from __future__ import annotations

from pathlib import Path

import pytest

from services.auth import auth_service


@pytest.fixture(autouse=True)
def configured_token_secret(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SPS_AUTH_JWT_SECRET_KEY", "test-only-secret-key")
    monkeypatch.setenv("SPS_AUTH_JWT_EXPIRE_SECONDS", "3600")
    monkeypatch.setenv("SPS_AUTH_REFRESH_TOKEN_EXPIRE_SECONDS", "86400")
    monkeypatch.setenv("SPS_ADMIN_EMAILS", "admin@example.test")


def _authenticated_headers() -> dict[str, str]:
    token = auth_service.create_token(
        "member-1",
        "member@example.test",
        "free",
    )["token"]
    return {"Authorization": f"Bearer {token}"}


def test_launcher_masks_database_configuration_values() -> None:
    project_root = Path(__file__).resolve().parents[2]
    launcher_source = (project_root / "launcher.py").read_text(encoding="utf-8")

    assert 'print("DB CONFIG =", MYSQL_CONFIG)' not in launcher_source
    assert '{key: "***" for key in MYSQL_CONFIG}' in launcher_source


def test_authenticated_web_clients_cannot_execute_admin_operations() -> None:
    from web.app import app

    client = app.test_client()
    headers = _authenticated_headers()

    for path in (
        "/api/admin/deploy/upload",
        "/api/admin/deploy/run",
        "/api/admin/deploy/log",
        "/api/admin/restart",
    ):
        response = client.post(path, headers=headers)
        assert response.status_code == 403


def test_ai_job_endpoints_require_authenticated_owner_scoping() -> None:
    project_root = Path(__file__).resolve().parents[2]
    controller_source = (
        project_root / "src" / "AI" / "controllers" / "ai_job_controller.py"
    ).read_text(encoding="utf-8")
    job_source = (
        project_root / "src" / "AI" / "repositories" / "ai_job_repository.py"
    ).read_text(encoding="utf-8")
    log_source = (
        project_root / "src" / "AI" / "repositories" / "ai_job_log_repository.py"
    ).read_text(encoding="utf-8")

    assert 'g.current_user["user_id"]' in controller_source
    assert "WHERE j.created_by = %s" in job_source
    assert "AND job.created_by = %s" in log_source

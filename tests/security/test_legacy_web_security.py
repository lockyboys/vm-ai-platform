"""Regression tests for the legacy web P0 security boundary."""

from __future__ import annotations

from pathlib import Path

import pytest

from services.auth import auth_service


@pytest.fixture(autouse=True)
def configured_token_secret(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(auth_service, "SECRET_KEY", "test-only-secret-key")
    monkeypatch.setenv("SPS_ADMIN_EMAILS", "admin@example.test")


def test_signed_token_cannot_be_forged_or_escalated() -> None:
    issued = auth_service.create_token("member-1", "member@example.test", "free")

    verified = auth_service.verify_token(issued["token"])
    assert verified["valid"] is True
    assert verified["user_id"] == "member-1"
    assert verified["plan"] == "free"
    assert verified["is_admin"] is False

    forged = issued["token"].rsplit(".", 1)[0] + ".forged"
    assert auth_service.verify_token(forged) == {"valid": False}
    assert auth_service.verify_token("any-arbitrary-string") == {"valid": False}


def test_password_hash_is_salted_and_verifiable() -> None:
    password_hash = auth_service.hash_password("correct-horse-battery-staple")

    assert password_hash.startswith("pbkdf2_sha256$")
    assert auth_service.verify_password("correct-horse-battery-staple", password_hash)
    assert not auth_service.verify_password("wrong-password", password_hash)


def test_legacy_web_api_requires_authentication_and_disables_admin_execution() -> None:
    from web.app import app

    client = app.test_client()
    assert client.post("/api/upload").status_code == 401

    token = auth_service.create_token("member-1", "member@example.test", "free")["token"]
    response = client.get(
        "/api/admin/deploy/log",
        headers={"Authorization": f"Bearer {token}"},
    )
    assert response.status_code == 403


def test_ownership_and_path_guards_are_present() -> None:
    project_root = Path(__file__).resolve().parents[2]
    app_source = (project_root / "web" / "app.py").read_text(encoding="utf-8")
    work_source = (project_root / "work" / "work_repository.py").read_text(encoding="utf-8")
    job_source = (project_root / "src" / "AI" / "repositories" / "ai_job_repository.py").read_text(encoding="utf-8")
    log_source = (project_root / "src" / "AI" / "repositories" / "ai_job_log_repository.py").read_text(encoding="utf-8")

    assert "candidate.relative_to(_current_upload_root())" in app_source
    assert "user_id = str(g.current_user[\"user_id\"])" in app_source
    assert "AND deleted_dt IS NULL" in work_source
    assert "WHERE j.created_by = %s" in job_source
    assert "AND job.created_by = %s" in log_source

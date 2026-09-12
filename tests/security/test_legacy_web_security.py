"""Regression tests for the legacy web P0 security boundary."""

from __future__ import annotations

from pathlib import Path

import pytest

from common.auth import CommonAuth
from services.auth import auth_service


@pytest.fixture(autouse=True)
def configured_token_secret(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SPS_AUTH_JWT_SECRET_KEY", "test-only-secret-key")
    monkeypatch.setenv("SPS_AUTH_JWT_EXPIRE_SECONDS", "3600")
    monkeypatch.setenv("SPS_AUTH_REFRESH_TOKEN_EXPIRE_SECONDS", "86400")
    monkeypatch.setenv("SPS_ADMIN_EMAILS", "admin@example.test")


def test_signed_token_cannot_be_forged_or_escalated() -> None:
    issued = auth_service.create_token("member-1", "member@example.test", "free")

    verified = auth_service.verify_token(issued["token"])
    assert verified["valid"] is True
    assert verified["user_id"] == "member-1"
    assert verified["plan"] == "free"
    assert verified["is_admin"] is False

    forged = issued["token"].rsplit(".", 1)[0] + ".forged"
    assert auth_service.verify_token(forged)["valid"] is False
    assert auth_service.verify_token("any-arbitrary-string")["valid"] is False


def test_password_hash_is_salted_and_verifiable() -> None:
    password_hash = auth_service.hash_password("correct-horse-battery-staple")

    assert password_hash.startswith("pbkdf2_sha256$600000$")
    assert auth_service.verify_password("correct-horse-battery-staple", password_hash)
    assert not auth_service.verify_password("wrong-password", password_hash)


def test_authentication_secret_has_no_runtime_default(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("SPS_AUTH_JWT_SECRET_KEY", raising=False)
    with pytest.raises(RuntimeError, match="SPS_AUTH_JWT_SECRET_KEY environment variable is required"):
        CommonAuth()


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
    for path in (
        "/api/files",
        "/api/download/guessed-report.pdf",
        "/api/history",
        "/api/history/all",
        "/api/history/model",
        "/api/stats",
    ):
        assert client.get(path, headers={"Authorization": f"Bearer {token}"}).status_code == 404


def test_work_session_api_uses_authenticated_owner(monkeypatch: pytest.MonkeyPatch) -> None:
    import importlib

    legacy_web = importlib.import_module("web.app")

    class FakeWorkRepository:
        def list_owned_sessions(self, user_id: str):
            assert user_id == "member-1"
            return [{"work_session_id": "session-1", "work_name": "owned work"}]

        def get_owned_session_detail(self, work_session_id: str, user_id: str):
            assert user_id == "member-1"
            return None if work_session_id != "session-1" else {"work_session_id": work_session_id}

        def list_owned_session_assets(self, work_session_id: str, user_id: str):
            assert user_id == "member-1"
            return None if work_session_id != "session-1" else [{"work_asset_id": "asset-1"}]

    monkeypatch.setattr(legacy_web, "work_repository", FakeWorkRepository())
    token = auth_service.create_token("member-1", "member@example.test", "free")["token"]
    headers = {"Authorization": f"Bearer {token}"}
    client = legacy_web.app.test_client()

    assert client.get("/api/work-sessions", headers=headers).get_json()["work_sessions"][0]["work_session_id"] == "session-1"
    assert client.get("/api/work-sessions/session-1", headers=headers).status_code == 200
    assert client.get("/api/work-sessions/session-1/assets", headers=headers).status_code == 200
    assert client.get("/api/work-sessions/not-owned", headers=headers).status_code == 404


def test_ownership_and_path_guards_are_present() -> None:
    project_root = Path(__file__).resolve().parents[2]
    app_source = (project_root / "web" / "app.py").read_text(encoding="utf-8")
    work_source = (project_root / "work" / "work_repository.py").read_text(encoding="utf-8")
    job_source = (project_root / "src" / "AI" / "repositories" / "ai_job_repository.py").read_text(encoding="utf-8")
    log_source = (project_root / "src" / "AI" / "repositories" / "ai_job_log_repository.py").read_text(encoding="utf-8")

    assert "candidate.relative_to(_current_upload_root())" in app_source
    assert "user_id = str(g.current_user[\"user_id\"])" in app_source
    assert "save_upload_history(str(g.current_user[\"user_id\"])," in app_source
    assert "AND deleted_dt IS NULL" in work_source
    assert "WHERE j.created_by = %s" in job_source
    assert "AND job.created_by = %s" in log_source


def test_analysis_path_is_limited_to_the_authenticated_users_upload_root(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import importlib

    legacy_web = importlib.import_module("web.app")
    monkeypatch.setattr(legacy_web, "UPLOAD_PATH", str(tmp_path))
    owned_file = tmp_path / "member-1" / "owned.csv"
    owned_file.parent.mkdir()
    owned_file.write_text("value\n1\n", encoding="utf-8")
    outside_file = tmp_path / "outside.csv"
    outside_file.write_text("value\n2\n", encoding="utf-8")

    with legacy_web.app.test_request_context():
        legacy_web.g.current_user = {"user_id": "member-1"}
        assert legacy_web._resolve_current_user_upload_path(str(owned_file)) == owned_file.resolve()
        assert legacy_web._resolve_current_user_upload_path(str(outside_file)) is None

def test_deleted_work_session_is_excluded_from_owner_verification() -> None:
    from work.work_repository import WorkRepository

    class FakeDatabase:
        def __init__(self) -> None:
            self.query = ""
            self.params = None

        def fetch_one(self, query, params):
            self.query = query
            self.params = params
            return None

        def close(self) -> None:
            return None

    database = FakeDatabase()
    repository = WorkRepository(database_factory=lambda **_kwargs: database)

    assert repository.verify_owner("deleted-session", "member-1") is False
    assert database.params == ("deleted-session", "member-1")
    assert "AND deleted_dt IS NULL" in database.query

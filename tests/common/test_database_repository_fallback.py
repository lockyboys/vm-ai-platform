# =============================================================================
# File Name   : tests/common/test_database_repository_fallback.py
# Purpose     : CommonDatabase Repository fallback regression tests
# =============================================================================
# CHANGE HISTORY
# =============================================================================
# 20260830 | OpenAI | STORY role Repository environment fallback tests added
# =============================================================================

from __future__ import annotations

import pytest

from common.database import CommonDatabase


_ROLE_KEYS = (
    "STORY_PLATFORM_MARIADB_HOST",
    "STORY_PLATFORM_MARIADB_PORT",
    "STORY_PLATFORM_MARIADB_USER",
    "STORY_PLATFORM_MARIADB_PASSWORD",
    "STORY_PLATFORM_MARIADB_DATABASE",
)


class _RepositoryDatabaseManager:
    def get_database_name(self, database_role: str) -> str:
        assert database_role in {"STORY", "STORY_PLATFORM"}
        return "te_story_platform"


def _set_repository_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("common.database.DatabaseManager", _RepositoryDatabaseManager)
    for key in _ROLE_KEYS:
        monkeypatch.setenv(key, "")
    monkeypatch.setenv("SPS_REPOSITORY_HOST", "repository-host")
    monkeypatch.setenv("SPS_REPOSITORY_PORT", "3307")
    monkeypatch.setenv("SPS_REPOSITORY_USER", "repository-user")
    monkeypatch.setenv("SPS_REPOSITORY_PASSWORD", "repository-password")
    monkeypatch.setenv("SPS_REPOSITORY_BOOTSTRAP_DATABASE", "te_story_platform")


def test_story_role_uses_repository_environment_fallback(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _set_repository_environment(monkeypatch)

    database = CommonDatabase(
        database_role="STORY",
        connect_mariadb=False,
    )

    assert database._load_mariadb_config() == {
        "host": "repository-host",
        "port": "3307",
        "user": "repository-user",
        "password": "repository-password",
        "database": "te_story_platform",
    }


def test_story_role_prefers_role_specific_environment(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _set_repository_environment(monkeypatch)
    monkeypatch.setenv("STORY_PLATFORM_MARIADB_USER", "story-user")
    monkeypatch.setenv("STORY_PLATFORM_MARIADB_PASSWORD", "story-password")
    monkeypatch.setenv("STORY_PLATFORM_MARIADB_DATABASE", "story-database")

    database = CommonDatabase(
        database_role="STORY_PLATFORM",
        connect_mariadb=False,
    )

    config = database._load_mariadb_config()
    assert config["user"] == "story-user"
    assert config["password"] == "story-password"
    assert config["database"] == "story-database"

# =============================================================================
# File Name   : tests/harness/mcp/test_server_tool_catalog.py
# Purpose     : SPS Harness FastMCP runtime tool catalog verification
# =============================================================================
# CHANGE HISTORY
# =============================================================================
# 20260830 | OpenAI | identifier_generate 직접 서비스 노출 검증을 추가했음
# 20260831 | CODEX  | mongodb_update_document 직접 서비스 노출 검증을 추가했음
# =============================================================================

from __future__ import annotations

import asyncio
import subprocess
from types import SimpleNamespace

import httpx
import pytest

from harness.mcp.tools import git_tools
from harness.mcp.sps_harness_server import OAUTH_SETTINGS, mcp


def test_git_history_tools_are_exposed_and_queries_are_bounded(monkeypatch, tmp_path) -> None:
    # Verify tool registration and argument bounds without invoking real Git.
    names = {tool.name for tool in mcp._tool_manager.list_tools()}
    assert {"git_log", "git_blame"}.issubset(names)
    target = tmp_path / "sample.py"
    target.write_text("pass\n", encoding="utf-8")
    monkeypatch.setattr(git_tools, "PROJECT_ROOT", tmp_path)
    seen = {}

    def fake_run(command):
        seen["command"] = command
        return SimpleNamespace(returncode=0, stdout="abc\tAuthor\tdate\tsubject\n", stderr="")

    monkeypatch.setattr(git_tools, "_run_git", fake_run)
    result = git_tools.git_log("sample.py", limit=999)
    assert result["limit"] == git_tools.MAX_HISTORY_COMMITS
    assert seen["command"][-2:] == ["--", "sample.py"]


def test_git_query_timeout_is_reported(monkeypatch) -> None:
    # Verify a stuck subprocess becomes a bounded, caller-visible failure.
    def timeout(*args, **kwargs):
        raise subprocess.TimeoutExpired(args[0], kwargs["timeout"])

    monkeypatch.setattr(git_tools.subprocess, "run", timeout)
    with pytest.raises(TimeoutError, match="exceeded"):
        git_tools._run_git(["git", "log"])


def test_git_blame_rejects_oversized_range_without_running_git(monkeypatch, tmp_path) -> None:
    # Verify invalid blame ranges fail before any Git process can start.
    target = tmp_path / "sample.py"
    target.write_text("pass\n", encoding="utf-8")
    monkeypatch.setattr(git_tools, "PROJECT_ROOT", tmp_path)
    monkeypatch.setattr(git_tools, "_run_git", lambda command: pytest.fail("Git must not run"))
    with pytest.raises(ValueError, match="cannot exceed"):
        git_tools.git_blame("sample.py", 1, git_tools.MAX_BLAME_LINES + 1)


def test_identifier_generate_is_exposed_in_fastmcp_catalog() -> None:
    tool_manager = mcp._tool_manager
    tools = tool_manager.list_tools()
    tool_names = {tool.name for tool in tools}

    assert "identifier_generate" in tool_names


def test_mongodb_update_document_is_exposed_in_fastmcp_catalog() -> None:
    tool_manager = mcp._tool_manager
    tools = tool_manager.list_tools()
    tool_names = {tool.name for tool in tools}

    assert "mongodb_update_document" in tool_names


def test_mongodb_delete_document_is_exposed_in_fastmcp_catalog() -> None:
    tool_names = {tool.name for tool in mcp._tool_manager.list_tools()}

    assert "mongodb_delete_document" in tool_names


def test_openid_discovery_alias_exposes_oauth_metadata() -> None:
    async def scenario() -> None:
        app = mcp.streamable_http_app()
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(
            transport=transport,
            base_url=OAUTH_SETTINGS.issuer_url,
        ) as client:
            response = await client.get("/.well-known/openid-configuration")

        assert response.status_code == 200
        metadata = response.json()
        assert metadata["issuer"] == f"{OAUTH_SETTINGS.issuer_url}/"
        assert metadata["authorization_endpoint"] == f"{OAUTH_SETTINGS.issuer_url}/authorize"
        assert metadata["token_endpoint"] == f"{OAUTH_SETTINGS.issuer_url}/token"
        assert metadata["code_challenge_methods_supported"] == ["S256"]

    asyncio.run(scenario())


def test_backup_tools_are_exposed_in_fastmcp_catalog() -> None:
    tool_names = {tool.name for tool in mcp._tool_manager.list_tools()}

    assert {
        "database_backup_create",
        "database_backup_verify",
        "mongodb_backup_collection",
        "mongodb_backup_verify",
        "mongodb_backup_delete",
        "mongodb_delete_backup",
    }.issubset(tool_names)


def test_mariadb_ddl_execute_is_exposed_in_fastmcp_catalog() -> None:
    tool_names = {tool.name for tool in mcp._tool_manager.list_tools()}

    assert "mariadb_ddl_execute" in tool_names


def test_codex_apps_run_python_source_has_requested_catalog_name() -> None:
    # 서버가 함수명을 MCP 카탈로그에 정확한 이름으로 공개하는지 확인한다.
    catalog = {tool.name: tool for tool in mcp._tool_manager.list_tools()}

    assert "mcp_codex_apps_run_python_source" in catalog
    assert "Plan or execute one approved project-relative Python source file." in catalog[
        "mcp_codex_apps_run_python_source"
    ].description

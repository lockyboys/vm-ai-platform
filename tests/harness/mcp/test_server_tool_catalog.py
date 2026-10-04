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

import httpx

from harness.mcp.sps_harness_server import OAUTH_SETTINGS, mcp


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

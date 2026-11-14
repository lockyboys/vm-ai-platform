"""PARTNER 워커의 실제 SPS MCP 브리지 격리 검증."""
import asyncio
from types import SimpleNamespace

import haness.mcp.agents.source_partner_agent as agent


class FakeMCPClient:
    def __init__(self, servers):
        self.servers = servers

    async def get_tools(self):
        return [
            SimpleNamespace(name="source_read"),
            SimpleNamespace(name="source_patch"),
            SimpleNamespace(name="git_diff"),
        ]


def test_tools_list_loads_and_blocks_writes_without_approval(monkeypatch):
    monkeypatch.setenv("SPS_MCP_URL", "http://mcp.test/mcp")
    monkeypatch.setenv("SPS_MCP_BEARER_TOKEN", "test-token")
    monkeypatch.setattr(agent, "MultiServerMCPClient", FakeMCPClient)

    tools = asyncio.run(agent._load_sps_mcp_tools(source_write_confirmed=False))

    assert [item.name for item in tools] == ["source_read", "git_diff"]


def test_tools_list_exposes_write_tools_after_approval(monkeypatch):
    monkeypatch.setenv("SPS_MCP_URL", "http://mcp.test/mcp")
    monkeypatch.setenv("SPS_MCP_BEARER_TOKEN", "test-token")
    monkeypatch.setattr(agent, "MultiServerMCPClient", FakeMCPClient)

    tools = asyncio.run(agent._load_sps_mcp_tools(source_write_confirmed=True))

    assert [item.name for item in tools] == ["source_read", "source_patch", "git_diff"]

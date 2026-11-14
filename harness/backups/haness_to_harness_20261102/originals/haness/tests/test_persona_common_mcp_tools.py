from langchain_core.tools import tool

from haness.mcp.agents.source_partner_agent import _MCP_WRITE_TOOLS
from haness.mcp.agents.persona_source_runtime import Session


@tool
def mcp_read_probe() -> str:
    """Fake read-only SPS MCP tool."""
    return "read"


@tool("source_patch")
def source_patch_probe() -> str:
    """Fake SPS MCP write tool."""
    return "write"


def test_all_personas_receive_common_mcp_read_tools_without_write_approval(tmp_path):
    session = Session(
        "haness/apps/tetris_combined_chromium_20261026",
        tmp_path,
        approved=False,
        mcp_tools=[mcp_read_probe, source_patch_probe],
    )

    for role in ("ORCHESTRATOR", "ARCHITECT", "TESTER", "REVIEWER", "TUTOR"):
        names = {tool.name for tool in session.tools(role)}
        assert "mcp_read_probe" in names
        assert not names.intersection(_MCP_WRITE_TOOLS)


def test_only_approved_partner_receives_common_mcp_write_tools(tmp_path):
    session = Session(
        "haness/apps/tetris_combined_chromium_20261025",
        tmp_path,
        approved=True,
        mcp_tools=[mcp_read_probe, source_patch_probe],
    )

    assert "mcp_read_probe" in {tool.name for tool in session.tools("ORCHESTRATOR")}
    assert not {tool.name for tool in session.tools("TESTER")}.intersection(_MCP_WRITE_TOOLS)
    assert "source_patch" in {tool.name for tool in session.tools("PARTNER")}

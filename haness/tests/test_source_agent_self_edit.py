"""Regression tests for the shared SPS source-agent path and gateway fallback guards."""
import asyncio
import json
from types import SimpleNamespace

import pytest
from langchain_core.messages import AIMessage

import haness.mcp.agents.source_partner_agent as agent


def test_shared_source_path_guard_rejects_escape_symlink_and_wrong_allowlist(tmp_path):
    """The common guard accepts one exact source path and rejects traversal and links."""
    from common.common_function import resolve_project_source_file

    relative = "FastAPI/LangGraph/Agent_Import_PFDs/public_document_catalog_collector.py"
    source = tmp_path / relative
    source.parent.mkdir(parents=True)
    source.write_text("VALUE = 1\n", encoding="utf-8")
    assert resolve_project_source_file(
        tmp_path, relative, allowed_paths=[relative], allowed_suffixes={".py"}) == (relative, source)
    for invalid in ("../outside.py", "/etc/passwd", "other.py"):
        with pytest.raises(ValueError):
            resolve_project_source_file(tmp_path, invalid, allowed_paths=[relative])
    (tmp_path / "link.py").symlink_to(source)
    with pytest.raises(ValueError, match="symlink"):
        resolve_project_source_file(tmp_path, "link.py")


def test_partner_continues_real_tool_loop_when_gateway_returns_401(monkeypatch):
    """The PARTNER LLM still calls a local ToolNode tool after a nested MCP 401."""
    async def rejected_bridge(**_kwargs):
        raise ExceptionGroup("MCP bridge", [PermissionError("401 Unauthorized")])

    monkeypatch.setattr(agent, "_original_mcp_tools_loader", rejected_bridge)
    monkeypatch.setattr(agent, "git_status", lambda: {"state": "test"})

    class Model:
        def __init__(self):
            self.calls = 0

        def bind_tools(self, _tools):
            return self

        async def ainvoke(self, _messages):
            self.calls += 1
            if self.calls == 1:
                return AIMessage(content="", tool_calls=[
                    {"name": "get_git_status", "args": {}, "id": "status-check"}])
            return AIMessage(content="local tool result received")

    model = Model()
    monkeypatch.setattr(agent, "_build_model", lambda: model)
    result = asyncio.run(agent.run_source_partner_agent(
        "Read repository status and report it.",
        dry_run=True,
        source_write_confirmed=False,
    ))
    assert result["success"]
    assert result["mcp_tools_bridge_error"] == "ExceptionGroup"
    assert result["mcp_tools_loaded"] == []
    assert "get_git_status" in result["called_tool_names"]
    assert model.calls == 2


def test_scoped_source_agent_hides_direct_mcp_writers(monkeypatch):
    """A scoped source task exposes writes only through the change-set allowlist."""
    observed = []

    async def loader(*, source_write_confirmed):
        observed.append(source_write_confirmed)
        return [SimpleNamespace(name="source_patch")]

    class Model:
        def bind_tools(self, _tools):
            return self

        async def ainvoke(self, _messages):
            return AIMessage(content="scoped task inspected")

    monkeypatch.setattr(agent, "_original_mcp_tools_loader", loader)
    monkeypatch.setattr(agent, "_build_model", Model)
    result = asyncio.run(agent.run_source_partner_agent(
        "Inspect a scoped source task.",
        dry_run=True,
        source_write_confirmed=True,
        allowed_source_paths=[
            "FastAPI/LangGraph/Agent_Import_PFDs/public_document_catalog_collector.py",
        ],
    ))
    assert observed == [False]
    assert result["mcp_tools_loaded"] == []
    assert result["success"]


def test_source_agent_boundary_validates_and_forwards_allowed_paths(monkeypatch):
    """The orchestrator validates canonical relative paths before handing them to PARTNER."""
    from haness.mcp.tools import orchestrator_tools

    observed = {}

    async def fake_partner(task, **kwargs):
        observed.update(task=task, **kwargs)
        return {"success": True}

    monkeypatch.setattr(orchestrator_tools, "_run_source_partner_agent", fake_partner)
    payload = {
        "mode": "source_agent",
        "task": "Inspect the public PDF collector.",
        "source_write_confirmed": True,
        "allowed_source_paths": [
            "common/common_function.py",
            "FastAPI/LangGraph/Agent_Import_PFDs/public_document_catalog_collector.py",
        ],
    }
    result = asyncio.run(orchestrator_tools.run_sps_orchestrator(
        json.dumps(payload), dry_run=True))
    assert result["success"]
    assert observed["allowed_source_paths"] == payload["allowed_source_paths"]

    payload["allowed_source_paths"] = ["../outside.py"]
    with pytest.raises(ValueError, match="canonical project-relative"):
        asyncio.run(orchestrator_tools.run_sps_orchestrator(
            json.dumps(payload), dry_run=True))

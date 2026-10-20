"""Exercise MCP orchestration boundaries without a live provider or crawler."""
import asyncio
import io
import json
import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock
import pytest

from haness.mcp.tools import orchestrator_tools as module

@pytest.fixture
def process_context(tmp_path, monkeypatch):
    # Separate reports and disable process creation in unit tests.
    monkeypatch.setattr(module, "PROJECT_ROOT", tmp_path)
    start = AsyncMock()
    monkeypatch.setattr(module.asyncio, "create_subprocess_exec", start)
    return start

def test_dry_run_does_not_launch_worker(process_context):
    result = asyncio.run(module.run_sps_orchestrator("어떤 도구가 있니?"))
    assert not result["executed"]
    assert result["command"][:3] == ["sudo", "-n", "systemd-run"]
    process_context.assert_not_awaited()

@pytest.mark.parametrize("query", ["", "   ", "x" * 20001, None])
def test_invalid_query(process_context, query):
    with pytest.raises(ValueError):
        asyncio.run(module.run_sps_orchestrator(query, False))
    process_context.assert_not_awaited()

def test_worker_receives_task_on_stdin(process_context):
    process = SimpleNamespace(returncode=0, communicate=AsyncMock(return_value=(b'{"success": true}', b"")))
    process_context.return_value = process
    result = asyncio.run(module.run_sps_orchestrator("private task", False))
    assert result["success"] and result["executed"]
    assert "private task" not in process_context.call_args.args
    assert json.loads(process.communicate.call_args.args[0]) == {"query": "private task"}
    assert (module.PROJECT_ROOT / result["report_path"]).exists()

def test_failed_worker_is_not_success(process_context):
    process_context.return_value = SimpleNamespace(returncode=1, communicate=AsyncMock(return_value=(b"", b"failed")))
    assert not asyncio.run(module.run_sps_orchestrator("task", False))["success"]

def test_worker_reuses_existing_api_function(monkeypatch, capsys):
    endpoint = AsyncMock(return_value={"success": True, "response": "existing graph"})
    # Import isolation verifies delegation without constructing any actual Gemini model.
    monkeypatch.setitem(sys.modules, "FastAPI.LangGraph.sps_main_orchestrator",
                        SimpleNamespace(ChatRequest=lambda **kw: kw, api_chat_orchestrator=endpoint))
    monkeypatch.setattr(sys, "stdin", io.StringIO('{"query": "task"}'))
    asyncio.run(module._worker())
    endpoint.assert_awaited_once_with({"query": "task"})
    assert json.loads(capsys.readouterr().out)["response"] == "existing graph"

def test_registration_and_original_source_compile():
    root = Path("/data/vm_project")
    server = (root / "harness/mcp/sps_harness_server.py").read_text()
    assert "mcp.tool()(run_sps_orchestrator)" in server
    compile((root / "FastAPI/LangGraph/sps_main_orchestrator.py").read_text(), "<main>", "exec")

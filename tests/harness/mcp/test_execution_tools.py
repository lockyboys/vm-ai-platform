from __future__ import annotations

import sys

import pytest

from harness.mcp.tools import execution_tools


def test_mcp_codex_apps_run_python_source_dry_run_does_not_start_process(monkeypatch):
    called = False

    def fail_run(*args, **kwargs):
        nonlocal called
        called = True
        raise AssertionError("subprocess must not run during dry-run")

    monkeypatch.setattr(execution_tools.subprocess, "run", fail_run)
    result = execution_tools.mcp_codex_apps_run_python_source(
        "FastAPI/LangGraph/Agent_Import_RAGs/LangGraph_email_RAG_Agent.py"
    )
    assert result["dry_run"] is True
    assert result["executed"] is False
    assert called is False
    assert result["llm_call_allowed"] is False


def test_mcp_codex_apps_run_python_source_rejects_outside_allowlist():
    with pytest.raises(ValueError):
        execution_tools.mcp_codex_apps_run_python_source("harness/mcp/sps_harness_server.py")


def test_mcp_codex_apps_run_python_source_requires_explicit_approval(monkeypatch):
    called = False

    def fail_run(*args, **kwargs):
        nonlocal called
        called = True
        raise AssertionError("subprocess must not run without approval")

    monkeypatch.setattr(execution_tools.subprocess, "run", fail_run)
    result = execution_tools.mcp_codex_apps_run_python_source(
        "FastAPI/LangGraph/Agent_Import_RAGs/LangGraph_email_RAG_Agent.py",
        dry_run=False,
    )
    assert result["executed"] is False
    assert result["approval_required"] is True
    assert result["llm_call_allowed"] is False
    assert called is False


def test_mcp_codex_apps_run_python_source_executes_with_explicit_false_dry_run(monkeypatch):
    class Completed:
        returncode = 0
        stdout = "ok"
        stderr = ""

    captured = {}

    def fake_run(*args, **kwargs):
        captured["args"] = args
        captured["kwargs"] = kwargs
        return Completed()

    monkeypatch.setattr(execution_tools.subprocess, "run", fake_run)
    result = execution_tools.mcp_codex_apps_run_python_source(
        "FastAPI/LangGraph/Agent_Import_RAGs/LangGraph_email_RAG_Agent.py",
        dry_run=False,
        timeout_seconds=150,
        execute_confirmed=True,
    )
    assert result["executed"] is True
    assert result["llm_call_allowed"] is True
    assert result["returncode"] == 0
    assert captured["kwargs"]["timeout"] == 120
    assert captured["args"][0] == [sys.executable, "/data/vm_project/FastAPI/LangGraph/Agent_Import_RAGs/LangGraph_email_RAG_Agent.py"]

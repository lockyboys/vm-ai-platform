"""Regression tests for durable reviews with separate MCP and worker lifetimes."""
import asyncio
import json
from importlib import import_module
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock
import pytest

@pytest.fixture
def context(tmp_path, monkeypatch):
    module = import_module("haness.mcp.tools.multi_persona_tools")
    source = tmp_path / "sample.py"
    source.write_text("print('sample')\n", encoding="utf-8")
    runner = tmp_path / "FastAPI/LangGraph/multi_persona/multi_persona_agent_gemini.py"
    runner.parent.mkdir(parents=True)
    runner.write_text("# existing CLI\n", encoding="utf-8")
    monkeypatch.setattr(module, "PROJECT_ROOT", tmp_path)
    monkeypatch.setattr(module, "REVIEW_SOURCE", runner)
    monkeypatch.setattr(module.project_config, "MULTI_PERSONA_REVIEW_TIMEOUT_SECONDS", 300)
    monkeypatch.setattr(module.project_config, "MULTI_PERSONA_REVIEW_OUTPUT_CHARS", 12000)
    start = AsyncMock(return_value=SimpleNamespace(
        returncode=0, communicate=AsyncMock(return_value=(b"", b""))))
    monkeypatch.setattr(module.asyncio, "create_subprocess_exec", start)
    return module, source, start

def test_dry_run_never_starts_worker(context):
    module, source, start = context
    plan = asyncio.run(module.review_python_source(str(source)))
    assert plan["timeout_seconds"] == 300 and not plan["executed"]
    assert "--wait" not in plan["command"] and "--pipe" not in plan["command"]
    assert plan["review_command"][-2:] == ["--source-path", str(source)]
    assert not (module.PROJECT_ROOT / "harness/memory/source_reviews").exists()
    start.assert_not_awaited()

@pytest.mark.parametrize("value", ["", "../escape.py", "missing.py", "bad.txt"])
def test_invalid_source_rejected(context, value):
    module, source, start = context
    with pytest.raises((ValueError, FileNotFoundError)):
        asyncio.run(module.review_python_source(value))
    start.assert_not_awaited()

def test_symlink_escape_rejected(context, tmp_path):
    module, source, start = context
    outside = tmp_path.parent / (tmp_path.name + "_outside.py")
    outside.write_text("# outside\n")
    (tmp_path / "linked.py").symlink_to(outside)
    with pytest.raises(ValueError):
        asyncio.run(module.review_python_source("linked.py"))

def test_error_log_cannot_overwrite_source(context):
    module, source, start = context
    with pytest.raises(ValueError):
        asyncio.run(module.review_python_source(str(source), error_path=str(source)))

@pytest.mark.parametrize("limit", [0, 301])
def test_invalid_worker_timeout_rejected(context, monkeypatch, limit):
    module, source, start = context
    monkeypatch.setattr(module.project_config, "MULTI_PERSONA_REVIEW_TIMEOUT_SECONDS", limit)
    with pytest.raises(ValueError):
        asyncio.run(module.review_python_source(str(source)))
    start.assert_not_awaited()

def test_start_returns_job_without_waiting_for_review(context):
    module, source, start = context
    result = asyncio.run(module.review_python_source(str(source), dry_run=False))
    assert result["state"] == "running" and result["executed"]
    assert result["success"] is None and result["timeout_seconds"] == 300
    args = start.call_args.args
    assert args[:3] == ("sudo", "-n", "systemd-run")
    assert "--wait" not in args and "--pipe" not in args
    assert "User=jeaje" in args and "RuntimeMaxSec=310" in args
    assert "EnvironmentFile=" + str(module.PROJECT_ROOT / ".env") in args
    assert "EnvironmentFile=/etc/sps-harness/secrets.env" in args

def test_status_returns_running_without_starting_second_review(context, monkeypatch):
    module, source, start = context
    result = asyncio.run(module.review_python_source(str(source), dry_run=False))
    start.reset_mock()
    start.return_value = SimpleNamespace(returncode=0, communicate=AsyncMock(
        return_value=(b"LoadState=loaded\nActiveState=active\nResult=success\n", b"")))
    status = asyncio.run(module.review_python_source(str(source), job_id=result["job_id"]))
    assert status["state"] == "running" and status["success"] is None
    assert start.call_args.args[:2] == ("systemctl", "show")

def test_invalid_job_id_rejected(context):
    module, source, start = context
    with pytest.raises(ValueError):
        asyncio.run(module.review_python_source(str(source), job_id="../escape"))

def test_failed_launch_is_not_success(context):
    module, source, start = context
    start.return_value = SimpleNamespace(returncode=1, communicate=AsyncMock(
        return_value=(b"", b"launch failed")))
    result = asyncio.run(module.review_python_source(str(source), dry_run=False))
    assert result["state"] == "failed" and result["success"] is False

def test_worker_result_survives_a_new_status_call(context, monkeypatch):
    module, source, start = context
    original = source.read_bytes()
    job = asyncio.run(module.review_python_source(str(source), dry_run=False))
    output = "[최종 검증된 답변]:\nfull review\n"
    run = lambda *a, **kw: SimpleNamespace(returncode=0, stdout=output.encode(), stderr=b"")
    monkeypatch.setattr(module.subprocess, "run", run)
    module._run_review_job(job["job_id"])
    start.reset_mock()
    result = asyncio.run(module.review_python_source(str(source), job_id=job["job_id"]))
    assert result["state"] == "completed" and result["success"]
    assert result["model_verified"] and result["source_unchanged"]
    assert result["tests_executed"] is False and source.read_bytes() == original
    assert (module.PROJECT_ROOT / result["report_path"]).read_text() == output
    start.assert_not_awaited()

def test_worker_timeout_preserves_partial_output(context, monkeypatch):
    module, source, start = context
    job = asyncio.run(module.review_python_source(str(source), dry_run=False))
    calls = []
    def run(*args, **kwargs):
        calls.append(kwargs)
        raise module.subprocess.TimeoutExpired(args[0], 300, output=b"partial review", stderr=b"")
    monkeypatch.setattr(module.subprocess, "run", run)
    module._run_review_job(job["job_id"])
    result = asyncio.run(module.review_python_source(str(source), job_id=job["job_id"]))
    assert calls[0]["timeout"] == 300
    assert result["state"] == "timed_out" and result["timed_out"]
    assert result["output"] == "partial review" and not result["success"]

def test_status_rejects_different_source(context):
    module, source, start = context
    job = asyncio.run(module.review_python_source(str(source), dry_run=False))
    other = source.with_name("other.py")
    other.write_text("# other\n")
    with pytest.raises(ValueError):
        asyncio.run(module.review_python_source(str(other), job_id=job["job_id"]))

def test_missing_worker_is_not_reported_as_running(context):
    module, source, start = context
    job = asyncio.run(module.review_python_source(str(source), dry_run=False))
    start.return_value = SimpleNamespace(returncode=0, communicate=AsyncMock(
        return_value=(b"LoadState=not-found\nActiveState=inactive\nResult=success\n", b"")))
    # Even if the transient unit was collected, completed results above remain queryable.
    status = asyncio.run(module.review_python_source(str(source), job_id=job["job_id"]))
    assert status["state"] == "failed" and not status["success"]

def test_server_still_registers_same_tool():
    source = Path("/data/vm_project/harness/mcp/sps_harness_server.py").read_text()
    compile(source, "<server>", "exec")
    assert "mcp.tool()(review_python_source)" in source

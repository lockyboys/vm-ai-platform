"""Expose the existing main orchestrator through an isolated systemd worker."""
from __future__ import annotations

import asyncio
import json
import sys
from time import monotonic

import config as project_config
from common.common_function import normalize_required_text
from haness.mcp.agents.source_partner_agent import run_source_partner_agent as _run_source_partner_agent
from haness.mcp.tools.change_set_graph import run_change_set as _run_change_set
from haness.mcp.tools.multi_persona_tools import (
    PROJECT_ROOT, _mask_secrets, _stop_review, _systemd_command,
)


async def run_sps_orchestrator(query: str, dry_run: bool = True) -> dict:
    """Run a task with the SPS LangGraph orchestrator.

    mode=source_agent runs the actual PARTNER LLM/tool loop, while
    mode=change_set directly runs its deterministic source-change backend.
    Source patches proceed after their dry-run check. source_write and git
    commit receive only the explicit confirmation fields supplied at this MCP
    boundary. Git staging runs inside the backend graph. Other queries keep
    using the existing Gemini graph.
    """
    if not isinstance(query, str):
        raise ValueError("query must be text")
    query = normalize_required_text(query, "query")
    if len(query) > 20000:
        raise ValueError("query exceeds 20000 characters")
    if query.lstrip().startswith("{"):
        try:
            payload = json.loads(query)
        except json.JSONDecodeError as exc:
            raise ValueError("JSON query is invalid") from exc
        if isinstance(payload, dict):
            if payload.get("mode") == "change_set":
                # 파일·Git 작업은 동기 도구이므로 이벤트 루프를 막지 않게 별도 스레드에서 그래프를 실행한다.
                return await asyncio.to_thread(_run_change_set, payload, bool(dry_run))
            if payload.get("mode") == "source_agent":
                source_write_confirmed = payload.get("source_write_confirmed", False)
                if not isinstance(source_write_confirmed, bool):
                    raise ValueError("source_write_confirmed must be boolean")
                commit = payload.get("commit", {})
                if not isinstance(commit, dict):
                    raise ValueError("commit must be an object")
                commit_confirmed = commit.get("confirmed", False)
                if not isinstance(commit_confirmed, bool):
                    raise ValueError("commit.confirmed must be boolean")
                task = payload.get("task")
                if not isinstance(task, str):
                    raise ValueError("source_agent task must be text")
                return await _run_source_partner_agent(
                    task,
                    dry_run=bool(dry_run),
                    source_write_confirmed=source_write_confirmed,
                    commit_confirmed=commit_confirmed,
                )

    timeout = int(project_config.SPS_MAIN_ORCHESTRATOR_TIMEOUT_SECONDS)
    if not 1 <= timeout <= 120:
        raise ValueError("Orchestrator timeout must be between 1 and 120 seconds")
    unit, command = _systemd_command(
        ["-m", "haness.mcp.tools.orchestrator_tools", "--worker"], timeout, "orchestrator")
    plan = {"dry_run": bool(dry_run), "executed": False, "command": command,
            "timeout_seconds": timeout}
    if dry_run:
        return plan
    # Pass the task through stdin rather than exposing its content in process arguments.
    started = monotonic()
    process = await asyncio.create_subprocess_exec(
        *command, cwd=str(PROJECT_ROOT), stdin=asyncio.subprocess.PIPE,
        stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
    try:
        output, errors = await asyncio.wait_for(
            process.communicate(json.dumps({"query": query}).encode()), timeout=timeout + 4)
    except asyncio.TimeoutError:
        await _stop_review(process, unit)
        return {**plan, "executed": True, "success": False, "timed_out": True}
    except asyncio.CancelledError:
        await _stop_review(process, unit)
        raise
    elapsed = monotonic() - started
    timed_out = process.returncode != 0 and elapsed >= timeout
    text = _mask_secrets(output.decode("utf-8", errors="replace"))
    errors = _mask_secrets(errors.decode("utf-8", errors="replace"))
    # Preserve an auditable full response and bound the MCP preview.
    report = PROJECT_ROOT / "harness/memory/orchestrator_runs" / (unit + ".txt")
    report.parent.mkdir(parents=True, exist_ok=True)
    report.write_text(text + errors, encoding="utf-8")
    return {**plan, "executed": True, "success": not timed_out and process.returncode == 0 and bool(text.strip()),
            "returncode": process.returncode, "timed_out": timed_out,
            "elapsed_seconds": round(elapsed, 3),
            "output": text[:12000], "stderr": errors[:12000],
            "output_truncated": len(text) > 12000 or len(errors) > 12000,
            "report_path": str(report.relative_to(PROJECT_ROOT))}


async def _worker() -> None:
    # Load the original graph only inside the requested, environment-configured worker.
    from FastAPI.LangGraph.sps_main_orchestrator import ChatRequest, api_chat_orchestrator
    request = json.loads(sys.stdin.read())
    result = await api_chat_orchestrator(ChatRequest(query=request["query"]))
    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__" and sys.argv[1:] == ["--worker"]:
    asyncio.run(_worker())

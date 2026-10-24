"""실제 LLM 기반 PARTNER 소스 에이전트의 도구 루프와 승인 경계를 검증한다."""
from __future__ import annotations

import asyncio
import json
from unittest.mock import AsyncMock

import pytest

from haness.mcp.agents import source_partner_agent
from haness.mcp.tools import orchestrator_tools


def test_empty_task_is_rejected_before_model_creation(monkeypatch):
    """잘못된 빈 작업은 LLM을 만들거나 호출하기 전에 거부해야 한다."""
    called = []
    monkeypatch.setattr(
        source_partner_agent,
        "_build_model",
        lambda: called.append(True),
    )

    with pytest.raises(ValueError, match="task"):
        asyncio.run(source_partner_agent.run_source_partner_agent("   "))

    assert called == []


def test_change_set_tool_forces_trusted_approval_values(monkeypatch):
    """LLM이 승인 필드를 위조해도 호출자가 전달한 승인 값만 실행기에 들어가야 한다."""
    captured = []
    monkeypatch.setattr(
        source_partner_agent,
        "run_change_set",
        lambda payload, dry_run: captured.append((payload, dry_run)) or {"state": "PLANNED"},
    )
    tools = source_partner_agent.build_partner_tools(
        dry_run=False,
        source_write_confirmed=False,
        commit_confirmed=False,
    )
    execute_tool = next(tool for tool in tools if tool.name == "execute_change_set")
    payload = {
        "mode": "change_set",
        "change_set_id": "agent-test",
        "source_write_confirmed": True,
        "writes": [{"path": "haness/new.py", "content": "VALUE = 1\n"}],
        "patch_text": "",
        "test_paths": ["tests/harness/mcp/test_source_partner_agent.py"],
        "stage_groups": {"source": ["haness/new.py"], "tests": [], "docs": [], "operations": []},
        "commit": {"requested": True, "confirmed": True, "message": "feat: agent test"},
    }

    result = execute_tool.invoke({"change_set_json": json.dumps(payload)})

    assert json.loads(result)["state"] == "PLANNED"
    assert captured[0][1] is False
    assert captured[0][0]["source_write_confirmed"] is False
    assert captured[0][0]["commit"]["confirmed"] is False


def test_partner_tools_include_inspection_and_guarded_execution():
    """PARTNER는 저장소를 읽고 차이를 확인한 뒤 변경 세트 실행기를 호출할 수 있어야 한다."""
    names = {
        tool.name
        for tool in source_partner_agent.build_partner_tools(
            dry_run=True,
            source_write_confirmed=False,
            commit_confirmed=False,
        )
    }

    assert names == {
        "search_source",
        "read_source",
        "get_git_status",
        "get_git_diff",
        "execute_change_set",
    }


def test_graph_binds_tools_to_model():
    """LangGraph 에이전트 노드는 LangChain 모델에 실제 도구를 bind_tools 해야 한다."""
    class FakeBoundModel:
        async def ainvoke(self, messages):
            raise AssertionError("그래프 작성만 검증하므로 호출되면 안 된다")

    class FakeModel:
        def __init__(self):
            self.bound_tools = None

        def bind_tools(self, tools):
            self.bound_tools = tools
            return FakeBoundModel()

    model = FakeModel()
    graph = source_partner_agent.build_source_partner_graph(
        model=model,
        tools=source_partner_agent.build_partner_tools(
            dry_run=True,
            source_write_confirmed=False,
            commit_confirmed=False,
        ),
    )

    assert graph is not None
    assert {tool.name for tool in model.bound_tools} >= {"read_source", "execute_change_set"}


def test_public_orchestrator_routes_source_agent_mode(monkeypatch):
    """공개 MCP 함수는 source_agent JSON 요청을 실제 PARTNER 실행기로 전달해야 한다."""
    expected = {"agent": "PARTNER", "success": True}
    runner = AsyncMock(return_value=expected)
    monkeypatch.setattr(orchestrator_tools, "_run_source_partner_agent", runner)
    request = {
        "mode": "source_agent",
        "task": "버그를 재현하고 수정하라",
        "source_write_confirmed": False,
        "commit": {"requested": True, "confirmed": False},
    }

    result = asyncio.run(
        orchestrator_tools.run_sps_orchestrator(
            json.dumps(request, ensure_ascii=False),
            dry_run=True,
        )
    )

    assert result is expected
    runner.assert_awaited_once_with(
        "버그를 재현하고 수정하라",
        dry_run=True,
        source_write_confirmed=False,
        commit_confirmed=False,
    )

import asyncio
import json

import pytest

from haness.mcp.agents.source_partner_agent import build_partner_tools


def _chromium_tool():
    tools = build_partner_tools(
        dry_run=True,
        source_write_confirmed=False,
        commit_confirmed=False,
    )
    return next(tool for tool in tools if tool.name == "run_chromium_check")


def _result(path, **kwargs):
    raw = asyncio.run(_chromium_tool().ainvoke({"path": path, **kwargs}))
    return json.loads(raw)


def test_chromium_check_dry_run_does_not_launch_browser():
    result = _result(
        "haness/apps/tetris_combined_chromium_20261026/tetris.html"
    )
    assert result["status"].startswith("planned;")
    assert result["browser"] == "chromium"


def test_chromium_check_requires_explicit_execution_confirmation():
    result = _result(
        "haness/apps/tetris_combined_chromium_20261026/tetris.html",
        dry_run=False,
        execute_confirmed=False,
    )
    assert result["status"].startswith("planned;")


def test_chromium_check_rejects_paths_outside_allowed_roots():
    with pytest.raises(ValueError, match="allowed application roots"):
        asyncio.run(
            _chromium_tool().ainvoke(
                {"path": "web/templates/mindmap_v7.20.0.html"}
            )
        )

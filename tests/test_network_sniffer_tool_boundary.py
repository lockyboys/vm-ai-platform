"""Crawler agent must not receive source-repair tools.

This regression test prevents a document collector from invoking the
self-repair API without a file_path argument.
"""

import ast
from pathlib import Path


SOURCE_PATH = (
    Path(__file__).resolve().parents[1]
    / "FastAPI"
    / "LangGraph"
    / "Agent_Import_PFDs"
    / "LangGraph_Network_Sniffer.py"
)


def _crawler_tool_names():
    tree = ast.parse(SOURCE_PATH.read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if isinstance(node, ast.AsyncFunctionDef) and node.name == "explore_unknown_site":
            for child in ast.walk(node):
                if isinstance(child, ast.Assign):
                    for target in child.targets:
                        if isinstance(target, ast.Name) and target.id == "tools":
                            value = child.value
                            assert isinstance(value, ast.List)
                            return [
                                element.id
                                for element in value.elts
                                if isinstance(element, ast.Name)
                            ]
    raise AssertionError("explore_unknown_site tools list was not found")


def test_crawler_does_not_bind_source_repair_tools():
    tool_names = _crawler_tool_names()
    assert "read_repair_source" not in tool_names
    assert "source_patch" not in tool_names

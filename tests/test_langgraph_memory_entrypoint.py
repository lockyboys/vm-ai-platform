"""Verify both legacy import modes without starting AI clients."""
import runpy
import sys
from pathlib import Path
from types import ModuleType

import pytest


@pytest.mark.parametrize("module_name,run_name", [
    ("langgraph_long_term_memory_agent", "main"),
    ("FastAPI.LangGraph.langgraph_long_term_memory_agent", "FastAPI.LangGraph.main"),
])
def test_main_reuses_agent_app(monkeypatch, module_name, run_name):
    module = ModuleType(module_name)
    module.app = object()
    monkeypatch.setitem(sys.modules, module_name, module)
    path = Path(__file__).resolve().parents[1] / "FastAPI/LangGraph/main.py"
    namespace = runpy.run_path(str(path), run_name=run_name)
    assert namespace["app"] is module.app

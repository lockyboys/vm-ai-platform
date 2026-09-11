"""Harness 테스트를 공식 tests 진입점으로 노출한다."""
import runpy
from pathlib import Path
_suite = runpy.run_path(str(Path(__file__).resolve().parents[1] / "harness/tests/test_langgraph_memory_chat_api.py"))
globals().update({name: value for name, value in _suite.items() if name.startswith("test_") or name == "api"})

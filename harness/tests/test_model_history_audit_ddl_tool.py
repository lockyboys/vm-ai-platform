"""Compatibility wrapper for the guarded DDL MCP tool tests."""
from __future__ import annotations

from pathlib import Path
from runpy import run_path

_test_file = Path(__file__).resolve().parents[2] / "tests" / "test_model_history_audit_ddl_tool.py"
_namespace = run_path(str(_test_file))
globals().update({name: value for name, value in _namespace.items() if name.startswith("test_")})

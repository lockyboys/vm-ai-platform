"""Validate Gateway command input without calling Gemini or importing service credentials."""
import ast
from pathlib import Path
import pytest

ROOT = Path(__file__).resolve().parents[3]
SOURCE = ROOT / "FastAPI/LangGraph/gemini/sps_gateway_command.py"

def validator():
    # Compile only the pure input boundary; tests must never mint credentials or run an LLM.
    tree = ast.parse(SOURCE.read_text(encoding="utf-8"))
    node = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "validate_request")
    namespace = {}
    exec(compile(ast.Module(body=[node], type_ignores=[]), str(SOURCE), "exec"), namespace)
    return namespace["validate_request"]

@pytest.mark.parametrize("payload", [None, {}, {"message": "hi"}, {"user_input": 1}, {"user_input": ""}, {"user_input": "  "}, {"user_input": "x" * 20001}])
def test_invalid_commands_are_rejected(payload):
    # Reject malformed inputs before launching a worker or issuing a bearer.
    with pytest.raises(ValueError):
        validator()(payload)

def test_valid_command_is_preserved():
    assert validator()({"user_input": "현재 도구 목록을 알려줘"}) == "현재 도구 목록을 알려줘"

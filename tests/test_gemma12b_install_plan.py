"""설치 전에 중첩 원격 스크립트의 문법과 줄바꿈 경계를 검사합니다."""
import ast
from pathlib import Path
FILE = Path(__file__).resolve().parents[1] / "FastAPI/LangGraph/install_gpu_gemma12b.py"

def worker_tree():
    outer = ast.parse(FILE.read_text())
    script = next(n.value.value for n in outer.body if isinstance(n, ast.Assign) and any(isinstance(t, ast.Name) and t.id == "script" for t in n.targets))
    remote = ast.parse(script)
    worker = next(n.value.value for n in remote.body if isinstance(n, ast.Assign) and any(isinstance(t, ast.Name) and t.id == "worker" for t in n.targets))
    return ast.parse(worker)

def test_nested_script_syntax():
    worker_tree()

def test_code_fence_splits_actual_newline():
    tree = worker_tree()
    splits = [n for n in ast.walk(tree) if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute) and n.func.attr == "split"]
    assert any(n.args and isinstance(n.args[0], ast.Constant) and n.args[0].value == "\n" for n in splits)

def test_smoke_prompt_preserves_actual_python_lines():
    tree = worker_tree()
    prompt = next(n.value for n in ast.walk(tree) if isinstance(n, ast.Constant) and isinstance(n.value, str) and n.value.startswith("Fix this Python"))
    assert "\ndef safe_divide" in prompt

"""원본 FastAPI/LangGraph/LangGraph_MariaDB_Memory_Agent.py 테스트 (2026-11-15). 내용은 selffix_memory_agent/memory_agent_cases.py 공용."""
import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
TARGET = ROOT / "FastAPI/LangGraph/LangGraph_MariaDB_Memory_Agent.py"
_spec = importlib.util.spec_from_file_location("memory_agent_cases", Path(__file__).parent / "selffix_memory_agent/memory_agent_cases.py")
_cases = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_cases)
_cases.load_cases(globals(), TARGET)

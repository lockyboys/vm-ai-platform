"""ChatGPT(openai) 자가 수정 복사본 테스트 (2026-11-16). 내용은 memory_agent_cases.py 공용, 대상 경로만 다르다."""
import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
TARGET = ROOT / "FastAPI/LangGraph/selffix_demo/memory_agent/openai/LangGraph_MariaDB_Memory_Agent.py"
_spec = importlib.util.spec_from_file_location("memory_agent_cases_openai", Path(__file__).parent / "memory_agent_cases.py")
_cases = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_cases)
_cases.load_cases(globals(), TARGET)

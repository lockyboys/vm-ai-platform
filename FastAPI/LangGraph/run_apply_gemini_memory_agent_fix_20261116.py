"""apply_gemini_memory_agent_fix_20261116.py 를 --apply(원본에 반영)로 실행하는 감싸기. 원본이 바뀌었으면 검사에서 스스로 멈춘다."""
import runpy
import sys
from pathlib import Path

target = Path(__file__).resolve().parent / "apply_gemini_memory_agent_fix_20261116.py"
sys.argv = [str(target), "--apply"]
runpy.run_path(str(target), run_name="__main__")

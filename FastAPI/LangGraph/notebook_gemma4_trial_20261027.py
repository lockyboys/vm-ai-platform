"""노트북 Gemma4 시험기의 MCP 호환 진입점."""
import runpy
import sys
from pathlib import Path
# 독립 워커에서도 공통 모듈을 찾도록 저장소 루트를 명시한다.
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
runpy.run_path("/data/vm_project/haness/scripts/notebook_gemma4_trial_20261027.py",run_name="__main__")

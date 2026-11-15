"""harness/scripts/reorganize_a7c2fca_20261115.py 를 dry-run(브랜치 그대로)으로 실행하는 감싸기."""
import runpy
import sys
from pathlib import Path

target = Path(__file__).resolve().parents[2] / "harness/scripts/reorganize_a7c2fca_20261115.py"
sys.argv = [str(target)]
runpy.run_path(str(target), run_name="__main__")

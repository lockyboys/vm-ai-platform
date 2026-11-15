"""harness/scripts/reorganize_a7c2fca_20261115.py 를 --apply(브랜치를 새 기록으로 옮김)로 실행하는 감싸기. push는 하지 않는다."""
import runpy
import sys
from pathlib import Path

target = Path(__file__).resolve().parents[2] / "harness/scripts/reorganize_a7c2fca_20261115.py"
sys.argv = [str(target), "--apply"]
runpy.run_path(str(target), run_name="__main__")

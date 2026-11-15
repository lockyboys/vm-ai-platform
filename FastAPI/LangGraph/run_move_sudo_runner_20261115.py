"""harness/scripts/move_sudo_runner_20261115.py 실행 감싸기. MODE를 "--apply"로 바꿀 때만 반영(기본 dry-run)."""
import runpy
import sys
from pathlib import Path

MODE = sys.argv[1] if len(sys.argv) > 1 else ""
target = Path(__file__).resolve().parents[2] / "harness/scripts/move_sudo_runner_20261115.py"
sys.argv = [str(target)] + ([MODE] if MODE else [])
runpy.run_path(str(target), run_name="__main__")

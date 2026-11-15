"""harness/scripts/move_sudo_runner_20261115.py 를 --apply(실제 반영)로 실행하는 감싸기. 이미 반영됐으면 검사에서 스스로 멈춘다."""
import runpy
import sys
from pathlib import Path

target = Path(__file__).resolve().parents[2] / "harness/scripts/move_sudo_runner_20261115.py"
sys.argv = [str(target), "--apply"]
runpy.run_path(str(target), run_name="__main__")

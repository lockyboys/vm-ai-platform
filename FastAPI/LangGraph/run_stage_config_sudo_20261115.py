"""config.py index에 uncommit + sudo 블록을 넣는다(stage_config_part_20261115.py sudo --apply). 검사 실패 시 스스로 멈춤."""
import runpy
import sys
from pathlib import Path

target = Path(__file__).resolve().parents[2] / "harness/scripts/stage_config_part_20261115.py"
sys.argv = [str(target), "sudo", "--apply"]
runpy.run_path(str(target), run_name="__main__")

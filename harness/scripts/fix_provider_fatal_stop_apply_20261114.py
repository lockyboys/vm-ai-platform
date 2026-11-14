"""fix_provider_fatal_stop_20261114.py를 --apply로 실행하는 감싸기(도구 argv가 SSH 인자로 쓰여 직접 넘길 수 없음)."""
import runpy
import sys
from pathlib import Path

sys.argv = [str(Path(__file__).with_name("fix_provider_fatal_stop_20261114.py")), "--apply"]
runpy.run_path(sys.argv[0], run_name="__main__")

"""commit_fatal_config_part_20261116.py 를 --apply 로 실행하는 감싸기 (실행 도구가 argv 를 못 넘겨서 둠, 2026-11-16 일회용)."""
import runpy
import sys
from pathlib import Path

sys.argv = ["commit_fatal_config_part_20261116.py", "--apply"]   # 실제 커밋 모드
runpy.run_path(str(Path(__file__).with_name("commit_fatal_config_part_20261116.py")), run_name="__main__")

"""build_hard10_20261114.py를 --write로 실행하는 진입점 (2026-11-14).

MCP 실행 도구가 argv를 SSH 인자로 해석해 인자를 넘길 수 없으므로, 이 파일이 --write를 대신 붙인다.
(build_hard_write_targets.py와 같은 방식)
"""
import runpy
import sys
from pathlib import Path

sys.argv = [str(Path(__file__).with_name("build_hard10_20261114.py")), "--write"]
runpy.run_path(sys.argv[0], run_name="__main__")

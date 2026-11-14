"""build_hard.py를 --write-targets 로 실행하는 래퍼 (2026-11-11).

실행 도구(mcp_codex_apps_run_python_source)가 인자를 넘길 수 없어 만든 파일이다.
AI별 대상 파일과 보존용 원본을 처음 한 번 만든다(이미 있으면 build_hard가 덮어쓰지 않고 중단).
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[4]))  # 프로젝트 루트(config.py 위치)
sys.argv = [sys.argv[0], "--write-targets"]

from FastAPI.LangGraph.selffix_demo.hard import build_hard  # noqa: E402

build_hard.main()

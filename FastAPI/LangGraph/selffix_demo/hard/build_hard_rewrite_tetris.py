"""build_hard.py를 --rewrite=tetris_engine 로 실행하는 래퍼 (2026-11-11).

테트리스 정답 소스 docstring 보강(명세에 없던 기본값·상수·모양을 명시) 뒤, 결함 사본을 다시 만든다.
실행 도구가 인자를 넘길 수 없어 만든 파일이다. AI가 고쳐 반영된 사본이 있으면 build_hard가 중단한다.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[4]))  # 프로젝트 루트(config.py 위치)
sys.argv = [sys.argv[0], "--rewrite=tetris_engine"]

from FastAPI.LangGraph.selffix_demo.hard import build_hard  # noqa: E402

build_hard.main()

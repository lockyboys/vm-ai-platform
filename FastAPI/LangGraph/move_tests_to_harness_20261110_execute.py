"""move_tests_to_harness_20261110.py 실행 모드 진입점 (2026-11-10, dry-run 37건 확인 후 LuckyBoys 지시로 실행).

MCP 실행 도구의 argv는 SSH 전용이라 --execute를 이 파일에서 고정해 넘긴다.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import move_tests_to_harness_20261110 as mover  # noqa: E402

if __name__ == "__main__":
    sys.argv = [sys.argv[0], "--execute"]  # 실행 모드 고정
    mover.main()

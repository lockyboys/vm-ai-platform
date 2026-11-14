"""migrate_haness_to_harness_20261102.py를 실행 모드(--execute)로 부르는 1회성 진입점 (2026-11-02).

이유: MCP 실행 도구의 argv 인자는 SSH 실행 전용이라 로컬 스크립트에 --execute를 넘길 수 없다.
      dry-run 결과(이동 1162, 충돌 0, 수정 230파일)를 LuckyBoys가 승인한 뒤에만 이 파일을 실행한다.
"""
import sys
from pathlib import Path

# 같은 폴더의 이동 스크립트를 import할 수 있게 경로를 추가한다.
sys.path.insert(0, str(Path(__file__).resolve().parent))
import migrate_haness_to_harness_20261102 as migration  # noqa: E402

if __name__ == "__main__":
    sys.argv = [sys.argv[0], "--execute"]  # 실행 모드 고정
    migration.main()

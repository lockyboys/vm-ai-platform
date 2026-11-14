"""SPS 실행 도구의 경로 제한을 위한 호환 진입점. 에이전트는 기존 소스 내부에 유지한다."""
from pathlib import Path
import runpy

if __name__ == "__main__":
    root = Path(__file__).resolve().parents[2]
    runpy.run_path(str(root / "haness/tests/apply_source_repair_update.py"), run_name="__main__")

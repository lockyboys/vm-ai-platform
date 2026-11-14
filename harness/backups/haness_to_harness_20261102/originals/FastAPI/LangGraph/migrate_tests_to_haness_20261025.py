"""실행 연결 전용: 실제 소스는 haness/scripts/migrate_tests_to_haness_20261025.py (일반 지침 10).

run_python_source가 FastAPI/LangGraph 아래만 실행하므로, 같은 이름으로 연결만 한다.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from haness.scripts.migrate_tests_to_haness_20261025 import main  # noqa: E402

if __name__ == "__main__":
    main()

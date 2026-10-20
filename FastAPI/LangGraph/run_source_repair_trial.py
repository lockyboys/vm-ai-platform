"""운영 소스를 변경하지 않는 자율 수정 시험 진입점."""
from pathlib import Path
import json
import runpy
import sys

if __name__ == "__main__":
    root = Path(__file__).resolve().parents[2]
    request = json.load(sys.stdin)
    action = request.get("action", "unit")
    if action not in {"unit", "live"}:
        raise ValueError("지원하지 않는 시험")
    script = "test_source_repair.py" if action == "unit" else "live_source_repair_trial.py"
    sys.argv = [script]
    runpy.run_path(str(root / "haness/tests" / script), run_name="__main__")

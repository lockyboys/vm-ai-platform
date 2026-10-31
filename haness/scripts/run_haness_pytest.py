"""haness/tests 등 지정 테스트를 pytest로 실행하고 요약만 출력한다(run_pytest_verification이 tests/만 허용하므로).

입력(stdin JSON): {"test_paths": ["haness/tests/...", "tests/..."]}
- 프로젝트 루트 밖·.. 포함 경로·없는 파일은 거부한다. 출력: returncode, 마지막 요약 줄, 실패 줄.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path, PurePosixPath

ROOT = Path(__file__).resolve().parents[2]


def main() -> None:
    paths = json.loads(sys.stdin.read() or "{}").get("test_paths") or []
    if not isinstance(paths, list) or not paths:
        raise ValueError("test_paths must be a non-empty list")
    for path in paths:
        relative = PurePosixPath(str(path))
        if relative.is_absolute() or ".." in relative.parts or not (ROOT / relative).is_file():
            raise ValueError(f"invalid test path: {path}")
    done = subprocess.run([sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider", *paths],
                          cwd=ROOT, capture_output=True, text=True, timeout=600)
    lines = done.stdout.splitlines()
    print(json.dumps({"returncode": done.returncode, "summary": lines[-1] if lines else "",
                      "failures": [l for l in lines if l.startswith(("FAILED", "ERROR"))][:50],
                      "stderr_tail": done.stderr[-800:]}, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()

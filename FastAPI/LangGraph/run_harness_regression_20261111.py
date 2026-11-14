"""harness/tests 전체 회귀 실행 (2026-11-11, 자가 수정 앱 변경 후 사이드 이펙트 확인용).

- 이미 알려진 기존 문제 파일(test_self_repair_collect_tools_20261110.py: config에 SELF_REPAIR_COLLECT 없음,
  이번 작업과 무관)은 수집 단계에서 전체를 멈추므로 --ignore로 제외하고, 제외 사실을 출력에 남긴다.
- selffix_hard/ 의 bench 파일은 이름이 test_로 시작하지 않아 자동 수집되지 않는다.
- 결과 요약(마지막 30줄)만 출력한다. LLM 호출 없음.
"""
import subprocess
import sys
from pathlib import Path

import config  # 루트 공통 설정(일반 지침 4)

ROOT = Path(config.PROJECT_ROOT)
KNOWN_BROKEN = "harness/tests/test_self_repair_collect_tools_20261110.py"

run = subprocess.run(
    [sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider", "harness/tests",
     f"--ignore={KNOWN_BROKEN}"],
    cwd=str(ROOT), stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=1500, check=False)
lines = run.stdout.decode("utf-8", errors="replace").splitlines()
print(f"[제외] {KNOWN_BROKEN} (기존 문제, 이번 변경과 무관)")
print(f"[returncode] {run.returncode}")
print("\n".join(lines[-30:]))

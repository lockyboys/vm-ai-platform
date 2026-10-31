"""test_source_partner_agent.py 위치 이동 (2026-11-01, LuckyBoys 지시: tests/harness/mcp → haness/tests).

이유: 테스트 위치 규칙은 haness/tests/ 이다(10-25 이동 계획 haness/scripts/migrate_tests_to_haness_20261025.py와 같음).
동작: git mv 로 옮겨 Git 이력을 유지한다. 내용은 바꾸지 않으며, 이동 전후 sha256이 같은지 확인한다.
주의: 목적지가 이미 있으면 덮어쓰지 않고 중단한다(원본 보존). 커밋은 하지 않는다.
"""
import hashlib
import json
import subprocess
from pathlib import Path

import config  # 루트 공통 설정(일반 지침 4) — PROJECT_ROOT

SOURCE = "tests/harness/mcp/test_source_partner_agent.py"
DESTINATION = "haness/tests/test_source_partner_agent.py"


def main() -> None:
    root = Path(config.PROJECT_ROOT)
    src, dst = root / SOURCE, root / DESTINATION
    if not src.is_file():
        raise FileNotFoundError(SOURCE)
    if dst.exists():
        raise FileExistsError(f"destination already exists: {DESTINATION}")
    before = hashlib.sha256(src.read_bytes()).hexdigest()
    done = subprocess.run(["git", "mv", SOURCE, DESTINATION], cwd=root,
                          capture_output=True, text=True, timeout=30)
    after = hashlib.sha256(dst.read_bytes()).hexdigest() if dst.is_file() else None
    print(json.dumps({"source": SOURCE, "destination": DESTINATION, "returncode": done.returncode,
                      "stderr": done.stderr[-500:], "sha256_before": before, "sha256_after": after,
                      "content_unchanged": before == after, "source_removed": not src.exists()},
                     ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()

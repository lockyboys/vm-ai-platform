"""harness/tests 의 test_*.py 목록을 JSON으로 출력한다 (2026-11-11).

전체 회귀를 비동기 pytest job(submit_pytest_job)으로 돌리기 위해 파일 목록만 뽑는다.
(동기 실행 도구로 전체 회귀를 돌리면 MCP 서버가 끝날 때까지 다른 요청에 응답하지 못했다.)
"""
import json
from pathlib import Path

import config  # 루트 공통 설정(일반 지침 4)

root = Path(config.PROJECT_ROOT)
print(json.dumps(sorted(str(p.relative_to(root)) for p in (root / "harness/tests").glob("test_*.py"))))

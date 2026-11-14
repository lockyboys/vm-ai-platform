"""공용 리뷰 CLI가 공급자별로 '모델 생성까지' 되는지 확인하는 스모크 테스트 (2026-11-10).

방법: CLI를 --help로 실행한다. 모듈 import 시 모델 객체가 만들어지고 --help에서 바로 끝나므로
      LLM 호출(비용)은 0회다. 공급자별 종료 코드와 마지막 오류 줄만 출력한다(키 값 미출력).
"""
import json
import subprocess
import sys
from pathlib import Path

import config  # 루트 공통 설정(일반 지침 4)

ROOT = Path(config.PROJECT_ROOT)
CLI = ROOT / "FastAPI/LangGraph/multi_persona/multi_persona_agent_gemini.py"

report = {}
for provider in ["gemini", "openai", "claude"]:
    done = subprocess.run([sys.executable, str(CLI), "--provider", provider, "--help"],
                          cwd=str(ROOT), capture_output=True, text=True, timeout=120)
    tail = (done.stderr.strip().splitlines() or [""])[-1][:300]
    report[provider] = {"returncode": done.returncode, "last_error_line": tail if done.returncode else ""}
print(json.dumps(report, ensure_ascii=False, indent=1))

"""haness->harness 이동 + 자가 수정 기능 수정 커밋 (2026-11-03, LuckyBoys 지시: orchestrator 3개 "같이").

스테이징 범위(명시 경로만, 광범위 pathspec 사용 안 함):
  1) 이동 매니페스트의 git 추적 파일 이동(이미 git mv로 스테이징됨)
  2) 참조 수정 파일 중 git 추적 파일(이동 후 경로)
  3) 이번 작업에서 고친 파일(review_contract.py, multi_persona_tools.py, 테스트, config.py 등)
  4) 다른 세션이 스테이징한 orchestrator 파일 3개(이동 후 경로)
미추적 파일(일회성 스크립트·백업·실행 기록)은 추가하지 않는다. push 하지 않는다.
"""
import json
import subprocess
from pathlib import Path

import config  # 루트 공통 설정(일반 지침 4)

ROOT = Path(config.PROJECT_ROOT)
MANIFEST = ROOT / "harness/memory/migrations/haness_to_harness_20261102.json"
EXTRA = [
    "config.py",
    "FastAPI/LangGraph/multi_persona/review_contract.py",
    "FastAPI/LangGraph/multi_persona/multi_persona_agent_gemini.py",
    "harness/mcp/tools/multi_persona_tools.py",
    "harness/mcp/tools/orchestrator_tools.py",
    "harness/tests/test_orchestrator_background_job_20261102.py",
    "harness/tests/test_orchestrator_timeout_max_20261102.py",
    "harness/tests/test_review_selffix_20261102.py",
    "harness/tests/test_timeout_policy_20261026.py",
    "harness/tests/test_persona_repair_chain.py",
    "tests/harness/mcp/test_multi_persona_review_tool.py",
]
MESSAGE = """Move haness/ to harness/ and harden review_python_source self-fix checks

- Move haness/ package to harness/ (git mv for tracked files) and rewrite module/path references
- validate_review: reject proposals that reference non-existent import/-m modules
- review_python_source: model_verified/success require verifier + contract + proposed.py
- Store review.md/proposed.py per job (--output-dir) to avoid concurrent overwrite
- Review timeout 3590s + 10s grace within 3600s unit cap; persist lost-worker failures
- Apply Gemini review proposal to review_contract.py (job 03b52a4d)
- Update persona reference sha256 after skill guideline sync (haness -> harness)
- Include orchestrator background job changes staged by another session

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
Claude-Session: https://claude.ai/code/session_01PXp2JKBTsb3CZKbbPSQjrV
"""


def _git(*args: str) -> str:
    return subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True, check=True).stdout


def main() -> None:
    tracked = set(_git("ls-files", "-z").split("\0")) - {""}
    data = json.loads(MANIFEST.read_text(encoding="utf-8"))
    rewrite_paths = [r["final_path"] for r in data["rewrites"] if r["final_path"] in tracked]
    paths = sorted({p for p in rewrite_paths + EXTRA if (ROOT / p).exists()})
    for start in range(0, len(paths), 200):  # 명령 길이 제한 회피용 분할
        _git("add", "--", *paths[start:start + 200])
    staged = [line for line in _git("diff", "--cached", "--name-status").splitlines() if line]
    _git("commit", "-q", "-F", "-", ) if False else subprocess.run(
        ["git", "commit", "-q", "-F", "-"], cwd=ROOT, input=MESSAGE, text=True, check=True)
    head = _git("log", "-1", "--format=%h %s").strip()
    leftover = [l for l in _git("diff", "--cached", "--name-only").splitlines() if l]
    print(json.dumps({"staged_entries": len(staged),
                      "renames": sum(1 for l in staged if l.startswith("R")),
                      "commit": head, "still_staged_after": len(leftover)}, ensure_ascii=False))


if __name__ == "__main__":
    main()

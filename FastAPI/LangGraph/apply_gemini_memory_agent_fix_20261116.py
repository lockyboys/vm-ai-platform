"""Gemini 자가 수정안을 원본 LangGraph_MariaDB_Memory_Agent.py에 반영한다 (2026-11-16, LuckyBoys 결정).

반영할 내용: 개선 후 재시험(job 18ceb65c)에서 Gemini가 2차에 만든 수정안 = 현재 gemini 복사본
  FastAPI/LangGraph/selffix_demo/memory_agent/gemini/LangGraph_MariaDB_Memory_Agent.py (테스트 18/18)
  (Tavily·모델명 유지, 고친 것: 약관 검색어를 마지막 사용자 질문으로, __main__ 의 DB 연결 try...finally)
안전장치
- 원본이 시험 시작 때와 같을 때만 진행(sha256 f43a67d1…). 다르면 멈춘다(그사이 누가 고쳤을 수 있음).
- 복사본이 job 결과 파일(round2/proposed.py)과 같은지 확인.
- 원본은 harness/backups/memory_agent_gemini_fix_20261116/ 에 먼저 보존. 반영 후 compile 확인.
- MODE 인자: 없으면 dry-run(검사만), "--apply"면 반영, "--restore"면 백업으로 되돌림.
"""
import hashlib
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ORIGINAL = ROOT / "FastAPI/LangGraph/LangGraph_MariaDB_Memory_Agent.py"
COPY = ROOT / "FastAPI/LangGraph/selffix_demo/memory_agent/gemini/LangGraph_MariaDB_Memory_Agent.py"
PROPOSED = ROOT / "harness/memory/source_reviews/job_18ceb65c9438419ab4cc64484a1a64d4/round2/proposed.py"
BACKUP = ROOT / "harness/backups/memory_agent_gemini_fix_20261116/LangGraph_MariaDB_Memory_Agent.py"
EXPECTED_ORIGINAL = "f43a67d16f89f945e83cd4a83b1274e7fd63d842730749d4f072dd02d072a753"
MODE = sys.argv[1] if len(sys.argv) > 1 else ""


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


if MODE == "--restore":
    shutil.copy2(BACKUP, ORIGINAL)
    print({"restored": True, "sha256": sha(ORIGINAL)[:16]})
    raise SystemExit(0)

checks = {
    "original_unchanged_since_test": sha(ORIGINAL) == EXPECTED_ORIGINAL,
    "copy_equals_gemini_proposal": sha(COPY) == sha(PROPOSED),
    "copy_differs_from_original": sha(COPY) != sha(ORIGINAL),
}
compile(COPY.read_text(encoding="utf-8"), str(COPY), "exec")
print({"checks": checks, "copy_sha256": sha(COPY)[:16]})
if not all(checks.values()):
    raise SystemExit("[중단] 검사 실패 — 반영하지 않음")
if MODE != "--apply":
    print("[dry-run] 통과. 원본은 바꾸지 않았습니다.")
    raise SystemExit(0)
BACKUP.parent.mkdir(parents=True, exist_ok=True)
if not BACKUP.exists():
    shutil.copy2(ORIGINAL, BACKUP)
shutil.copy2(COPY, ORIGINAL)
print({"applied": True, "original_sha256_now": sha(ORIGINAL)[:16], "backup": str(BACKUP.relative_to(ROOT))})

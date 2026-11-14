"""Gemini 리뷰 제안(job 03b52a4d)을 review_contract.py에 반영하는 1회성 스크립트 (2026-11-03, LuckyBoys 지시 "넣어").

순서: 1) 현재 원본을 harness/backups/review_contract_proposal_20261103/에 백업(일반 지침 7)
      2) 제안 소스 문법 확인(py_compile) — 실패하면 원본을 건드리지 않고 중단
      3) 제안 소스로 교체 후 sha256 출력
LLM 호출 없음.
"""
import hashlib
import json
import py_compile
import shutil
from pathlib import Path

import config  # 루트 공통 설정(일반 지침 4)

ROOT = Path(config.PROJECT_ROOT)
TARGET = ROOT / "FastAPI/LangGraph/multi_persona/review_contract.py"
PROPOSED = ROOT / "harness/memory/source_reviews/job_03b52a4d08c3494c895f1380c78b12dd/proposed.py"
BACKUP = ROOT / "harness/backups/review_contract_proposal_20261103/review_contract.py"


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    if BACKUP.exists():
        raise FileExistsError(f"backup already exists: {BACKUP}")  # 첫 원본 보호
    py_compile.compile(str(PROPOSED), doraise=True)  # 문법 오류면 여기서 중단
    BACKUP.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(TARGET, BACKUP)
    before = _sha(TARGET)
    shutil.copyfile(PROPOSED, TARGET)  # 권한 등 메타데이터는 기존 파일 유지
    print(json.dumps({"backup": str(BACKUP.relative_to(ROOT)), "sha256_before": before,
                      "sha256_after": _sha(TARGET), "matches_proposal": _sha(TARGET) == _sha(PROPOSED)},
                     ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()

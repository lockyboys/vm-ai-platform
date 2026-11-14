"""haness->harness 이동 충돌 파일 비교 + 최근 다른 세션 흔적 조사(읽기 전용, 2026-11-02).

목적: 1) 충돌 파일 두 개의 해시·크기·수정 시각·차이를 비교한다.
      2) 최근 60분 안에 바뀐 저장소 파일을 시각순으로 보여 활동 중인 세션을 추정한다.
아무 파일도 쓰지 않는다.
"""
import difflib
import hashlib
import json
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path

import config  # 루트 공통 설정(일반 지침 4)

ROOT = Path(config.PROJECT_ROOT)
KST = timezone(timedelta(hours=9))
NAME = "tests/test_autodiscover_self_repair_error_detail.py"
SKIP = {".git", "venv", "__pycache__", "node_modules", ".pytest_cache"}


def _info(path: Path) -> dict:
    data = path.read_bytes()
    return {"path": str(path.relative_to(ROOT)), "bytes": len(data),
            "sha256": hashlib.sha256(data).hexdigest(),
            "mtime_kst": datetime.fromtimestamp(path.stat().st_mtime, KST).strftime("%Y-%m-%d %H:%M:%S")}


def main() -> None:
    old, new = ROOT / "harness" / NAME, ROOT / "harness" / NAME
    diff = list(difflib.unified_diff(old.read_text(encoding="utf-8").splitlines(),
                                     new.read_text(encoding="utf-8").splitlines(),
                                     "harness/" + NAME, "harness/" + NAME, lineterm="", n=1))
    cutoff = time.time() - 3600
    recent = []
    for path in ROOT.rglob("*"):
        if any(p in SKIP for p in path.relative_to(ROOT).parts) or not path.is_file():
            continue
        if path.stat().st_mtime >= cutoff:
            recent.append((path.stat().st_mtime, str(path.relative_to(ROOT))))
    recent.sort()
    print(json.dumps({
        "haness_file": _info(old), "harness_file": _info(new), "identical": diff == [],
        "diff_head": diff[:60],
        "recent_changes_kst": [f"{datetime.fromtimestamp(t, KST).strftime('%H:%M:%S')} {p}" for t, p in recent[-60:]],
    }, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()

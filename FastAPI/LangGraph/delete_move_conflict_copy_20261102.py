"""이동 충돌로 이름을 바꿔 둔 중복 사본 삭제 (2026-11-02, LuckyBoys 승인).

대상: harness/tests/test_autodiscover_self_repair_error_detail_copy_20261102.py (미추적 파일)
근거: 이동된 원본 harness/tests/test_autodiscover_self_repair_error_detail.py 와 내용이 같다.
      (두 파일 모두 이동 때 haness->harness 참조가 똑같이 고쳐져 처음 해시 f2a0474d와는 달라졌다.)
      source_delete 도구는 git 추적 파일만 지울 수 있어 이 스크립트로 지운다.
안전: 두 파일 sha256이 서로 같을 때만 사본을 지운다. 원본은 건드리지 않는다.
"""
import hashlib
import json
from pathlib import Path

import config  # 루트 공통 설정(일반 지침 4)

ROOT = Path(config.PROJECT_ROOT)
ORIGINAL = ROOT / "harness/tests/test_autodiscover_self_repair_error_detail.py"
COPY = ORIGINAL.with_name("test_autodiscover_self_repair_error_detail_copy_20261102.py")


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    if _sha(ORIGINAL) != _sha(COPY):
        raise RuntimeError("원본과 사본 내용이 달라 삭제하지 않음")
    COPY.unlink()
    print(json.dumps({"deleted": str(COPY.relative_to(ROOT)), "copy_exists_after": COPY.exists(),
                      "original_kept": str(ORIGINAL.relative_to(ROOT)), "original_sha256": _sha(ORIGINAL)},
                     ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()

"""haness->harness 이동 충돌 파일 이름 변경 (2026-11-02, LuckyBoys 지시: "이름을 바꿔").

대상: harness/tests/test_autodiscover_self_repair_error_detail.py (02:26 생성, 미추적)
      haness 쪽 같은 이름 파일과 sha256이 완전히 같다(f2a0474d...). 내용 손실 없이 이름만 바꾼다.
새 이름: test_autodiscover_self_repair_error_detail_copy_20261102.py
안전: 새 이름이 이미 있거나 해시가 달라졌으면 아무것도 하지 않고 중단한다.
"""
import hashlib
import json
from pathlib import Path

import config  # 루트 공통 설정(일반 지침 4)

ROOT = Path(config.PROJECT_ROOT)
SOURCE = ROOT / "harness/tests/test_autodiscover_self_repair_error_detail.py"
TARGET = SOURCE.with_name("test_autodiscover_self_repair_error_detail_copy_20261102.py")
EXPECTED = "f2a0474d83629dde6d4b5c5e5aa4e9106207d4b08efb88630a1d964ed3715a12"


def main() -> None:
    digest = hashlib.sha256(SOURCE.read_bytes()).hexdigest()
    if digest != EXPECTED:
        raise RuntimeError(f"비교 이후 내용이 바뀌어 중단: {digest}")
    if TARGET.exists():
        raise FileExistsError(f"새 이름이 이미 있음: {TARGET}")
    SOURCE.rename(TARGET)  # 같은 폴더 안 이름 변경(내용 그대로)
    print(json.dumps({"renamed_from": str(SOURCE.relative_to(ROOT)), "renamed_to": str(TARGET.relative_to(ROOT)),
                      "sha256": hashlib.sha256(TARGET.read_bytes()).hexdigest(),
                      "source_exists_after": SOURCE.exists()}, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()

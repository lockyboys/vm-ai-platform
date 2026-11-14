"""페르소나 references 고정 sha256 갱신 (2026-11-03, LuckyBoys 지시 "고정값 갱신").

이유: 스킬 지침 haness->harness 변경 후 harness/personas/references/*.md 13개가 다시 동기화되어
      test_persona_repair_chain.py의 ORIGINAL_SHA256 고정값과 달라졌다.
동작: 테스트 파일의 각 '"<name>.md": "<old>"' 줄에서 old 해시를 현재 파일 해시로만 바꾼다(다른 줄 변경 없음).
"""
import hashlib
import json
import re
from pathlib import Path

import config  # 루트 공통 설정(일반 지침 4)

ROOT = Path(config.PROJECT_ROOT)
TEST = ROOT / "harness/tests/test_persona_repair_chain.py"
PERSONA_DIR = ROOT / "harness/personas/references"


def main() -> None:
    text = TEST.read_text(encoding="utf-8")
    changed = {}

    def _swap(match: re.Match) -> str:
        name, old = match.group(1), match.group(2)
        new = hashlib.sha256((PERSONA_DIR / name).read_bytes()).hexdigest()
        if new != old:
            changed[name] = {"old": old[:12], "new": new[:12]}
        return f'"{name}": "{new}"'

    text = re.sub(r'"([a-z_]+\.md)": "([0-9a-f]{64})"', _swap, text)
    TEST.write_text(text, encoding="utf-8")
    print(json.dumps({"updated": len(changed), "files": changed}, ensure_ascii=False))


if __name__ == "__main__":
    main()

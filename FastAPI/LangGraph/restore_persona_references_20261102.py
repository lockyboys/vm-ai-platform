"""이동 중 바뀐 페르소나 references 원문 사본을 원래 내용으로 되돌리는 1회성 스크립트 (2026-11-02).

이유: harness/personas/references/*.md 와 outputs/sps-orchestrator/references/*.md 는
      Claude 스킬 references의 "원문 그대로" 사본이다(test_persona_repair_chain.py가 sha256으로 고정).
      이동 스크립트가 본문의 "haness 폴더"를 바꿔 원문 계약이 깨졌다. 지침 10번 문구 변경은
      스킬 원본을 먼저 고친 뒤 동기화해야 하므로, 사본은 원문으로 되돌린다.
동작: 이동 매니페스트의 rewrites 중 해당 경로만 골라 백업 원본을 복사하고, sha256이 이동 전 값과 같은지 확인한다.
"""
import hashlib
import json
import shutil
from pathlib import Path

import config  # 루트 공통 설정(일반 지침 4)

ROOT = Path(config.PROJECT_ROOT)
MANIFEST = ROOT / "harness/memory/migrations/haness_to_harness_20261102.json"
BACKUP = ROOT / "harness/backups/haness_to_harness_20261102/originals"
TARGET_DIRS = ("harness/personas/references/", "outputs/sps-orchestrator/references/")


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    rewrites = json.loads(MANIFEST.read_text(encoding="utf-8"))["rewrites"]
    restored = []
    for item in rewrites:
        if not item["final_path"].startswith(TARGET_DIRS) or not item["final_path"].endswith(".md"):
            continue
        source = BACKUP / item["path"]          # 이동 전 경로 기준으로 저장된 원본
        target = ROOT / item["final_path"]      # 이동 후 실제 위치
        shutil.copy2(source, target)
        restored.append({"path": item["final_path"], "match_original": _sha(target) == item["sha256_before"]})
    print(json.dumps({"restored": len(restored), "all_match": all(r["match_original"] for r in restored),
                      "files": restored}, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()

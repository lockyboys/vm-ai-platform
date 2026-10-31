"""SPS ORCHESTRATOR 페르소나 원문 프롬프트를 haness/personas/references로 복사한다(내용 변경 없음).

근거: 2026-10-25 LuckyBoys "프롬프트는 제가 쓴 거랑 똑같이" + 일반 지침 10(output 소스는 haness로).
입력(stdin JSON): {"dry_run": true, "expected_sha256": {"partner.md": "<스킬 원본 sha256>", ...}}
- 원본: outputs/sps-orchestrator/references/<이름>.md (원본은 그대로 둔다 — 지침 7 원본 보존)
- 원본 sha256이 expected와 다르면 아무것도 복사하지 않고 오류로 보고한다(다른 프롬프트가 실리는 것 방지).
- 대상 파일이 이미 있고 내용이 다르면 덮어쓰지 않고 오류로 보고한다.
"""
from __future__ import annotations

import hashlib
import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SOURCE_DIR = ROOT / "outputs/sps-orchestrator/references"
TARGET_DIR = ROOT / "haness/personas/references"


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    request = json.loads(sys.stdin.read() or "{}")
    expected = request.get("expected_sha256") or {}
    if not isinstance(expected, dict) or not expected:
        raise ValueError("expected_sha256 must be a non-empty object")
    plan, errors = [], []
    for name, want in expected.items():
        if "/" in name or not name.endswith(".md"):
            raise ValueError(f"invalid persona file name: {name}")
        source, target = SOURCE_DIR / name, TARGET_DIR / name
        item = {"name": name, "source_sha256": _sha(source) if source.is_file() else None,
                "target_exists": target.is_file()}
        item["source_matches"] = item["source_sha256"] == want
        item["target_same"] = target.is_file() and _sha(target) == want
        if not item["source_matches"] or (item["target_exists"] and not item["target_same"]):
            errors.append(name)
        plan.append(item)
    result = {"dry_run": bool(request.get("dry_run", True)), "plan": plan, "errors": errors, "copied": []}
    if not result["dry_run"] and not errors:
        TARGET_DIR.mkdir(parents=True, exist_ok=True)
        for item in plan:
            if not item["target_same"]:
                shutil.copy2(SOURCE_DIR / item["name"], TARGET_DIR / item["name"])
                result["copied"].append(item["name"])
        result["verified"] = {i["name"]: _sha(TARGET_DIR / i["name"]) == expected[i["name"]] for i in plan}
    print(json.dumps(result, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()

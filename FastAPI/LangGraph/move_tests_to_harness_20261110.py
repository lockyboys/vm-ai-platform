"""tests/harness/mcp/* 와 tests/test_review_output_contract.py 를 harness/tests/ 로 옮기는 스크립트 (2026-11-10, LuckyBoys 지시).

기본은 dry-run(계획만 출력). 같은 폴더의 *_execute.py 진입점으로 실행할 때만 실제 이동한다.
  - git 추적 파일은 git mv(이력 보존), 미추적 파일은 일반 이동.
  - harness/tests에 같은 이름이 있으면 덮어쓰지 않고 <이름>_mcp.py 로 바꿔 옮긴다(둘 다 보존).
  - 파일 안의 Path(__file__).parents[N] 은 폴더 깊이가 달라지므로(tests/harness/mcp=3단계 → harness/tests=2단계)
    프로젝트 루트를 가리키는 parents[3] → parents[2] 로만 고친다. 그 밖의 경로 표현은 목록으로 보고만 한다.
  - __pycache__ 는 옮기지 않는다.
"""
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

import config  # 루트 공통 설정(일반 지침 4)

ROOT = Path(config.PROJECT_ROOT)
DEST = ROOT / "harness/tests"
SOURCES = sorted(p for p in (ROOT / "tests/harness/mcp").glob("*") if p.is_file()) + [
    ROOT / "tests/test_review_output_contract.py"]


def _git(*args):
    return subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True, check=True).stdout


def plan():
    tracked = set(_git("ls-files", "-z", "--", "tests").split("\0")) - {""}
    moves = []
    for src in SOURCES:
        target = DEST / src.name
        if target.exists():
            target = DEST / (src.stem + "_mcp" + src.suffix)   # 이름 충돌: 둘 다 보존
        text = src.read_text(encoding="utf-8") if src.suffix == ".py" else ""
        depth_fix = src.parent == ROOT / "tests/harness/mcp" and "parents[3]" in text
        other_paths = sorted(set(re.findall(r"parents\[\d\]|tests/harness/mcp", text)) - {"parents[3]"}) \
            if src.suffix == ".py" else []
        moves.append({"from": str(src.relative_to(ROOT)), "to": str(target.relative_to(ROOT)),
                      "tracked": str(src.relative_to(ROOT)) in tracked,
                      "renamed_for_conflict": target.name != src.name,
                      "fix_parents3_to_2": depth_fix, "check_manually": other_paths})
    return moves


def execute(moves):
    for m in moves:
        if (ROOT / m["to"]).exists():
            raise FileExistsError(m["to"])
        if m["tracked"]:
            _git("mv", "--", m["from"], m["to"])
        else:
            shutil.move(str(ROOT / m["from"]), str(ROOT / m["to"]))
        if m["fix_parents3_to_2"]:
            path = ROOT / m["to"]
            path.write_text(path.read_text(encoding="utf-8").replace("parents[3]", "parents[2]"), encoding="utf-8")


def main():
    moves = plan()
    run = "--execute" in sys.argv[1:]
    if run:
        execute(moves)
    print(json.dumps({"mode": "execute" if run else "dry_run", "count": len(moves),
                      "conflict_renames": [m["to"] for m in moves if m["renamed_for_conflict"]],
                      "parents_fixed": [m["to"] for m in moves if m["fix_parents3_to_2"]],
                      "check_manually": {m["to"]: m["check_manually"] for m in moves if m["check_manually"]},
                      "moves": [f'{m["from"]} -> {m["to"]}' for m in moves]}, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()

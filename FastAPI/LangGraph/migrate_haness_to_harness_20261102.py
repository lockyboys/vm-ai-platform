"""haness/ -> harness/ 전체 이동 + 참조 경로 수정 스크립트 (2026-11-02, LuckyBoys 승인).

기본은 dry-run: 아무것도 옮기거나 쓰지 않고 계획(이동 수, 수정할 파일·치환 수)만 출력한다.
`--execute`를 줄 때만 실제로 실행한다.

실행 순서
  1) 사전 점검: harness/에 같은 상대 경로가 있으면(충돌) 즉시 중단한다.
  2) 참조 수정 대상 파일의 원본을 harness/backups/haness_to_harness_20261102/originals/에 복사한다(일반 지침 7).
  3) 파일 이동: git 추적 파일은 `git mv`(이력 보존), 미추적 파일은 shutil.move.
  4) 참조 수정: 코드·설정·문서의 `haness.` / `haness/` / "haness" / `haness 폴더` 만 정확히 바꾼다.
     - 백업(backups/, *_BACKUP_*), 실행 기록(harness/memory/, logs/, apps/**/results/)은 과거 증빙이라 수정하지 않는다.
     - sps-haness-mcp, sps_haness, test_..._haness_... 처럼 이름 일부인 경우는 단어 경계로 제외한다.
  5) 사후 검증: 수정한 .py 전부 py_compile, 남은 `haness.`/`haness/` 참조 목록 출력.
  6) 되돌리기용 매니페스트(이동·수정 목록, sha256)를 harness/memory/migrations/에 저장한다.
"""
import hashlib
import json
import py_compile
import re
import shutil
import subprocess
import sys
from pathlib import Path

import config  # 루트 공통 설정(일반 지침 4)

ROOT = Path(config.PROJECT_ROOT)
SRC, DST = ROOT / "haness", ROOT / "harness"
STAMP = "haness_to_harness_20261102"
BACKUP_DIR = DST / "backups" / STAMP / "originals"
MANIFEST = DST / "memory" / "migrations" / (STAMP + ".json")

SKIP_DIRS = {".git", "venv", "__pycache__", "node_modules", ".pytest_cache"}
TEXT_SUFFIXES = {".py", ".md", ".json", ".yaml", ".yml", ".toml", ".ini", ".cfg", ".sh",
                 ".service", ".conf", ".txt", ".js"}

# 치환 규칙: (설명, 정규식, 바꿀 문자열). 앞뒤 단어 경계로 이름 일부(sps_haness 등)는 건드리지 않는다.
RULES = [
    ("module", re.compile(r"(?<![\w-])haness\.(?=[A-Za-z_])"), "harness."),
    ("path", re.compile(r"(?<![\w-])haness(?=[/\\])"), "harness"),
    ("quoted", re.compile(r"(?<=[\"'])haness(?=[\"'])"), "harness"),
    ("folder_ko", re.compile(r"(?<![\w-])haness(`?) 폴더"), r"harness\1 폴더"),
]


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _is_record_or_backup(rel: str) -> bool:
    """과거 증빙(백업·실행 기록)이거나 이번 이동 도구 자신이면 True — 내용 수정 대상에서 제외한다."""
    # 이 스크립트와 사전 조사 스크립트는 'haness' 문자열을 규칙으로 담고 있어 고치면 안 된다.
    own_tools = {"FastAPI/LangGraph/migrate_haness_to_harness_20261102.py",
                 "FastAPI/LangGraph/inventory_haness_to_harness_20261102.py"}
    if rel in own_tools:
        return True
    return ("backups/" in rel or "BACKUP" in rel or rel.startswith(("harness/memory/", "logs/"))
            or ("/apps/" in rel and "/results/" in rel) or rel.startswith(f"{SRC.name}/memory/"))


def _walk(base: Path):
    for path in base.rglob("*"):
        if any(part in SKIP_DIRS for part in path.relative_to(ROOT).parts):
            continue
        if path.is_file() or path.is_symlink():
            yield path


def _git(*args: str) -> str:
    done = subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True, check=True)
    return done.stdout


def _rewrite(text: str):
    """규칙별 치환 결과와 횟수를 돌려준다."""
    counts = {}
    for name, pattern, repl in RULES:
        text, n = pattern.subn(repl, text)
        if n:
            counts[name] = n
    return text, counts


def plan():
    """이동 목록과 참조 수정 목록을 만든다(쓰기 없음)."""
    tracked = set(_git("ls-files", "-z", "--", "haness").split("\0")) - {""}
    moves = []
    for path in sorted(_walk(SRC)):
        rel = path.relative_to(SRC)
        moves.append({"from": str(path.relative_to(ROOT)), "to": str((DST / rel).relative_to(ROOT)),
                      "tracked": str(path.relative_to(ROOT)) in tracked})
    conflicts = [m["to"] for m in moves if (ROOT / m["to"]).exists()]

    rewrites = []
    for path in _walk(ROOT):
        rel = str(path.relative_to(ROOT))
        if path.suffix not in TEXT_SUFFIXES or _is_record_or_backup(rel) or path.is_symlink():
            continue
        if path.stat().st_size > 2_000_000:
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        if "haness" not in text:
            continue
        new_text, counts = _rewrite(text)
        if counts:
            # 이동 후 경로(haness/... -> harness/...)를 기록해 실행 단계에서 그 위치를 고친다.
            final = "harness/" + rel[len("haness/"):] if rel.startswith("haness/") else rel
            rewrites.append({"path": rel, "final_path": final, "counts": counts})
    return moves, conflicts, rewrites


def execute(moves, rewrites):
    """백업 -> 이동 -> 참조 수정 -> 검증 -> 매니페스트 저장."""
    # 2) 수정 대상 원본 백업(이동 전 위치 기준, 같은 상대 경로)
    for item in rewrites:
        src = ROOT / item["path"]
        dst = BACKUP_DIR / item["path"]
        if dst.exists():
            raise FileExistsError(f"backup already exists: {dst}")
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
        item["sha256_before"] = _sha256(src)

    # 3) 이동: 추적 파일은 git mv로 이력 보존, 미추적 파일은 일반 이동
    for move in moves:
        target = ROOT / move["to"]
        target.parent.mkdir(parents=True, exist_ok=True)
        if move["tracked"]:
            _git("mv", "-k", "--", move["from"], move["to"])
        if (ROOT / move["from"]).exists() or (ROOT / move["from"]).is_symlink():
            shutil.move(str(ROOT / move["from"]), str(target))
    # 빈 디렉터리 정리(파일이 남아 있으면 지우지 않는다)
    for directory in sorted((p for p in SRC.rglob("*") if p.is_dir()), key=lambda p: -len(p.parts)):
        if not any(directory.iterdir()):
            directory.rmdir()
    if SRC.exists() and not any(SRC.iterdir()):
        SRC.rmdir()

    # 4) 참조 수정(이동 후 위치에서)
    compile_errors = []
    for item in rewrites:
        path = ROOT / item["final_path"]
        new_text, _ = _rewrite(path.read_text(encoding="utf-8"))
        path.write_text(new_text, encoding="utf-8")
        item["sha256_after"] = _sha256(path)
        if path.suffix == ".py":
            try:
                py_compile.compile(str(path), doraise=True, cfile=None)
            except py_compile.PyCompileError as error:
                compile_errors.append(f"{item['final_path']}: {error.msg}")

    # 5) 남은 참조(코드 파일 기준)
    remaining = []
    for path in _walk(ROOT):
        rel = str(path.relative_to(ROOT))
        if path.suffix not in TEXT_SUFFIXES or _is_record_or_backup(rel) or path.is_symlink():
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        for rule_name, pattern, _ in RULES:
            if pattern.search(text):
                remaining.append(f"{rel} ({rule_name})")
    return compile_errors, remaining


def main() -> None:
    do_execute = "--execute" in sys.argv[1:]
    moves, conflicts, rewrites = plan()
    summary = {
        "mode": "execute" if do_execute else "dry_run",
        "moves": len(moves), "tracked_moves": sum(m["tracked"] for m in moves),
        "untracked_moves": sum(not m["tracked"] for m in moves),
        "conflicts": conflicts[:50],
        "rewrite_files": len(rewrites),
        "rewrite_counts": {name: sum(r["counts"].get(name, 0) for r in rewrites) for name, *_ in RULES},
        "rewrite_sample": [r["path"] for r in rewrites[:40]],
    }
    if conflicts:
        summary["stopped"] = "harness/에 같은 경로가 있어 중단"
        print(json.dumps(summary, ensure_ascii=False, indent=1))
        return
    if do_execute:
        compile_errors, remaining = execute(moves, rewrites)
        summary.update(compile_errors=compile_errors, remaining_references=remaining[:80],
                       remaining_count=len(remaining), manifest=str(MANIFEST.relative_to(ROOT)),
                       backup_dir=str(BACKUP_DIR.relative_to(ROOT)))
        MANIFEST.parent.mkdir(parents=True, exist_ok=True)
        MANIFEST.write_text(json.dumps({"summary": summary, "moves": moves, "rewrites": rewrites},
                                       ensure_ascii=False, indent=1), encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()

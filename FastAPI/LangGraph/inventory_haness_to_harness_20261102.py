"""haness/ -> harness/ 전체 이동 사전 조사(읽기 전용) 스크립트 (2026-11-02, LuckyBoys 승인).

목적: 이동 계획을 세우기 전에 실제 규모와 위험을 숫자로 확인한다.
  1) haness/ 아래 파일 수(백업·캐시 제외/포함 구분)
  2) harness/ 에 같은 상대 경로가 이미 있는 "충돌" 파일 목록
  3) 저장소 전체에서 'haness' 문자열을 참조하는 파일 수(코드/백업/기록 구분)
  4) systemd 유닛·드롭인에서 haness를 참조하는 줄
원칙: 아무 파일도 쓰거나 옮기지 않는다. 결과는 JSON으로 출력만 한다.
"""
import json
from collections import Counter
from pathlib import Path

import config  # 루트 공통 설정(일반 지침 4)

ROOT = Path(config.PROJECT_ROOT)
SRC, DST = ROOT / "haness", ROOT / "harness"
# 검색에서 제외할 디렉터리(가상환경·git·캐시)
SKIP_DIRS = {".git", "venv", "__pycache__", "node_modules", ".pytest_cache"}
TEXT_SUFFIXES = {".py", ".md", ".json", ".yaml", ".yml", ".toml", ".ini", ".cfg", ".sh",
                 ".service", ".conf", ".txt", ".js", ".env"}


def _walk(base: Path):
    """제외 디렉터리를 건너뛰며 파일만 돌려준다."""
    for path in base.rglob("*"):
        if any(part in SKIP_DIRS for part in path.relative_to(ROOT).parts):
            continue
        if path.is_file():
            yield path


def _category(rel: str) -> str:
    """참조 파일을 성격별로 분류한다(백업·실행 기록은 수정 대상에서 제외 후보)."""
    if "backups/" in rel or "_BACKUP_" in rel or "BACKUP" in rel:
        return "backup"
    if rel.startswith("harness/memory/") or rel.startswith("logs/"):
        return "record"
    return "code"


def main() -> None:
    src_files = list(_walk(SRC))
    non_backup = [p for p in src_files if "backups" not in p.relative_to(SRC).parts]
    conflicts = sorted(str(p.relative_to(SRC)) for p in non_backup if (DST / p.relative_to(SRC)).exists())

    refs = Counter()
    code_refs = []
    for path in _walk(ROOT):
        if path.suffix not in TEXT_SUFFIXES or path.stat().st_size > 2_000_000:
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        if "haness" not in text:
            continue
        rel = str(path.relative_to(ROOT))
        kind = _category(rel)
        refs[kind] += 1
        if kind == "code":
            code_refs.append({"path": rel, "count": text.count("haness")})

    unit_lines = []
    for unit_dir in (Path("/etc/systemd/system"),):
        for path in sorted(unit_dir.glob("sps*")):
            files = [path] if path.is_file() else sorted(path.glob("*.conf"))
            for f in files:
                try:
                    for no, line in enumerate(f.read_text(encoding="utf-8").splitlines(), 1):
                        if "haness" in line:
                            unit_lines.append(f"{f}:{no}: {line.strip()}")
                except OSError as error:
                    unit_lines.append(f"{f}: 읽기 실패 {error}")

    print(json.dumps({
        "haness_files_total": len(src_files),
        "haness_files_excluding_backups": len(non_backup),
        "conflicts_with_existing_harness": {"count": len(conflicts), "paths": conflicts[:80]},
        "reference_files_by_kind": dict(refs),
        "code_reference_files": sorted(code_refs, key=lambda r: -r["count"])[:60],
        "code_reference_files_count": len(code_refs),
        "systemd_lines": unit_lines,
    }, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()

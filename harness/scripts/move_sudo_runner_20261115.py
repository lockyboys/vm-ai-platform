"""common_function.py에 넣었던 run_allowed_sudo 블록을 빼고(common/sudo_runner.py로 옮김), config 주석을 고친다 (2026-11-15).

이유: common_function을 import하는 모든 스크립트가 sudo 승인을 요구하게 된 부작용 제거(LuckyBoys 승인 "빨리 해").
- common_function.py: "2026-11-15 (LuckyBoys 요청 \"sudo" 표시 블록부터 파일 끝까지 삭제(그 블록은 파일 맨 끝에 있음 — 확인 후 삭제)
- config.py: 주석의 "common.common_function.run_allowed_sudo" → "common.sudo_runner.run_allowed_sudo"
- sys.argv[1] == "--apply" 일 때만 반영, 원본은 <파일>.bak_20261115_sudomove 로 보존.
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
APPLY = len(sys.argv) > 1 and sys.argv[1] == "--apply"
BLOCK_START = ("\n\n# =============================================================================\n"
               "# 2026-11-15 (LuckyBoys 요청 \"sudo 실행하는 도구 만들자\"")
CONFIG_OLD = "common.common_function.run_allowed_sudo"
CONFIG_NEW = "common.sudo_runner.run_allowed_sudo"


def main() -> int:
    cf_path, cfg_path = ROOT / "common/common_function.py", ROOT / "config.py"
    cf, cfg = cf_path.read_text(encoding="utf-8"), cfg_path.read_text(encoding="utf-8")
    n_block, n_cfg = cf.count(BLOCK_START), cfg.count(CONFIG_OLD)
    cut = cf.find(BLOCK_START)
    tail = cf[cut:] if cut >= 0 else ""
    # 블록이 파일 끝에 있고, 그 뒤에 run_allowed_sudo 말고 다른 함수가 없는지 확인
    other_defs = [line for line in tail.splitlines() if line.startswith("def ") and "run_allowed_sudo" not in line]
    print(f"[검사] 블록 {n_block}회, 블록 뒤 다른 함수 {other_defs}, config 주석 {n_cfg}회")
    if n_block != 1 or other_defs or n_cfg != 1:
        print("[중단] 조건 불일치")
        return 1
    new_cf = cf[:cut].rstrip("\n") + "\n"
    new_cfg = cfg.replace(CONFIG_OLD, CONFIG_NEW)
    compile(new_cf, "common_function.py", "exec")
    compile(new_cfg, "config.py", "exec")
    if "run_allowed_sudo" in new_cf or '"sudo"' in new_cf:
        print("[중단] 삭제 후에도 sudo 흔적이 남음")
        return 1
    if not APPLY:
        print(f"[dry-run] 통과. common_function.py {len(cf.splitlines())}→{len(new_cf.splitlines())}줄")
        return 0
    for path, old, new in ((cf_path, cf, new_cf), (cfg_path, cfg, new_cfg)):
        backup = path.with_name(path.name + ".bak_20261115_sudomove")
        if not backup.exists():
            backup.write_text(old, encoding="utf-8")
        path.write_text(new, encoding="utf-8")
        print(f"[반영] {path.relative_to(ROOT)} (백업 {backup.name})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

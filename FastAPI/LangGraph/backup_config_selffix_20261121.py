"""config.py를 고치기 전에 그대로 복사해 둔다 (2026-11-21, 일회용, 일반 지침 7: 원본 보존).

다른 세션의 미커밋 변경도 들어 있어 Git HEAD만으로는 지금 상태를 되살릴 수 없기 때문이다.
이미 백업이 있으면 덮어쓰지 않는다(첫 원본 보존).
"""
import hashlib
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "config.py"
BACKUP = ROOT / "harness/backups/selffix_focus_salvage_20261121/config.py"

if BACKUP.exists():
    print(f"[건너뜀] 백업이 이미 있음: {BACKUP.relative_to(ROOT)}")
else:
    BACKUP.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(SOURCE, BACKUP)
    print(f"[백업] {BACKUP.relative_to(ROOT)}")
print("sha256", hashlib.sha256(BACKUP.read_bytes()).hexdigest())

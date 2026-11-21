"""config.py·multi_persona_tools.py를 Ollama 사전 점검 수정 전에 그대로 복사해 둔다 (2026-11-21, 일회용, 원본 보존).

두 파일 모두 다른 세션의 미커밋 변경(상황별 대응표 등)이 들어 있어 Git HEAD로는 지금 상태를 되살릴 수 없다.
이미 백업이 있으면 덮어쓰지 않는다.
"""
import hashlib
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
TARGETS = ["config.py", "harness/mcp/tools/multi_persona_tools.py", "common/common_function.py"]
DEST = ROOT / "harness/backups/selffix_ollama_preflight_20261121"

for name in TARGETS:
    backup = DEST / name
    if backup.exists():
        print(f"[건너뜀] {backup.relative_to(ROOT)}")
    else:
        backup.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROOT / name, backup)
        print(f"[백업] {backup.relative_to(ROOT)}")
    print("  sha256", hashlib.sha256(backup.read_bytes()).hexdigest())

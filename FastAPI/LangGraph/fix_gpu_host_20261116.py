"""config.py 의 GPU 서버(turing-enigma-ai) 기본 IP 한 줄만 바꾼다 (2026-11-16, 일회용, LuckyBoys 승인 ①).

AI 서버를 다시 켜면서 IP 가 34.64.134.46 → 8.230.3.46 으로 바뀌었다(LuckyBoys 제공 ssh 설정).
config 주석대로 SPS_GPU_SSH_HOST 하나만 바꾸면 ssh 대상과 Ollama 후보 주소가 함께 바뀐다.
- 인자 없으면 dry-run(검사만), sys.argv[1] == "--apply" 일 때만 백업 후 반영.
- 그 줄 외에는 건드리지 않는다(다른 세션의 미커밋 변경 보존).
"""
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CONFIG = ROOT / "config.py"
BACKUP = ROOT / "harness/backups/gpu_host_20261116/config.py"
OLD = '        "host": os.getenv("SPS_GPU_SSH_HOST", "34.64.134.46"),'
NEW = '        "host": os.getenv("SPS_GPU_SSH_HOST", "8.230.3.46"),   # 2026-11-16 AI 서버 재기동으로 IP 변경(이전 34.64.134.46)'
APPLY = len(sys.argv) > 1 and sys.argv[1] == "--apply"

text = CONFIG.read_text(encoding="utf-8")
count = text.count(OLD)
print(f"[검사] 바꿀 줄 발견 {count}번(1번이어야 함)")
if count != 1:
    raise SystemExit(1)
patched = text.replace(OLD, NEW, 1)
compile(patched, "config.py", "exec")          # 문법 검사
print("[검사] 문법 통과, 바뀌는 줄 1개")
if not APPLY:
    print("[dry-run] 반영하지 않았습니다.")
    raise SystemExit(0)
BACKUP.parent.mkdir(parents=True, exist_ok=True)
shutil.copy2(CONFIG, BACKUP)
CONFIG.write_text(patched, encoding="utf-8")
print(f"[반영] config.py 수정, 백업 {BACKUP.relative_to(ROOT)}")

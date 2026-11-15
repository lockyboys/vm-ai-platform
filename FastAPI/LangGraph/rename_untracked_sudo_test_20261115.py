"""아직 커밋 안 된(추적 안 됨) sudo 허용 목록 테스트 이름에서 날짜를 뺀다 (2026-11-15, LuckyBoys 결정: 계속 쓰는 테스트만).

source_rename은 추적 중인 파일만 바꿀 수 있어서, 이 파일 하나만 os.replace로 옮긴다.
새 이름이 이미 있으면 덮어쓰지 않고 멈춘다. 내용은 바꾸지 않는다(이동 전후 sha256 비교).
"""
import hashlib
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "harness/tests/test_common_sudo_allowlist_20261115.py"
DST = ROOT / "harness/tests/test_common_sudo_allowlist.py"

if DST.exists():
    raise SystemExit(f"[중단] 이미 있음: {DST.relative_to(ROOT)}")
before = hashlib.sha256(SRC.read_bytes()).hexdigest()
os.replace(SRC, DST)
after = hashlib.sha256(DST.read_bytes()).hexdigest()
print({"moved": True, "from": str(SRC.relative_to(ROOT)), "to": str(DST.relative_to(ROOT)), "content_preserved": before == after})

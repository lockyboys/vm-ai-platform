"""개선 후 재시험용: AI별 복사본을 원본으로 되돌린다 (2026-11-16, LuckyBoys "개선 진행").

- 대상: selffix_demo/memory_agent/<openai|claude|gemini|ollama>/LangGraph_MariaDB_Memory_Agent.py
- 원본과 다른 복사본(예: 1차 시험에서 반영된 gemini)은 덮기 전에 <파일>.round1_20261116.bak 으로 보존한다.
- 원본 파일은 읽기만 한다. 끝나면 모든 복사본이 원본과 sha256이 같은지 출력한다.
"""
import hashlib
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "FastAPI/LangGraph/LangGraph_MariaDB_Memory_Agent.py"
BASE = ROOT / "FastAPI/LangGraph/selffix_demo/memory_agent"
digest = hashlib.sha256(SOURCE.read_bytes()).hexdigest()

for name in ("openai", "claude", "gemini", "ollama"):
    target = BASE / name / SOURCE.name
    current = hashlib.sha256(target.read_bytes()).hexdigest() if target.exists() else None
    backup = None
    if current and current != digest:
        backup = target.with_name(target.name + ".round1_20261116.bak")
        if not backup.exists():
            shutil.copy2(target, backup)
    shutil.copy2(SOURCE, target)
    print({"copy": name, "was_modified": current != digest, "backup": backup.name if backup else None,
           "now_same_as_original": hashlib.sha256(target.read_bytes()).hexdigest() == digest})

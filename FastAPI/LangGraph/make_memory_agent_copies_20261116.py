"""LangGraph_MariaDB_Memory_Agent.py를 AI별 복사본 3개로 만든다 (2026-11-16, LuckyBoys 결정: 원본은 그대로, 복사본만 고침).

대상: FastAPI/LangGraph/selffix_demo/memory_agent/<openai|claude|ollama>/LangGraph_MariaDB_Memory_Agent.py
- 이미 복사본이 있으면 덮어쓰지 않고 멈춘다(이전 시험 결과 보존).
- 원본과 복사본의 sha256이 같은지 확인해 출력한다. 원본 파일은 읽기만 한다.
"""
import hashlib
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "FastAPI/LangGraph/LangGraph_MariaDB_Memory_Agent.py"
BASE = ROOT / "FastAPI/LangGraph/selffix_demo/memory_agent"
PROVIDERS = ("openai", "claude", "ollama")

digest = hashlib.sha256(SOURCE.read_bytes()).hexdigest()
targets = [BASE / name / SOURCE.name for name in PROVIDERS]
existing = [str(t.relative_to(ROOT)) for t in targets if t.exists()]
if existing:
    raise SystemExit(f"[중단] 이미 있음(덮어쓰지 않음): {existing}")
for target in targets:
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(SOURCE, target)
    same = hashlib.sha256(target.read_bytes()).hexdigest() == digest
    print({"copy": str(target.relative_to(ROOT)), "same_as_original": same})
print({"original_sha256": digest[:16]})

"""LangGraph_MariaDB_Memory_Agent.py를 Gemini용 복사본으로 만든다 (2026-11-16, LuckyBoys 요청 "구글은??").

대상: FastAPI/LangGraph/selffix_demo/memory_agent/gemini/LangGraph_MariaDB_Memory_Agent.py
이미 있으면 덮어쓰지 않고 멈춘다. 원본은 읽기만 하고, 복사 후 sha256이 같은지 확인한다.
"""
import hashlib
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "FastAPI/LangGraph/LangGraph_MariaDB_Memory_Agent.py"
TARGET = ROOT / "FastAPI/LangGraph/selffix_demo/memory_agent/gemini" / SOURCE.name

if TARGET.exists():
    raise SystemExit(f"[중단] 이미 있음: {TARGET.relative_to(ROOT)}")
TARGET.parent.mkdir(parents=True, exist_ok=True)
shutil.copy2(SOURCE, TARGET)
same = hashlib.sha256(TARGET.read_bytes()).hexdigest() == hashlib.sha256(SOURCE.read_bytes()).hexdigest()
print({"copy": str(TARGET.relative_to(ROOT)), "same_as_original": same})

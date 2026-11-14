"""Anthropic(Claude) API 키·라이브러리 존재 확인 — 읽기 전용 (2026-11-01, LuckyBoys: Claude로 블라인드 리뷰 테스트).

키 값은 절대 출력하지 않는다(있음/없음·길이만). API 호출 없음.
.env 는 블라인드 워커와 같은 방식(load_dotenv, override=False)으로 읽는다.
"""
import importlib.util
import json
import os

from dotenv import load_dotenv

import config  # 루트 공통 설정(일반 지침 4)

load_dotenv(os.path.join(config.PROJECT_ROOT, ".env"), override=False)
# 2026-11-01: LuckyBoys "OPENAI_API_KEY로 등록" → 이름이 아니라 키 형식(접두어)으로 Anthropic 키인지 판별
names = ("ANTHROPIC_API_KEY", "CLAUDE_API_KEY", "OPENAI_API_KEY")
out = {name: {"present": bool(os.getenv(name, "").strip()), "length": len(os.getenv(name, "").strip())} for name in names}
for name in names:
    value = os.getenv(name, "").strip()
    out[name]["looks_anthropic"] = value.startswith("sk-ant-")  # Anthropic 키 접두어(값 자체는 출력 안 함)
# 호출에 쓸 라이브러리 설치 여부(설치되지 않았으면 이후 단계에서 설치 승인 필요)
out["anthropic_pkg"] = importlib.util.find_spec("anthropic") is not None
out["langchain_anthropic_pkg"] = importlib.util.find_spec("langchain_anthropic") is not None
print(json.dumps(out, ensure_ascii=False))

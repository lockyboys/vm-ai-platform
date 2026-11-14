"""PARTNER 모델 공급자별 사용 가능 여부 점검 (2026-11-14, LuckyBoys: 크레딧 남아 있는 AI로 진행).

배경: 메리츠 자기 수리가 Gemini 402(선불 크레딧 소진)로 실패. 남은 크레딧이 있는 공급자를 고르기 위해
      공용 팩토리(common/llm_provider.create_chat_model)로 공급자마다 아주 짧은 호출 1회를 해 본다.
비용: 공급자당 입력·출력 수십 토큰 수준(최소). 키·모델 이름 원문은 출력하지 않는다(모델은 설정 유무만).
출력: {provider: {"ok": bool, "error": 오류 종류와 앞부분 200자}} 와 환경변수 유무.
실행: python FastAPI/LangGraph/probe_partner_providers_20261114.py
"""
import json
import os
import sys
import time
from pathlib import Path

import config  # 루트 공통 설정(일반 지침 4)

sys.path.insert(0, str(Path(config.PROJECT_ROOT)))
from common import llm_provider  # noqa: E402  PARTNER 와 같은 공용 팩토리

PROVIDERS = ("gemini", "openai", "claude", "ollama")
ENV_FLAGS = ("GEMINI_API_KEY", "GOOGLE_API_KEY", "OPENAI_API_KEY", "OPENAI_MODEL",
             "ANTHROPIC_API_KEY", "ANTHROPIC_MODEL", "SPS_SOURCE_PARTNER_MODEL_PROVIDER")


def probe(provider: str) -> dict:
    """공급자 하나: 모델 생성 → '1+1' 짧은 질문 1회. 실패는 오류 종류로 돌려준다(숨기지 않음)."""
    started = time.monotonic()
    try:
        model = llm_provider.create_chat_model(provider, temperature=0)
        reply = model.invoke("1+1=? 숫자만 답해.")
        text = str(getattr(reply, "content", reply))[:20]
        return {"ok": True, "reply_head": text, "seconds": round(time.monotonic() - started, 1)}
    except Exception as error:  # noqa: BLE001 - 어떤 공급자가 왜 안 되는지 그대로 보고
        return {"ok": False, "error": f"{type(error).__name__}: {str(error)[:200]}",
                "seconds": round(time.monotonic() - started, 1)}


def main() -> int:
    report = {"env": {name: ("있음" if os.getenv(name) else "없음") for name in ENV_FLAGS},
              "results": {provider: probe(provider) for provider in PROVIDERS}}
    print(json.dumps(report, ensure_ascii=False, indent=1))
    return 0


if __name__ == "__main__":
    sys.exit(main())

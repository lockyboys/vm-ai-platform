"""LLM 공급자별 LangChain 라이브러리 설치 여부와 API 키 '이름'만 확인 (2026-11-10, 읽기 전용).

키 값은 절대 출력하지 않는다(있음/없음만). 패키지는 import하지 않고 find_spec으로만 확인한다.
"""
import importlib.util
import json
import os

from dotenv import dotenv_values

import config  # 루트 공통 설정(일반 지침 4)

PACKAGES = ["langchain_google_genai", "langchain_openai", "langchain_anthropic", "langchain_ollama"]
KEYS = ["GEMINI_API_KEY", "GOOGLE_API_KEY", "OPENAI_API_KEY", "ANTHROPIC_API_KEY"]
env_file = dotenv_values(str(config.PROJECT_ROOT) + "/.env")  # .env의 키 이름 존재 여부만 사용
print(json.dumps({
    "packages": {name: importlib.util.find_spec(name) is not None for name in PACKAGES},
    "keys_present": {k: bool((os.getenv(k) or env_file.get(k) or "").strip()) for k in KEYS},
}, ensure_ascii=False))

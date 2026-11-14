"""OpenAI 사용 가능 모델 목록 조회 — 읽기 전용 (2026-11-01, LuckyBoys: GPT를 블라인드 리뷰 검토자로 테스트).

동작: GET https://api.openai.com/v1/models 1회(생성 호출 아님 → 토큰 요금 없음).
키는 .env OPENAI_API_KEY 에서 읽고 절대 출력하지 않는다. 출력: 채팅용으로 보이는 모델 id 목록 + 라이브러리 설치 여부.
"""
import importlib.util
import json
import os
import urllib.error
import urllib.request

from dotenv import load_dotenv

import config  # 루트 공통 설정(일반 지침 4)

load_dotenv(os.path.join(config.PROJECT_ROOT, ".env"), override=False)
key = os.getenv("OPENAI_API_KEY", "").strip()
if not key:
    raise SystemExit("OPENAI_API_KEY absent")  # 키가 없으면 호출하지 않고 종료

out = {"openai_pkg": importlib.util.find_spec("openai") is not None,
       "langchain_openai_pkg": importlib.util.find_spec("langchain_openai") is not None}
req = urllib.request.Request("https://api.openai.com/v1/models", headers={"Authorization": f"Bearer {key}"})
try:
    with urllib.request.urlopen(req, timeout=20) as response:  # 프록시 설정은 환경 기본값을 따른다
        ids = sorted(m.get("id", "") for m in json.load(response).get("data", []))
    # 채팅·추론 모델로 보이는 것만(임베딩·음성·이미지 등 제외) — 이름 규칙 기반 근사 필터
    skip = ("embedding", "whisper", "tts", "dall-e", "audio", "realtime", "moderation", "image", "transcribe", "search")
    out["chat_models"] = [i for i in ids if i.startswith(("gpt", "o1", "o3", "o4", "o5", "chatgpt")) and not any(s in i for s in skip)]
    out["total_models"] = len(ids)
except urllib.error.HTTPError as error:  # 401(키 무효)·403(권한) 등은 코드와 짧은 본문만 기록
    out["error"] = f"HTTP {error.code}: {error.read().decode(errors='replace')[:300]}"
except Exception as error:  # 네트워크 차단 등
    out["error"] = f"{type(error).__name__}: {error}"
print(json.dumps(out, ensure_ascii=False))

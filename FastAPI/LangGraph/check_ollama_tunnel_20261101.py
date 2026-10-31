"""노트북 역방향 터널(127.0.0.1:11435) 연결만 읽기 전용으로 확인한다 (2026-11-01).

이유: 실행 도구 환경에 잘못된 OLLAMA_BASE_URL(34.64.134.46)이 남아 자동 선택이 멈추므로,
      그 값을 거치지 않고 config 후보 목록의 노트북 터널 주소만 직접 확인한다.
동작: 후보 중 :11435 주소에 GET /api/version 1회(common_function._probe_ollama_version, 읽기 전용).
"""
import json

import config  # 루트 공통 설정(일반 지침 4)
from common.common_function import _probe_ollama_version

# 하드코딩하지 않고 config 후보 목록에서 노트북 터널(:11435) 주소를 고른다.
tunnel = next(url for url in config.SPS_SOURCE_PARTNER_OLLAMA_CANDIDATES if url.endswith(":11435"))
try:
    _probe_ollama_version(tunnel, config.SPS_SOURCE_PARTNER_OLLAMA_PROBE_TIMEOUT_SECONDS)
    print(json.dumps({"url": tunnel, "ok": True}))
except Exception as error:  # 실패도 그대로 증빙
    print(json.dumps({"url": tunnel, "ok": False, "error": f"{type(error).__name__}: {error}"}))

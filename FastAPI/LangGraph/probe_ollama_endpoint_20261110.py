"""지금 자동 선택되면 어느 Ollama 주소가 쓰일지만 확인 (2026-11-10, 읽기 전용, LLM 생성 호출 없음).

GPU 서버 → 노트북 터널 → 개발 서버 순서로 /api/version만 확인한다(common_function.resolve_ollama_base_url).
"""
import json

import config  # 루트 공통 설정(일반 지침 4)
from common.common_function import resolve_ollama_base_url

result = resolve_ollama_base_url(config.SPS_SOURCE_PARTNER_OLLAMA_BASE_URL,
                                 config.SPS_SOURCE_PARTNER_OLLAMA_CANDIDATES,
                                 config.SPS_SOURCE_PARTNER_OLLAMA_PROBE_TIMEOUT_SECONDS)
print(json.dumps(result, ensure_ascii=False, indent=1, default=str))

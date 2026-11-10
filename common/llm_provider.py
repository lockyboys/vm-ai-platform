"""LLM 공급자(Gemini·ChatGPT·Claude·Ollama)를 같은 LangChain 채팅 모델로 만들어 주는 공용 팩토리 (2026-11-10).

목적
    스스로 고치는 리뷰 앱(multi_persona_agent_gemini.py 등)은 LangChain 채팅 모델 하나만 쓴다
    (invoke / bind_tools / usage_metadata). 공급자마다 다른 것은 "클래스·키·모델 이름"뿐이므로
    그 차이를 이 파일 한 곳에 모아, 어떤 공급자를 골라도 나머지 그래프 코드는 바뀌지 않게 한다.

설정(하드코딩 금지, 루트 config.py — 일반 지침 4)
    config.MULTI_PERSONA_LLM_PROVIDERS = {
        "<이름>": {"module": "<패키지>", "class": "<클래스>",
                  "model_env": "<모델 환경변수>", "default_model": "<기본 모델 또는 빈 문자열>",
                  "key_envs": ["<키 환경변수>", ...], "key_param": "<생성자 키 인자 이름 또는 빈 문자열>"},
    }

주의
    - API 키 값은 로그·예외 메시지에 넣지 않는다(환경변수 이름만 안내).
    - 패키지가 없거나(예: langchain_anthropic 미설치) 키가 없으면 명확한 오류로 즉시 실패한다.
    - Ollama는 키가 없고, 주소는 common_function.resolve_ollama_base_url()로 자동 선택한다.
"""
from __future__ import annotations

import importlib
import os

import config as project_config


def available_providers() -> list[str]:
    """설정에 등록된 공급자 이름 목록."""
    return sorted(project_config.MULTI_PERSONA_LLM_PROVIDERS)


def create_chat_model(provider: str, temperature: float = 0.2, max_retries: int = 2):
    """공급자 이름으로 LangChain 채팅 모델을 만든다.

    잘못된 입력(미등록 공급자, 패키지 미설치, 키·모델 미설정)은 ValueError로 거부한다.
    """
    settings = project_config.MULTI_PERSONA_LLM_PROVIDERS.get(provider) if isinstance(provider, str) else None
    if settings is None:
        raise ValueError("provider must be one of: " + ", ".join(available_providers()))
    try:
        module = importlib.import_module(settings["module"])
    except ImportError as error:
        raise ValueError(f"{provider}: package {settings['module']} is not installed") from error
    model_class = getattr(module, settings["class"])

    model = os.getenv(settings["model_env"], "").strip() or settings["default_model"]
    if not model and provider == "ollama":
        # 2026-11-01 튜닝 값: source_partner와 같은 Ollama 모델(gemma4:e4b, OLLAMA_MODEL로 변경 가능)
        model = project_config.SPS_SOURCE_PARTNER_OLLAMA_MODEL
    if not model:
        raise ValueError(f"{provider}: set the {settings['model_env']} environment variable")
    kwargs = {"model": model}
    # 2026-11-10: 일부 모델은 temperature 인자를 받지 않는다
    # (claude-opus-5-5: 400 "temperature: Extra inputs are not permitted", job 0b2d2ebe).
    # config의 supports_temperature가 False이면 넘기지 않는다(기본 True).
    if settings.get("supports_temperature", True):
        kwargs["temperature"] = temperature

    if settings["key_envs"]:
        api_key = next((os.getenv(name, "").strip() for name in settings["key_envs"]
                        if os.getenv(name, "").strip()), "")
        if not api_key:
            raise ValueError(f"{provider}: none of {', '.join(settings['key_envs'])} is set")
        from pydantic import SecretStr  # LangChain 모델들이 키를 SecretStr로 받는다(로그 노출 방지)
        kwargs[settings["key_param"]] = SecretStr(api_key)
        kwargs["max_retries"] = max_retries
    if provider == "ollama":
        # ---- 2026-11-01 Ollama 튜닝을 공용 모듈에 반영 (2026-11-10, LuckyBoys 지시) ----
        # ① 주소 자동 선택: GPU 서버(SPS_GPU_SSH_HOST:11434) → 노트북 터널 127.0.0.1:11435 → 개발 서버 127.0.0.1:11434.
        #    개발 서버는 CPU 전용이라 느리다(11-01 실측 3.6~6.5 tok/s, 11-10 리뷰 3590초 시간 초과).
        # ② 응답 대기: SPS_SOURCE_PARTNER_OLLAMA_TIMEOUT_SECONDS (모델 로딩 13~24초 + 생성 시간).
        # ③ 컨텍스트: OLLAMA_CONTEXT_LENGTH(없으면 MULTI_PERSONA_OLLAMA_CONTEXT, 기본 8192).
        #    노트북 RTX 3060 6GB는 262144에서 GPU를 못 쓰고 8192에서 100% GPU였다(11-01 확인).
        # 2026-11-10 버그 수정: 이 함수는 (고정 주소, 후보, 확인 대기초)를 받아 {"base_url": ...}를 돌려준다.
        # 이전 코드는 인자 없이 불러 실제 실행 시 TypeError가 났다(테스트가 대역 함수로 가려 놓쳤음).
        from common.common_function import resolve_ollama_base_url
        pinned = os.getenv("OLLAMA_BASE_URL", "").strip() or project_config.SPS_SOURCE_PARTNER_OLLAMA_BASE_URL
        kwargs["base_url"] = resolve_ollama_base_url(
            pinned,
            project_config.SPS_SOURCE_PARTNER_OLLAMA_CANDIDATES,
            project_config.SPS_SOURCE_PARTNER_OLLAMA_PROBE_TIMEOUT_SECONDS,
        )["base_url"]
        kwargs["client_kwargs"] = {"timeout": float(project_config.SPS_SOURCE_PARTNER_OLLAMA_TIMEOUT_SECONDS)}
        kwargs["num_ctx"] = int(os.getenv("OLLAMA_CONTEXT_LENGTH", "").strip()
                                or getattr(project_config, "MULTI_PERSONA_OLLAMA_CONTEXT", 8192))
        # GPU 서버에서 reasoning=False로 숨은 추론 출력을 끄는 설정(configure_gpu_review_reasoning.py)도 따른다.
        reasoning = getattr(project_config, "MULTI_PERSONA_OLLAMA_REASONING", None)
        if reasoning is not None:
            kwargs["reasoning"] = reasoning
    return model_class(**kwargs)

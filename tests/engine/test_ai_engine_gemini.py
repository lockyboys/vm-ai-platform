from unittest.mock import Mock, patch

import pytest

from engine.intelligence.ai_engine import AIEngine


def test_gemini_api_key_has_priority(monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "gemini-key")
    monkeypatch.setenv("GOOGLE_API_KEY", "google-key")
    monkeypatch.setenv("GEMINI_MODEL", "configured-model")

    engine = AIEngine()

    assert engine.google_api_key == "gemini-key"
    assert engine.is_ready() is True


def test_generate_content_uses_header_without_exposing_key_in_url():
    response = Mock()
    response.raise_for_status.return_value = None
    response.json.return_value = {
        "candidates": [{"content": {"parts": [{"text": "Gemini ready"}]}}]
    }
    engine = AIEngine(
        api_key="secret-key",
        model_name="configured-model",
        timeout_seconds=5,
    )

    with patch(
        "engine.intelligence.ai_engine.requests.post",
        return_value=response,
    ) as post:
        result = engine.generate_content("연결 확인")

    assert result == "Gemini ready"
    request_url = post.call_args.args[0]
    assert "secret-key" not in request_url
    assert post.call_args.kwargs["headers"]["x-goog-api-key"] == "secret-key"


def test_generate_content_requires_model():
    engine = AIEngine(api_key="secret-key", model_name=None)
    engine.model_name = None

    with pytest.raises(RuntimeError, match="GEMINI_MODEL"):
        engine.generate_content("연결 확인")

import os

import requests
from dotenv import load_dotenv


class AIEngine:
    """
    SPS AI Engine

    GEMINI_API_KEY를 우선 사용하고 GOOGLE_API_KEY는 호환용으로 읽는다.
    API Key는 절대 로그에 출력하지 않는다.
    """

    GEMINI_API_BASE_URL = "https://generativelanguage.googleapis.com/v1beta"

    def __init__(self, api_key=None, model_name=None, timeout_seconds=30):
        load_dotenv()
        self.google_api_key = (
            api_key
            or os.getenv("GEMINI_API_KEY")
            or os.getenv("GOOGLE_API_KEY")
        )
        self.model_name = model_name or os.getenv("GEMINI_MODEL")
        self.timeout_seconds = timeout_seconds

    def is_ready(self):
        return bool(self.google_api_key and self.model_name)

    def generate_content(self, prompt):
        if not self.google_api_key:
            raise RuntimeError(
                "GEMINI_API_KEY 또는 GOOGLE_API_KEY 환경변수가 필요합니다."
            )
        if not self.model_name:
            raise RuntimeError("GEMINI_MODEL 환경변수가 필요합니다.")
        if not isinstance(prompt, str) or not prompt.strip():
            raise ValueError("Gemini prompt는 비어 있지 않은 문자열이어야 합니다.")

        response = requests.post(
            f"{self.GEMINI_API_BASE_URL}/models/{self.model_name}:generateContent",
            headers={
                "Content-Type": "application/json",
                "x-goog-api-key": self.google_api_key,
            },
            json={"contents": [{"parts": [{"text": prompt}]}]},
            timeout=self.timeout_seconds,
        )
        try:
            response.raise_for_status()
        except requests.HTTPError as exc:
            raise RuntimeError(
                f"Gemini API 요청 실패: HTTP {response.status_code}"
            ) from exc

        payload = response.json()
        candidates = payload.get("candidates") or []
        if not candidates:
            raise RuntimeError("Gemini API 응답에 생성 후보가 없습니다.")

        parts = candidates[0].get("content", {}).get("parts", [])
        text = "".join(part.get("text", "") for part in parts).strip()
        if not text:
            raise RuntimeError("Gemini API 응답에 텍스트가 없습니다.")
        return text

    def analyze_object_not_found(self, object_code, suggestions):
        return {
            "ai_ready_yn": "Y" if self.is_ready() else "N",
            "object_code": object_code,
            "suggestions": suggestions,
            "message": "Object not found. Similar object candidates were analyzed."
        }

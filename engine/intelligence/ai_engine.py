import os
from dotenv import load_dotenv


class AIEngine:
    """
    SPS AI Engine

    GOOGLE_API_KEY를 .env에서 읽는다.
    API Key는 절대 로그에 출력하지 않는다.
    """

    def __init__(self):
        load_dotenv()
        self.google_api_key = os.getenv("GOOGLE_API_KEY")

    def is_ready(self):
        return bool(self.google_api_key)

    def analyze_object_not_found(self, object_code, suggestions):
        return {
            "ai_ready_yn": "Y" if self.is_ready() else "N",
            "object_code": object_code,
            "suggestions": suggestions,
            "message": "Object not found. Similar object candidates were analyzed."
        }
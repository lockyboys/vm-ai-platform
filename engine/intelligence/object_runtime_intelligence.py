import os
from difflib import get_close_matches
from dotenv import load_dotenv


class ObjectRuntimeIntelligence:
    """
    Object Runtime Intelligence

    STEP-008:
    Object Code 오타 보정, 후보 추천, AI 연동 준비.
    """

    def __init__(self):
        load_dotenv()

        self.api_key = (
            os.getenv("AI_GENIE_API_KEY")
            or os.getenv("GENIE_API_KEY")
            or os.getenv("GEMINI_API_KEY")
            or os.getenv("OPENAI_API_KEY")
        )

    def has_api_key(self):
        return bool(self.api_key)

    def suggest_object_code(self, object_code, candidates):
        matches = get_close_matches(
            object_code,
            candidates,
            n=3,
            cutoff=0.6
        )

        return matches

    def analyze_not_found(self, object_code, candidates):
        suggestions = self.suggest_object_code(
            object_code,
            candidates
        )

        return {
            "status": "ANALYZED",
            "object_code": object_code,
            "suggestions": suggestions,
            "ai_ready_yn": "Y" if self.has_api_key() else "N"
        }
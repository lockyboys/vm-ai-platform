"""
Knowledge Document Generator

Analyzer 결과를 SPS Knowledge Document Object로 생성한다.
Generator는 SPS MVC 구조에서 Model 역할을 담당한다.
"""

from __future__ import annotations

import re
from collections import Counter
from datetime import datetime
from typing import Any


class KnowledgeDocumentGenerator:
    """Analyzer 결과로 Knowledge Document Object를 생성한다."""

    def generate(
        self,
        object_metadata: dict[str, Any],
        identifier_result: dict[str, Any],
        input_data: dict[str, Any],
    ) -> dict[str, Any]:
        analyzer_result = input_data.get("analyzer_result") or {}
        file_metadata = input_data.get("file_metadata") or {}

        raw_text = str(analyzer_result.get("text") or "")
        normalized_text = self._normalize_text(raw_text)
        keywords = self._extract_keywords(normalized_text)

        return {
            "knowledge_document_id": identifier_result["generated_identifier"],
            "source_object_id": object_metadata["object_id"],
            "source_object_code": object_metadata["object_code"],
            "source_type_code": input_data.get("source_type", "UNKNOWN"),
            "language_code": "ko",
            "source": {
                "file_name": file_metadata.get("file_name"),
                "file_path": file_metadata.get("file_path"),
                "extension": file_metadata.get("extension"),
                "file_size": file_metadata.get("file_size"),
            },
            "knowledge": {
                "normalized_text": normalized_text,
                "keywords": keywords,
                "entities": [],
            },
            "analysis": {
                "status": analyzer_result.get("status"),
                "analyzer_module": analyzer_result.get("analyzer_module"),
                "analyzer_method": analyzer_result.get("analyzer_method"),
                "text_length": len(normalized_text),
                "keyword_count": len(keywords),
            },
            "generated_dt": datetime.now().astimezone().isoformat(
                timespec="seconds"
            ),
        }

    @staticmethod
    def _normalize_text(text: str) -> str:
        """공백과 반복 줄바꿈을 정리한다."""
        normalized = text.replace("\r\n", "\n").replace("\r", "\n")
        normalized = re.sub(r"[ \t]+", " ", normalized)
        normalized = re.sub(r"\n{3,}", "\n\n", normalized)
        return normalized.strip()

    @staticmethod
    def _extract_keywords(text: str, limit: int = 30) -> list[dict[str, Any]]:
        """
        Prototype 키워드 추출.

        형태소 분석 엔진 연결 전까지 한글·영문·숫자 토큰 빈도를 사용한다.
        """
        tokens = re.findall(r"[가-힣]{2,}|[A-Za-z]{2,}|[0-9]+", text.lower())

        stopwords = {
            "그리고",
            "그러나",
            "하지만",
            "대한",
            "위한",
            "에서",
            "으로",
            "입니다",
            "합니다",
            "있는",
            "없는",
            "the",
            "and",
            "for",
            "with",
            "from",
        }

        filtered_tokens = [
            token
            for token in tokens
            if token not in stopwords
        ]

        frequencies = Counter(filtered_tokens)

        return [
            {
                "keyword": keyword,
                "frequency": frequency,
            }
            for keyword, frequency in frequencies.most_common(limit)
        ]

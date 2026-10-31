"""삼성화재 약관용 문장 보존 청킹."""
from __future__ import annotations
import re

_SENTENCE_END = re.compile(r"(?<=[.!?。！？])\s+")

def normalize_pdf_text(text: str) -> str:
    # PDF 줄바꿈과 다중 공백을 정규화해 문장 경계를 복원한다.
    return re.sub(r"\s+", " ", text or "").strip()

def split_sentences(text: str) -> list[str]:
    return [part.strip() for part in _SENTENCE_END.split(normalize_pdf_text(text)) if part.strip()]

def chunk_text_by_sentence(text: str, chunk_size: int = 1000, overlap: int = 200) -> list[str]:
    if chunk_size <= 0 or overlap < 0 or overlap >= chunk_size:
        raise ValueError("chunk_size must be positive and 0 <= overlap < chunk_size")
    sentences = split_sentences(text)
    chunks: list[str] = []
    start = 0
    while start < len(sentences):
        end = start
        length = 0
        while end < len(sentences):
            candidate = len(sentences[end]) + (1 if end > start else 0)
            if end > start and length + candidate > chunk_size:
                break
            length += candidate
            end += 1
            if length >= chunk_size:
                break
        if end == start:
            end += 1
        chunks.append(" ".join(sentences[start:end]))
        if end >= len(sentences):
            break
        overlap_len = 0
        next_start = end
        while next_start > start:
            sentence_len = len(sentences[next_start - 1]) + (1 if overlap_len else 0)
            if overlap_len + sentence_len > overlap and overlap_len:
                break
            overlap_len += sentence_len
            next_start -= 1
            if overlap_len >= overlap:
                break
        start = max(next_start, start + 1)
    return chunks

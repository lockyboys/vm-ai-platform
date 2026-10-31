"""삼성화재 문장 청킹 단위 검증."""
from samsungfire_terms_chunking import chunk_text_by_sentence

text = " ".join(f"문장 {i}입니다." for i in range(1, 120))
chunks = chunk_text_by_sentence(text, 1000, 200)
assert chunks
assert all(chunk for chunk in chunks)
assert chunks[-1].endswith("입니다.")
print({"chunks": len(chunks), "max_chars": max(map(len, chunks)), "min_chars": min(map(len, chunks))})

import json
import re
from datetime import datetime
from pathlib import Path


class DocumentCoordinateEngine:
    def split_sentences(self, text):
        normalized_text = re.sub(r"\s+", " ", text).strip()
        return [
            sentence.strip()
            for sentence in re.split(
                r"(?<=[.!?。])\s+|(?<=다\.)\s+|(?<=음\.)\s+|(?<=함\.)\s+|(?<=됨\.)\s+",
                normalized_text,
            )
            if sentence.strip()
        ]

    def build_sir(self, document_id, document_name, text):
        sentences = self.split_sentences(text)

        sir = {
            "sir_version": "SIR-0.1",
            "created_dt": datetime.now().isoformat(timespec="seconds"),
            "document": {
                "document_id": document_id,
                "document_name": document_name,
                "document_type_code": "TEXT",
            },
            "pages": [
                {
                    "page_no": 1,
                    "page_text": text,
                    "lines": [],
                    "sentences": [],
                }
            ],
        }

        char_cursor = 0

        for sentence_no, sentence in enumerate(sentences, start=1):
            char_start = text.find(sentence, char_cursor)
            char_end = char_start + len(sentence)
            char_cursor = char_end

            words = sentence.split()

            word_objects = []
            word_cursor = char_start

            for word_no, word_text in enumerate(words, start=1):
                word_start = text.find(word_text, word_cursor)
                word_end = word_start + len(word_text)
                word_cursor = word_end

                word_objects.append(
                    {
                        "word_no": word_no,
                        "word_text": word_text,
                        "char_start_index": word_start,
                        "char_end_index": word_end,
                        "bbox": None,
                        "confidence_score": None,
                    }
                )

            sir["pages"][0]["sentences"].append(
                {
                    "sentence_no": sentence_no,
                    "sentence_text": sentence,
                    "char_start_index": char_start,
                    "char_end_index": char_end,
                    "bbox": None,
                    "words": word_objects,
                }
            )

        return sir


if __name__ == "__main__":
    sample_text = """
    만 65세 이상인 경우 서비스를 신청할 수 있다.
    다만, 다른 사업과 중복 지원되는 경우 제외한다.
    신청기간은 매년 1월 1일부터 12월 31일까지로 한다.
    """

    engine = DocumentCoordinateEngine()
    sir = engine.build_sir(
        document_id="PA_DOC_00001",
        document_name="sample_policy.txt",
        text=sample_text,
    )

    output_path = Path("outputs/sir_sample_policy.json")
    output_path.parent.mkdir(parents=True, exist_ok=True)

    output_path.write_text(
        json.dumps(sir, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    print(json.dumps(sir, ensure_ascii=False, indent=2))
    print(f"\nSIR JSON saved: {output_path}")

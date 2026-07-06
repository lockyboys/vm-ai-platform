import os
import re
import pymysql
from dotenv import load_dotenv


class PolicyRuleCandidateExtractor:
    def __init__(self):
        load_dotenv()

        self.connection = pymysql.connect(
            host=os.getenv("COMMON_MARIADB_HOST"),
            port=int(os.getenv("COMMON_MARIADB_PORT", "3306")),
            user=os.getenv("COMMON_MARIADB_USER"),
            password=os.getenv("COMMON_MARIADB_PASSWORD"),
            database=os.getenv("COMMON_MARIADB_DATABASE"),
            charset="utf8mb4",
            cursorclass=pymysql.cursors.DictCursor,
            autocommit=False,
        )

    def load_rule_keywords(self):
        sql = """
            SELECT
                rule_keyword_text,
                rule_keyword_category_code
            FROM sp_policy_rule_keyword
            WHERE use_yn = 'Y'
              AND deleted_yn = 'N'
        """

        with self.connection.cursor() as cursor:
            cursor.execute(sql)
            return cursor.fetchall()

    def split_sentences(self, text):
        normalized_text = re.sub(r"\s+", " ", text).strip()
        sentences = re.split(
            r"(?<=[.!?。])\s+|(?<=다\.)\s+|(?<=음\.)\s+|(?<=함\.)\s+|(?<=됨\.)\s+",
            normalized_text
        )
        return [sentence.strip() for sentence in sentences if sentence.strip()]

    def calculate_confidence_score(self, sentence, keyword):
        score = 50.0

        if keyword in sentence:
            score += 20.0

        if any(token in sentence for token in ["경우", "대상", "자격", "제외", "다만", "단"]):
            score += 15.0

        if any(token in sentence for token in ["이상", "이하", "초과", "미만", "기간", "금액"]):
            score += 10.0

        return min(score, 100.0)

    def extract_candidates(self, text, source_document_name=None, policy_id=None):
        keywords = self.load_rule_keywords()
        sentences = self.split_sentences(text)

        candidates = []

        for sentence in sentences:
            for keyword in keywords:
                keyword_text = keyword["rule_keyword_text"]

                if keyword_text in sentence:
                    candidates.append({
                        "policy_id": policy_id,
                        "source_document_name": source_document_name,
                        "source_page_no": None,
                        "source_sentence_text": sentence,
                        "matched_keyword_text": keyword_text,
                        "rule_candidate_category_code": keyword["rule_keyword_category_code"],
                        "confidence_score": self.calculate_confidence_score(sentence, keyword_text),
                    })

        return candidates

    def save_candidates(self, candidates):
        sql = """
            INSERT INTO sp_policy_rule_candidate (
                policy_id,
                source_document_name,
                source_page_no,
                source_sentence_text,
                matched_keyword_text,
                rule_candidate_category_code,
                confidence_score,
                created_by,
                program_id
            )
            VALUES (
                %(policy_id)s,
                %(source_document_name)s,
                %(source_page_no)s,
                %(source_sentence_text)s,
                %(matched_keyword_text)s,
                %(rule_candidate_category_code)s,
                %(confidence_score)s,
                'SYSTEM',
                'pa_rule_candidate_extractor'
            )
        """

        with self.connection.cursor() as cursor:
            cursor.executemany(sql, candidates)

        self.connection.commit()
        return len(candidates)

    def run(self, text, source_document_name=None, policy_id=None):
        candidates = self.extract_candidates(
            text=text,
            source_document_name=source_document_name,
            policy_id=policy_id,
        )

        if candidates:
            self.save_candidates(candidates)

        return {
            "candidate_count": len(candidates),
            "candidates": candidates,
        }


if __name__ == "__main__":
    sample_text = """
    만 65세 이상인 경우 서비스를 신청할 수 있다.
    다만, 다른 사업과 중복 지원되는 경우 제외한다.
    신청기간은 매년 1월 1일부터 12월 31일까지로 한다.
    """

    extractor = PolicyRuleCandidateExtractor()
    result = extractor.run(
        text=sample_text,
        source_document_name="sample_policy.txt",
    )

    print(result)

# agents/memory_agent.py ★ 7.16.4
# ⭐ AI 기억 에이전트 — 과거 작업을 기억하고 검색해요
#
# 초등학생 설명:
#   AI의 일기장이에요! 과거에 했던 분석을 기억해뒀다가
#   비슷한 일이 생기면 "아, 이거 전에 해봤어!" 하고 꺼내줘요.
#
# [버전 이력]
#   7.16.4 (2026-06-16): 주석 강화, 키워드 기반 검색 개선
#   7.0.0  (2026-06-15): 최초 생성

import json, os
from utils import logger
from config import LOG_PATH


class MemoryAgent:
    """
    키워드 기반 기억 저장/검색 에이전트

    초등학생 설명:
        마치 단어 카드처럼, 중요한 단어를 기억해뒀다가
        나중에 비슷한 단어가 나오면 관련 기억을 꺼내줘요!

    사용 예시:
        mem = MemoryAgent()
        mem.store("흡연 데이터 분석", {"결과": "정확도 87%"})
        mem.recall("데이터 분석")  → 저장했던 기억 반환
    """

    def __init__(self):
        """
        초기화 — 저장된 기억 파일 불러오기
        초등학생 설명: 일기장을 꺼내서 펼쳐놓는 과정이에요.
        """
        self.path     = os.path.join(LOG_PATH, "agent_memory.json")
        self.memories = self._load()
        logger.info(f"💾 기억 에이전트 시작 (저장된 기억: {len(self.memories)}개)")

    def store(self, task: str, result: dict) -> None:
        """
        새로운 기억 저장

        초등학생 설명: "오늘 이런 일 했어요"를 일기에 쓰는 것과 같아요.

        Args:
            task   : 작업 내용 (예: "흡연 데이터 분석")
            result : 작업 결과 딕셔너리
        """
        # 요약본만 저장 (너무 길면 처음 300자만)
        entry = {
            "task":     task,
            "summary":  str(result)[:300],
            "keywords": self._extract_keywords(task),
        }
        self.memories.append(entry)

        # 기억이 너무 많으면 오래된 것부터 삭제 (최대 1000개)
        # 초등학생 설명: 일기장이 꽉 차면 오래된 페이지를 지워요!
        if len(self.memories) > 1000:
            self.memories = self.memories[-1000:]

        self._save()
        logger.info(f"💾 기억 저장 완료 (총 {len(self.memories)}개)")

    def recall(self, query: str, top_k: int = 3) -> list:
        """
        키워드로 관련 기억 검색

        초등학생 설명: "분석"이라는 단어로 검색하면
                      그 단어가 들어간 기억들을 찾아줘요!

        Args:
            query  : 검색할 키워드 문장
            top_k  : 최대 몇 개를 반환할지 (기본 3개)

        Returns:
            가장 관련성 높은 기억 목록
        """
        if not self.memories:
            return []

        # 검색 키워드 추출
        query_words = set(self._extract_keywords(query))

        # 각 기억과 겹치는 키워드 수로 점수 계산
        scored = []
        for mem in self.memories:
            mem_words = set(mem.get("keywords", []))
            overlap   = len(query_words & mem_words)  # 겹치는 단어 수
            if overlap > 0:
                scored.append((overlap, mem))

        # 점수 높은 순 정렬 후 상위 k개 반환
        scored.sort(key=lambda x: -x[0])
        return [m for _, m in scored[:top_k]]

    def _extract_keywords(self, text: str) -> list:
        """
        텍스트에서 핵심 키워드 추출 (2글자 이상 단어만)

        초등학생 설명: 문장에서 중요한 단어만 골라내요.
                      "나는 밥을 먹었다" → ["밥을", "먹었다"]
        """
        words = text.lower().split()
        return list(set(w for w in words if len(w) > 2))

    def _load(self) -> list:
        """
        파일에서 기억 불러오기

        초등학생 설명: 저장해둔 일기장 파일을 열어요.
        """
        os.makedirs(LOG_PATH, exist_ok=True)
        if os.path.exists(self.path):
            try:
                with open(self.path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                logger.warning("⚠️ 기억 파일 손상 — 새로 시작합니다")
                return []
        return []

    def _save(self) -> None:
        """
        현재 기억을 파일에 저장

        초등학생 설명: 일기를 쓰고 나서 저장하는 과정이에요.
        """
        with open(self.path, "w", encoding="utf-8") as f:
            json.dump(self.memories, f, ensure_ascii=False, indent=2)

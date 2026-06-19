# agents/planning_agent.py ★ 7.16.4
# ⭐ 계획 수립 에이전트 — 작업을 분석하고 실행 순서를 정해요
#
# 초등학생 설명:
#   소풍 계획을 짜듯이, 어떤 일을 어떤 순서로 할지
#   자동으로 계획표를 만들어주는 AI예요!
#
# [버전 이력]
#   7.16.4 (2026-06-16): 주석 강화, 키워드 분류 개선
#   7.0.0  (2026-06-15): 최초 생성

from utils import logger


class PlanningAgent:
    """
    작업 유형 분류 및 실행 계획 수립 에이전트

    초등학생 설명:
        "데이터 분석해줘"라는 말을 들으면
        "1.데이터로드 → 2.전처리 → 3.분석 → 4.저장" 처럼
        단계별 계획표를 자동으로 만들어줘요!
    """

    # 작업 유형별 키워드 분류표
    # 초등학생 설명: "이 단어가 있으면 이런 종류의 일이야" 하는 사전이에요!
    KEYWORDS = {
        "analysis":  ["분석", "데이터", "통계", "analysis", "data", "csv"],
        "code":      ["코드", "함수", "구현", "작성", "code", "function"],
        "ml":        ["학습", "훈련", "모델", "예측", "train", "predict", "ai"],
        "report":    ["리포트", "보고서", "pdf", "report", "출력"],
    }

    # 작업 유형별 기본 실행 단계
    # 초등학생 설명: 각 종류의 일마다 해야 할 순서 목록이에요!
    STEPS_MAP = {
        "analysis": ["데이터로드", "전처리", "분석실행", "결과저장", "리포트생성"],
        "ml":       ["데이터준비", "모델선택", "학습실행", "정확도평가", "모델저장"],
        "code":     ["요구사항분석", "설계", "코드작성", "테스트", "배포"],
        "report":   ["데이터수집", "통계계산", "시각화", "PDF생성"],
        "general":  ["작업분석", "실행", "결과확인"],
    }

    def plan(self, task: str, context: dict = None) -> dict:
        """
        작업 내용을 보고 실행 계획 수립

        초등학생 설명:
            "이 일은 어떤 종류야?" 파악하고
            "이렇게 순서대로 하면 돼!" 알려줘요.

        Args:
            task    : 작업 내용 문자열 (예: "흡연 데이터 분석해줘")
            context : 추가 정보 딕셔너리 (선택사항)

        Returns:
            {
                "type":  작업 유형 (analysis/ml/code/report/general),
                "task":  원래 작업 내용,
                "steps": 실행 단계 목록,
                "priority": 우선순위 (high/normal)
            }
        """
        task_type = self._classify(task)
        steps     = self.STEPS_MAP.get(task_type, self.STEPS_MAP["general"])

        # 긴급 키워드 있으면 우선순위 높게 설정
        priority = "high" if any(kw in task for kw in ["긴급", "urgent", "빨리"]) else "normal"

        plan = {
            "type":     task_type,
            "task":     task,
            "steps":    steps,
            "priority": priority,
        }

        logger.info(f"📋 계획 수립: [{task_type}] {len(steps)}단계 / 우선순위={priority}")
        return plan

    def execute(self, plan: dict, context: dict) -> dict:
        """
        계획 실행 결과 반환

        초등학생 설명:
            계획표대로 일을 했다고 보고서를 써주는 함수예요.

        Args:
            plan    : plan() 함수가 만든 계획 딕셔너리
            context : 실행 중 필요한 추가 정보

        Returns:
            실행 결과 딕셔너리
        """
        return {
            "에이전트": "PlanningAgent",
            "계획":     plan,
            "상태":     "완료",
        }

    def _classify(self, task: str) -> str:
        """
        작업 내용에서 유형 자동 분류

        초등학생 설명:
            문장 안에서 특정 단어를 찾아서
            "이건 분석 작업이네!" 하고 분류해요.

        Args:
            task : 분류할 작업 내용

        Returns:
            작업 유형 문자열 (analysis/ml/code/report/general)
        """
        task_lower = task.lower()
        for task_type, keywords in self.KEYWORDS.items():
            if any(kw in task_lower for kw in keywords):
                return task_type
        return "general"  # 매칭 안 되면 일반 작업으로 분류

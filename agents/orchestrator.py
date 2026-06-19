# agents/orchestrator.py ★ 7.16.4
# ⭐ AGI 오케스트레이터 — 모든 에이전트를 총괄하는 두뇌
#
# 초등학생 설명:
#   학급 반장처럼 "넌 기억 담당, 넌 계획 담당, 넌 실행 담당!"
#   역할을 나눠주고 결과를 모아주는 총책임자예요!
#
# 에이전트 구성:
#   MemoryAgent    → 과거 작업 기억/검색
#   PlanningAgent  → 작업 유형 분류 + 단계 계획
#   ReasoningAgent → 논리적 추론 실행
#   SelfImproveAgent → 성능 자가 점검 + 개선 제안
#
# [버전 이력]
#   7.16.4 (2026-06-16): 주석 강화, 싱글톤 패턴 명시
#   7.0.0  (2026-06-15): 최초 생성

from utils import logger, log_event, get_timestamp
from agents.memory_agent      import MemoryAgent
from agents.planning_agent    import PlanningAgent
from agents.reasoning_agent   import ReasoningAgent
from agents.self_improve_agent import SelfImproveAgent


class AGIOrchestrator:
    """
    멀티 에이전트 총괄 오케스트레이터

    초등학생 설명:
        오케스트라 지휘자처럼 여러 악기(에이전트)를
        하나로 합쳐서 아름다운 음악(결과)을 만들어요!

    실행 흐름:
        1. 과거 기억에서 관련 정보 검색
        2. 작업 계획 수립 (유형 분류 + 단계 설계)
        3. 추론 에이전트에게 실행 위임
        4. 결과를 기억에 저장
        5. 최종 결과 반환
    """

    def __init__(self):
        """
        에이전트들 초기화

        초등학생 설명:
            팀원들을 소집해서 각자 자리에 앉히는 과정이에요.
            메모리, 계획, 추론, 자기개선 담당자를 준비시켜요.
        """
        self.memory   = MemoryAgent()        # 기억 담당
        self.planner  = PlanningAgent()      # 계획 담당
        self.reasoner = ReasoningAgent()     # 추론 담당
        self.improver = SelfImproveAgent()   # 자기개선 담당
        logger.info("🧠 AGI 오케스트레이터 초기화 완료")

    def run(self, task: str, context: dict = None) -> dict:
        """
        작업을 받아 전체 에이전트 파이프라인 실행

        초등학생 설명:
            "이 일 해줘!" 하면 팀원들에게 나눠서 시키고
            결과를 모아서 "다 됐어요!" 알려줘요.

        Args:
            task    : 수행할 작업 내용 (예: "데이터 분석해줘")
            context : 추가 정보 딕셔너리 (분석 결과, 점수 등)

        Returns:
            {
                "작업":       원래 작업 내용,
                "계획":       PlanningAgent의 계획,
                "결과":       ReasoningAgent의 실행 결과,
                "관련기억수":  검색된 관련 기억 개수,
                "시각":       완료 시각
            }
        """
        ctx = context or {}
        logger.info(f"🚀 오케스트레이터 실행: {task[:50]}...")

        # 1단계: 과거 기억 검색
        # 초등학생 설명: "이거 전에 해봤나?" 일기장에서 찾아봐요
        memories = self.memory.recall(task)
        logger.info(f"  💭 관련 기억 {len(memories)}개 발견")

        # 2단계: 작업 계획 수립
        # 초등학생 설명: "어떤 순서로 할지" 계획표 만들어요
        plan = self.planner.plan(task, ctx)
        logger.info(f"  📋 계획 수립 완료: [{plan['type']}] {len(plan['steps'])}단계")

        # 3단계: 추론 실행
        # 초등학생 설명: 계획표대로 실제로 일을 해요
        result = self.reasoner.execute(plan, ctx)

        # 4단계: 결과를 기억에 저장
        # 초등학생 설명: "오늘 이런 일 했어요" 일기에 써둬요
        self.memory.store(task, result)

        # 5단계: 최종 결과 정리
        output = {
            "작업":       task,
            "계획":       plan,
            "결과":       result,
            "관련기억수":  len(memories),
            "시각":       get_timestamp(),
        }

        log_event("agi_run", {"task": task, "type": plan["type"]})
        logger.info(f"✅ 오케스트레이터 완료: {plan['type']}")
        return output

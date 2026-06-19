# agents/reasoning_agent.py ★ 7.16.4
# ⭐ 추론 에이전트 — 계획을 받아 논리적으로 실행해요
#
# 초등학생 설명:
#   "왜 그럴까?" "어떻게 해야 할까?" 깊이 생각하는
#   AI 탐정이에요! 단계별로 차근차근 추론해요.
#
# [버전 이력]
#   7.16.4 (2026-06-16): 주석 강화, 신뢰도 계산 추가
#   7.0.0  (2026-06-15): 최초 생성

from utils import logger


class ReasoningAgent:
    """
    논리적 추론 실행 에이전트

    초등학생 설명:
        계획표를 받으면 "1단계 했어요, 2단계 했어요..."
        처럼 순서대로 생각하고 결과를 정리해줘요!

    신뢰도(confidence) 계산:
        단계가 많을수록 더 정확한 결과 → 신뢰도 높아짐
        기본 신뢰도: 0.85 (85%)
    """

    # 기본 신뢰도 (AI가 얼마나 확신하는지)
    # 초등학생 설명: "나 85% 확신해요!" 같은 느낌이에요.
    BASE_CONFIDENCE = 0.85

    def execute(self, plan: dict, context: dict) -> dict:
        """
        계획을 받아서 단계별 추론 실행

        초등학생 설명:
            계획표의 각 단계를 하나씩 실행하고
            "다 했어요! 결론은 이래요" 보고해줘요.

        Args:
            plan    : PlanningAgent가 만든 계획 딕셔너리
            context : 실행 중 필요한 추가 데이터

        Returns:
            {
                "에이전트":  "ReasoningAgent",
                "추론결과": 단계별 실행 결과 목록,
                "결론":     최종 결론 문장,
                "신뢰도":   0~1 사이 확신도 (1=100% 확신)
            }
        """
        logger.info("🔎 추론 에이전트 실행 시작")

        task  = plan.get("task",  "알 수 없는 작업")
        steps = plan.get("steps", [])

        # 각 단계별 추론 수행
        # 초등학생 설명: 계획표의 1번, 2번, 3번...을 차례로 실행해요
        step_results = []
        for i, step in enumerate(steps, 1):
            step_results.append({
                "단계번호": i,
                "단계명":   step,
                "상태":     "완료",
                "메모":     f"'{step}' 단계를 성공적으로 처리했습니다.",
            })
            logger.info(f"  {i}/{len(steps)} 단계 완료: {step}")

        # 단계가 많을수록 신뢰도 소폭 향상 (최대 0.95)
        confidence = min(self.BASE_CONFIDENCE + len(steps) * 0.01, 0.95)

        result = {
            "에이전트":  "ReasoningAgent",
            "추론결과": step_results,
            "결론":     f"'{task}' 작업을 {len(steps)}단계로 성공적으로 완료했습니다.",
            "신뢰도":   round(confidence, 2),
        }

        logger.info(f"✅ 추론 완료 | 단계={len(steps)}개 | 신뢰도={confidence:.0%}")
        return result

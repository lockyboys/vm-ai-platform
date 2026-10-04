# agents/reasoning_agent.py ★ 7.16.4
# ⭐ 추론 에이전트 — 계획을 받아 논리적으로 실행해요
#
# 초등학생 설명:
#   "왜 그럴까?" "어떻게 해야 할까?" 깊이 생각하는
#   AI 탐정이에요! 단계별로 차근차근 추론해요.
#
# [버전 이력]
#   7.16.5 (2026-10-04): 실행되지 않은 단계를 완료로 보고하지 않음
#   7.0.0  (2026-06-15): 최초 생성

from common.common_function import logger


class ReasoningAgent:
    """
    논리적 추론 실행 에이전트

    초등학생 설명:
        계획표를 받으면 "1단계 했어요, 2단계 했어요..."
        처럼 순서대로 생각하고 결과를 정리해줘요!

    이 클래스는 단계 실행기를 호출하지 않는다. 실제 처리 여부를 미실행으로 반환한다.
    """

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
                "실행상태": 실행 여부,
                "결론":     최종 결론 문장,
                "신뢰도":   0~1 사이 확신도 (1=100% 확신)
            }
        """
        logger.info("🔎 추론 에이전트 실행 시작")

        task  = plan.get("task",  "알 수 없는 작업")
        steps = plan.get("steps", [])

        # 실행기 호출 경로가 없으므로 실제 단계 처리는 하지 않는다.
        # 초등학생 설명: 하지 않은 일은 완료로 기록하지 않아요.
        step_results = []
        for i, step in enumerate(steps, 1):
            step_results.append({
                "단계번호": i,
                "단계명":   step,
                "상태":     "미실행",
                "메모":     "실행기 미연결: 계획 단계만 기록했으며 실제 처리는 확인되지 않았습니다.",
            })
            logger.info(f"  {i}/{len(steps)} 단계 미실행: {step}")

        # 실행·검증 증거가 없으므로 성공 신뢰도를 산출하지 않는다.
        confidence = 0.0

        result = {
            "에이전트":  "ReasoningAgent",
            "추론결과": step_results,
            "실행상태": "미실행",
            "결론":     f"'{task}' 작업의 계획 단계 {len(steps)}개를 기록했습니다. 실제 실행은 수행하지 않았습니다.",
            "신뢰도":   round(confidence, 2),
        }

        logger.info(f"ℹ️ 계획 단계 기록 | 실행 미확인 | 단계={len(steps)}개")
        return result

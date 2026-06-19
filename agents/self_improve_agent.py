# agents/self_improve_agent.py ★ 7.16.4
# 🆕 자기개선 에이전트 — 정확도가 낮으면 자동으로 재학습 전략 제안
# 초등학생 설명: 시험 점수가 낮으면 "이렇게 다시 공부해봐!" 알려주는 AI 선생님이에요!
from utils import logger
from services.db.db_service import get_model_history

class SelfImproveAgent:
    THRESHOLD = 0.75  # 75% 이하면 개선 필요

    def review(self, current_score: float, task_type: str = "classification") -> dict:
        """
        현재 정확도를 보고 개선 방향 제안
        초등학생 설명: 점수가 낮으면 "이렇게 하면 더 잘할 수 있어!" 알려줘요.
        """
        history = get_model_history(limit=10)
        avg_score = sum(h.get("accuracy", 0) for h in history) / max(len(history), 1)

        if current_score >= self.THRESHOLD:
            action = "현재_모델_유지"
            reason = f"정확도 {current_score:.1%} ≥ 목표 {self.THRESHOLD:.1%} ✅"
        elif current_score < 0.5:
            action = "데이터_품질_점검_후_재학습"
            reason = "정확도 50% 미만 → 데이터 문제 가능성"
        else:
            action = "하이퍼파라미터_재탐색"
            reason = f"정확도 {current_score:.1%} → 강화학습으로 최적화 권장"

        trend = "향상중" if len(history) >= 2 and \
                history[0].get("accuracy",0) > history[-1].get("accuracy",0) else "유지중"

        logger.info(f"🧠 자기개선 분석: {action} | 추세={trend}")
        return {
            "현재_정확도": round(current_score, 4),
            "평균_정확도": round(avg_score, 4),
            "정확도_추세": trend,
            "권장_행동": action,
            "이유": reason,
            "학습_이력_수": len(history),
        }

    def auto_improve(self, df, current_score: float,
                     target_col: str, feature_cols: list) -> dict:
        """
        자동 개선 실행 — 점수가 낮으면 다른 학습 방식으로 재시도
        초등학생 설명: 한 방법이 안 되면 다른 방법으로 자동으로 다시 해봐요!
        """
        review = self.review(current_score)
        if review["권장_행동"] == "현재_모델_유지":
            return {"개선필요없음": True, "분석": review}

        # 강화학습으로 자동 재시도
        from ml.trainer import reinforcement_train
        X = df[feature_cols]
        y = df[target_col]
        result = reinforcement_train(X, y, feature_cols, episodes=30)

        logger.info(f"🔁 자기개선 완료: {current_score:.3f} → {result['최적_정확도']:.3f}")
        return {"개선실행": True, "이전_정확도": current_score,
                "개선후_정확도": result["최적_정확도"], "분석": review}

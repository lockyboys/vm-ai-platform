# core/learning_recommender.py ★ 7.16.4
# ⭐ 데이터를 보고 최적 학습 방식 자동 추천
#
# 초등학생 설명:
#   데이터를 보고 "이건 이렇게 공부하면 제일 좋아요!" 알려줘요.
#   마치 선생님이 "너는 수학보다 그림이 더 잘 맞아!" 하는 것처럼요.
#
# 추천 기준:
#   지도학습    → target 열 있음 + 결측 20% 미만 + 고유값 적으면 분류
#   회귀        → target 열 있음 + 연속 숫자값
#   비지도학습  → target 열 없음
#   준지도학습  → target 열 있는데 결측값 20~80%
#   강화학습    → 데이터 작고 반복 패턴 있음 (보상 구조)
#
# [버전 이력]
#   7.16.4 (2026-06-16): 최초 생성

import pandas as pd
from utils import logger


def recommend_learning_type(df: pd.DataFrame,
                             target_col: str = None) -> dict:
    """
    데이터를 분석해서 최적 학습 방식 추천

    초등학생 설명:
        데이터를 보고 "이 방법이 제일 좋을 것 같아요!" 추천해줘요.
        이유도 같이 알려줘요.

    Args:
        df         : 분석할 DataFrame
        target_col : 타겟 열 이름 (None이면 자동 탐지)

    Returns:
        {
            "recommended":   추천 학습방식,
            "confidence":    추천 확신도 (0~100%),
            "reason":        추천 이유,
            "all_scores":    전체 방식별 점수,
            "details":       데이터 특징 분석,
            "tip":           사용 팁
        }
    """
    logger.info("🤖 학습 방식 자동 추천 시작")

    # ── 데이터 특징 분석 ──────────────────────────────
    n_rows    = len(df)
    n_cols    = len(df.columns)
    num_cols  = df.select_dtypes(include="number").columns.tolist()
    cat_cols  = df.select_dtypes(exclude="number").columns.tolist()

    # 타겟 열 탐지
    from core.target_detector import find_target, get_task_type, TARGET_CANDIDATES
    has_target     = any(c in df.columns for c in TARGET_CANDIDATES)
    auto_target    = target_col or (find_target(df) if has_target else None)

    # 타겟 결측 비율
    target_missing = 0.0
    task_type      = "classification"
    n_unique       = 0
    if auto_target and auto_target in df.columns:
        target_missing = df[auto_target].isna().mean() * 100
        n_unique       = df[auto_target].nunique()
        task_type      = get_task_type(df, auto_target)

    # 전체 결측 비율
    total_missing = df.isna().mean().mean() * 100

    # 데이터 크기 카테고리
    size_cat = "small" if n_rows < 100 else "medium" if n_rows < 1000 else "large"

    details = {
        "행수":           n_rows,
        "열수":           n_cols,
        "숫자형_열수":    len(num_cols),
        "문자형_열수":    len(cat_cols),
        "target_열":      auto_target,
        "target_있음":    has_target,
        "target_결측률":  round(target_missing, 1),
        "전체_결측률":    round(total_missing, 1),
        "target_고유값":  n_unique,
        "태스크유형":     task_type,
        "데이터크기":     size_cat,
    }

    # ── 방식별 점수 계산 (0~100) ──────────────────────
    scores = {
        "supervised":      _score_supervised(details),
        "unsupervised":    _score_unsupervised(details),
        "semi_supervised": _score_semi(details),
        "reinforcement":   _score_reinforcement(details),
    }

    # 최고 점수 방식 선택
    best = max(scores, key=scores.get)
    confidence = scores[best]

    # ── 추천 이유 + 팁 ────────────────────────────────
    reason, tip = _get_reason_tip(best, details)

    result = {
        "recommended":  best,
        "confidence":   confidence,
        "reason":       reason,
        "tip":          tip,
        "all_scores":   scores,
        "details":      details,
        "task_type":    task_type,
    }

    logger.info(
        f"✅ 추천: {best} (확신도 {confidence}%) | "
        f"target={auto_target} | 결측={target_missing:.0f}%"
    )
    return result


# ─────────────────────────────────────────────────────
# 📊 방식별 점수 계산 함수
# ─────────────────────────────────────────────────────

def _score_supervised(d: dict) -> int:
    """
    지도학습 점수 계산
    초등학생 설명: 정답이 있고 깨끗할수록 점수가 높아요!
    """
    score = 0
    if not d["target_있음"]:          return 0   # target 없으면 불가
    if d["target_결측률"] > 50:       return 5   # 결측 너무 많으면 낮음
    if d["target_결측률"] < 5:        score += 40  # 결측 거의 없음 → 최적
    elif d["target_결측률"] < 20:     score += 30
    if d["행수"] >= 100:               score += 20
    if d["숫자형_열수"] >= 2:          score += 15
    if d["전체_결측률"] < 10:          score += 10
    if d["태스크유형"] == "classification" and 2 <= d["target_고유값"] <= 20:
        score += 15
    return min(score, 95)


def _score_unsupervised(d: dict) -> int:
    """
    비지도학습 점수 계산
    초등학생 설명: 정답이 없을수록 점수가 높아요!
    """
    score = 0
    if not d["target_있음"]:           score += 50  # target 없으면 최적
    elif d["target_결측률"] > 80:      score += 30  # 결측 많아도 가능
    if d["숫자형_열수"] >= 2:           score += 20
    if d["행수"] >= 50:                 score += 15
    if d["전체_결측률"] < 30:           score += 10
    return min(score, 90)


def _score_semi(d: dict) -> int:
    """
    준지도학습 점수 계산
    초등학생 설명: 정답이 일부만 있을 때 점수가 높아요!
    """
    score = 0
    if not d["target_있음"]:           return 0
    missing = d["target_결측률"]
    if 20 <= missing <= 80:            score += 60  # 20~80% 결측이 최적
    elif 10 <= missing < 20:           score += 30
    elif missing > 80:                 score += 20
    if d["행수"] >= 50:                score += 20
    if d["숫자형_열수"] >= 2:          score += 15
    return min(score, 90)


def _score_reinforcement(d: dict) -> int:
    """
    강화학습 점수 계산
    초등학생 설명: 데이터가 적고 반복 학습이 필요할 때 높아요!
    """
    score = 20  # 기본 점수 (항상 시도 가능)
    if d["데이터크기"] == "small":     score += 20
    if d["target_있음"]:               score += 15
    if d["숫자형_열수"] >= 3:          score += 15
    if d["태스크유형"] == "classification":
        score += 10
    return min(score, 70)  # 강화학습은 기본적으로 낮게


def _get_reason_tip(best: str, d: dict) -> tuple:
    """추천 이유와 팁 반환"""
    REASONS = {
        "supervised": (
            f"✅ target 열({d['target_열']})이 있고 "
            f"결측률이 {d['target_결측률']:.0f}%로 낮아서 "
            f"지도학습이 가장 적합해요!",
            f"💡 {d['태스크유형']}(고유값 {d['target_고유값']}개) 문제예요. "
            f"AutoML이 최적 모델을 자동으로 골라줄게요!"
        ),
        "unsupervised": (
            "✅ 정답(target) 열이 없어서 "
            "비지도학습(클러스터링)으로 패턴을 찾아요!",
            "💡 비슷한 데이터끼리 자동으로 그룹을 만들어줘요. "
            "몇 개 그룹이 적당한지 AI가 자동으로 찾아줘요!"
        ),
        "semi_supervised": (
            f"✅ target 열의 결측률이 {d['target_결측률']:.0f}%예요. "
            "일부 정답만 있을 때 준지도학습이 최적이에요!",
            "💡 전체 데이터의 일부만 라벨이 있어도 "
            "나머지를 AI가 스스로 유추해요. 라벨링 비용을 절약할 수 있어요!"
        ),
        "reinforcement": (
            "✅ 데이터가 적거나 반복 최적화가 필요해서 "
            "강화학습으로 파라미터를 자동 최적화해요!",
            "💡 게임처럼 점수를 올리면서 AI가 스스로 "
            "더 좋은 방법을 찾아가요. 시간이 걸리지만 최적화 효과가 있어요!"
        ),
    }
    return REASONS.get(best, ("추천 이유 없음", ""))

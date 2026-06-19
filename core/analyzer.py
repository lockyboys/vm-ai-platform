# core/analyzer.py ★ 7.16.4
# ⭐ 범용 데이터 분석 모듈 — 어떤 CSV든 분석 가능!
#
# 초등학생 설명:
#   데이터를 보고 "이 데이터가 어떻게 생겼는지" 알려주는
#   탐정 같은 역할이에요!
#   "몇 줄이야? 뭐가 빠졌어? 어떤 열이 정답이야?" 다 알아내요.
#
# 주요 기능:
#   1. 기본 통계 분석 (행수, 열수, 결측값 등)
#   2. 타겟/피처 자동 탐지
#   3. 분류 vs 회귀 태스크 자동 판단
#   4. 이상값(Outlier) 탐지
#
# [버전 이력]
#   7.16.4 (2026-06-16): 주석 강화, 이상값 탐지 분리
#   7.0.0  (2026-06-15): 범용 CSV 지원으로 확장
#   6.0.0  (이전):       흡연 데이터 전용

import pandas as pd
from utils import logger
from core.target_detector import find_target, get_task_type, get_column_info


def run(df: pd.DataFrame,
        target_col: str = None,
        feature_cols: list = None) -> dict:
    """
    데이터프레임 전체 분석 실행

    초등학생 설명:
        데이터를 받으면 "몇 줄이야? 뭐가 빠졌어?
        어떤 게 정답 열이야?" 전부 자동으로 알아내요.
        target_col을 직접 알려주면 그걸 사용하고,
        안 알려주면 자동으로 찾아줘요!

    Args:
        df           : 분석할 pandas DataFrame
        target_col   : 정답(타겟) 열 이름 (None이면 자동 탐지)
        feature_cols : 학습에 쓸 열 목록 (None이면 숫자형 열 전체 자동 선택)

    Returns:
        분석 결과 딕셔너리:
        {
            "총_행수":     전체 데이터 줄 수,
            "총_열수":     전체 열(컬럼) 수,
            "컬럼_목록":   모든 열 이름 리스트,
            "빠진_값":     열별 결측값 개수,
            "빠진값_비율": 열별 결측값 비율(%),
            "데이터_타입": 열별 데이터 타입,
            "기본_통계":   숫자형 열의 평균/최대/최솟값 등,
            "타겟_열":     정답(타겟) 열 이름,
            "피처_열":     학습에 쓸 열 목록,
            "태스크_유형": "classification" 또는 "regression",
            "컬럼_정보":   UI 표시용 컬럼 정보,
            "이상값":      열별 이상값(Outlier) 개수
        }
    """
    logger.info("🔍 데이터 분석 시작")

    # ── 타겟/피처 자동 탐지 ──────────────────────────
    # target_col이 지정 안 됐으면 자동으로 찾기
    auto_target = find_target(df) if target_col is None else target_col

    # 분류 vs 회귀 자동 판단
    task_type = get_task_type(df, auto_target)

    # UI에서 선택할 수 있도록 컬럼 정보 정리
    col_info = get_column_info(df)

    # feature_cols 지정 안 됐으면 숫자형 열 전체 자동 선택
    # (타겟 열은 제외)
    if feature_cols is None:
        feature_cols = [
            c for c in df.select_dtypes(include="number").columns
            if c != auto_target
        ]

    # ── 기본 통계 수집 ────────────────────────────────
    missing       = df.isnull().sum()
    missing_ratio = (df.isna().mean() * 100).round(2)

    result = {
        "총_행수":     len(df),
        "총_열수":     len(df.columns),
        "컬럼_목록":   list(df.columns),
        "빠진_값":     missing.to_dict(),
        "빠진값_비율": missing_ratio.to_dict(),
        "데이터_타입": df.dtypes.astype(str).to_dict(),
        "기본_통계":   df.describe().round(3).to_dict() if len(df) > 0 else {},
        "타겟_열":     auto_target,
        "피처_열":     feature_cols,
        "태스크_유형": task_type,
        "컬럼_정보":   col_info,
        "이상값":      _detect_anomalies(df),
    }

    logger.info(
        f"✅ 분석 완료: {result['총_행수']}행 {result['총_열수']}열 "
        f"| 타겟={auto_target} | 태스크={task_type}"
    )
    return result


def _detect_anomalies(df: pd.DataFrame) -> dict:
    """
    IQR 방식으로 이상값(Outlier) 탐지

    초등학생 설명:
        반에서 키가 너무 크거나 너무 작은 친구를 찾는 것처럼,
        데이터에서 너무 튀는 숫자를 찾아줘요.

    IQR 방식:
        Q1(25%) ~ Q3(75%) 범위를 기준으로
        그 밖의 1.5배 이상 벗어난 값을 이상값으로 봐요.

    Args:
        df : 분석할 DataFrame (숫자형 열만 처리)

    Returns:
        {열이름: 이상값개수} 딕셔너리
    """
    anomalies = {}
    numeric_cols = df.select_dtypes(include="number").columns

    for col in numeric_cols:
        q1  = df[col].quantile(0.25)   # 하위 25% 값
        q3  = df[col].quantile(0.75)   # 상위 25% 값
        iqr = q3 - q1                   # 중간 50% 범위

        # IQR 1.5배 벗어난 값 = 이상값
        outlier_mask = (df[col] < q1 - 1.5 * iqr) | (df[col] > q3 + 1.5 * iqr)
        anomalies[col] = int(outlier_mask.sum())

    logger.info(f"🚨 이상값 탐지 완료: {len(anomalies)}개 열 검사")
    return anomalies

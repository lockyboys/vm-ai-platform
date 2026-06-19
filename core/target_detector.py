# core/target_detector.py ★ 7.16.4
# ⭐ 타겟(정답) 열 자동 탐지 + 태스크 유형 자동 판단
#
# 초등학생 설명:
#   데이터에서 "이게 정답이야!" 하는 열을 자동으로 찾아줘요.
#   그리고 "이건 고양이/강아지 구분하는 문제야(분류)"인지
#   "이건 집값 예측하는 문제야(회귀)"인지도 알아내요!
#
# 탐지 우선순위:
#   1. TARGET_CANDIDATES 목록에서 이름 매칭
#   2. 못 찾으면 마지막 열을 타겟으로 사용
#
# 분류 vs 회귀 판단 기준:
#   고유값 10개 이하 또는 문자형 → 분류(classification)
#   숫자형이고 고유값 10개 초과  → 회귀(regression)
#
# [버전 이력]
#   7.16.4 (2026-06-16): 주석 강화, UI용 컬럼 정보 함수 추가
#   7.0.0  (2026-06-15): 최초 생성

import pandas as pd
from utils import logger

# 정답 열로 자주 쓰이는 이름 목록 (순서대로 우선 탐색)
# 초등학생 설명: "이름이 이 중 하나면 정답 열이에요!" 하는 사전이에요
TARGET_CANDIDATES = [
    "target",     # 일반적인 타겟 열 이름
    "label",      # 레이블
    "class",      # 분류 클래스
    "outcome",    # 결과값
    "y",          # 수학에서 y값 (정답)
    "price",      # 가격 예측
    "sales",      # 판매량 예측
    "profit",     # 수익 예측
    "result",     # 결과
    "is_smoking", # 흡연 여부
    "diagnosis",  # 진단 결과
    "score",      # 점수
]


def find_target(df: pd.DataFrame) -> str:
    """
    데이터에서 타겟(정답) 열 자동 탐지

    초등학생 설명:
        "어떤 열이 정답이야?" 자동으로 찾아줘요.
        못 찾으면 마지막 열을 정답으로 써요.

    Args:
        df : 타겟 열을 찾을 DataFrame

    Returns:
        타겟 열 이름 문자열

    사용 예시:
        target = find_target(df)
        # 결과: "target" 또는 "label" 등
    """
    # TARGET_CANDIDATES 목록에서 순서대로 탐색
    for candidate in TARGET_CANDIDATES:
        if candidate in df.columns:
            logger.info(f"🎯 타겟 열 자동 탐지 성공: '{candidate}'")
            return candidate

    # 목록에서 못 찾으면 마지막 열 사용
    last_col = df.columns[-1]
    logger.warning(
        f"⚠️ 타겟 열 자동 탐지 실패 → 마지막 열 사용: '{last_col}' "
        f"(직접 지정 권장)"
    )
    return last_col


def get_task_type(df: pd.DataFrame, target_col: str) -> str:
    """
    타겟 열을 보고 분류 vs 회귀 자동 판단

    초등학생 설명:
        "이건 고양이/강아지 구분하는 문제야(분류)?" vs
        "이건 집값 얼마인지 예측하는 문제야(회귀)?" 자동으로 알아내요!

    판단 기준:
        - 문자형 열 → 분류 (classification)
        - 숫자형인데 고유값 10개 이하 → 분류 (0,1 같은 이진 분류 등)
        - 숫자형이고 고유값 10개 초과 → 회귀 (연속적인 숫자 예측)

    Args:
        df         : 데이터 DataFrame
        target_col : 타겟 열 이름

    Returns:
        "classification" (분류) 또는 "regression" (회귀)
    """
    n_unique = df[target_col].nunique()   # 고유값 개수
    is_num   = pd.api.types.is_numeric_dtype(df[target_col])

    # 문자형이거나 고유값이 10개 이하면 분류
    if not is_num or n_unique <= 10:
        task = "classification"
    else:
        task = "regression"

    logger.info(
        f"📋 태스크 유형 자동 판단: {task} "
        f"(고유값 {n_unique}개, 숫자형={is_num})"
    )
    return task


def get_column_info(df: pd.DataFrame) -> dict:
    """
    UI에서 Feature/Target 선택할 수 있도록 컬럼 정보 반환

    초등학생 설명:
        웹 화면에서 "어떤 열을 쓸지" 선택할 때 필요한
        컬럼 목록 정보를 정리해줘요.

    Args:
        df : 정보를 추출할 DataFrame

    Returns:
        {
            "all_columns":     모든 열 이름 목록,
            "numeric_columns": 숫자형 열 목록 (Feature로 추천),
            "text_columns":    문자형 열 목록,
            "suggested_target": 자동 탐지된 타겟 열,
            "row_count":       전체 행 수
        }

    사용 예시:
        info = get_column_info(df)
        # UI에서 드롭다운 메뉴에 info["all_columns"] 표시
    """
    return {
        "all_columns":      list(df.columns),
        "numeric_columns":  df.select_dtypes(include="number").columns.tolist(),
        "text_columns":     df.select_dtypes(exclude="number").columns.tolist(),
        "suggested_target": find_target(df),
        "row_count":        len(df),
    }

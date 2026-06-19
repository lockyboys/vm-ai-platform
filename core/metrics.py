# core/metrics.py ★ 7.16.4
# ⭐ 데이터 품질 점수 계산 모듈
#
# 초등학생 설명:
#   시험 채점하듯이 데이터가 얼마나 좋은지 점수를 매겨요!
#   빠진 값이 많을수록 점수가 낮아지고,
#   데이터 양이 많을수록 위험 점수가 올라가요.
#
# 등급 기준:
#   A (우수): 90점 이상
#   B (양호): 70~89점
#   C (보통): 50~69점
#   D (주의): 50점 미만
#
# [버전 이력]
#   7.16.4 (2026-06-16): 주석 강화, 등급 기준 명시
#   7.0.0  (2026-06-15): 최초 생성

from utils import logger


def calculate(analysis: dict) -> dict:
    """
    분석 결과를 받아 품질 점수와 등급 계산

    초등학생 설명:
        분석 결과를 보고 100점 만점으로 점수를 줘요!
        빠진 값이 많으면 점수가 깎여요.

    점수 계산 방식:
        데이터_품질_점수 = 100 - 총 결측값 개수 (최솟값 0)
        위험_점수       = min(100, 행수 ÷ 10)

    Args:
        analysis : core/analyzer.py의 run() 결과 딕셔너리

    Returns:
        {
            "데이터_품질_점수": 0~100 (높을수록 좋음),
            "위험_점수":       0~100 (높을수록 분석할 데이터 많음),
            "종합_등급":       "A(우수)" / "B(양호)" / "C(보통)" / "D(주의)"
        }

    사용 예시:
        from core.metrics import calculate
        score = calculate(analysis)
        # 결과: {"데이터_품질_점수": 95, "위험_점수": 15, "종합_등급": "A(우수)"}
    """
    # 분석 결과에서 필요한 값 추출
    rows         = analysis.get("총_행수", 0)
    missing_dict = analysis.get("빠진_값", {})
    total_missing = sum(missing_dict.values())   # 전체 결측값 합계

    # 품질 점수: 결측값이 많을수록 감점 (최솟값 0점)
    quality_score = max(0, 100 - total_missing)

    # 위험 점수: 데이터가 많을수록 높음 (최댓값 100점)
    # 초등학생 설명: 데이터가 많을수록 분석할 게 많아서 "위험 점수"가 올라가요
    risk_score = min(100, rows // 10)

    scores = {
        "데이터_품질_점수": quality_score,
        "위험_점수":       risk_score,
        "종합_등급":       _get_grade(quality_score),
    }

    logger.info(
        f"📊 점수 계산 완료: 품질={quality_score}점 | "
        f"위험={risk_score}점 | 등급={scores['종합_등급']}"
    )
    return scores


def _get_grade(score: int) -> str:
    """
    점수를 문자 등급으로 변환

    초등학생 설명:
        90점 이상은 A, 70점 이상은 B처럼
        숫자 점수를 글자 등급으로 바꿔줘요!

    Args:
        score : 0~100 사이의 점수

    Returns:
        "A(우수)" / "B(양호)" / "C(보통)" / "D(주의)"
    """
    if score >= 90:
        return "A(우수)"
    elif score >= 70:
        return "B(양호)"
    elif score >= 50:
        return "C(보통)"
    else:
        return "D(주의)"

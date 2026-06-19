# core/shap_service.py ★ 7.16.4
# ⭐ SHAP AI 설명 자동화 모듈
#
# 초등학생 설명:
#   AI가 왜 그런 결정을 했는지 그림으로 설명해줘요!
#   예: "이 사람이 위험한 이유는 나이(40%) + 흡연(35%) + 비만(25%) 때문이에요"
#   처럼 각 항목이 결과에 얼마나 영향을 줬는지 알려줘요.
#
# SHAP이란?
#   SHapley Additive exPlanations 의 약자예요.
#   AI가 "블랙박스"가 아니라 "왜 그랬는지" 설명하게 해줘요.
#
# [버전 이력]
#   7.16.4 (2026-06-16): 주석 강화, shap 미설치 시 안내 메시지 개선
#   7.0.0  (2026-06-15): 최초 생성

import os
from utils import logger
from config import OUTPUT_PATH


def generate_shap(model, X, output_path: str = None) -> str:
    """
    SHAP 요약 그래프 생성 후 PNG 파일로 저장

    초등학생 설명:
        AI가 "왜 이런 결과가 나왔는지" 막대그래프로 보여줘요.
        어떤 항목이 결과에 가장 크게 영향을 줬는지 한눈에 볼 수 있어요!

    Args:
        model       : 학습된 AI 모델 (sklearn 호환)
        X           : 입력 데이터 (pandas DataFrame)
        output_path : 저장할 PNG 파일 경로 (없으면 자동 설정)

    Returns:
        저장된 PNG 파일 경로 (실패 시 빈 문자열 반환)

    사용 예시:
        from core.shap_service import generate_shap
        path = generate_shap(model, X_test)
        print(f"그래프 저장됨: {path}")
    """
    try:
        import shap
        import matplotlib
        matplotlib.use("Agg")   # 화면 없이 파일로만 저장 (서버용 설정)
        import matplotlib.pyplot as plt

        # 저장 경로 자동 설정
        if output_path is None:
            output_path = os.path.join(OUTPUT_PATH, "charts", "shap_summary.png")

        # 저장 폴더 없으면 자동 생성
        os.makedirs(os.path.dirname(output_path), exist_ok=True)

        logger.info("🧠 SHAP 분석 시작...")

        # SHAP 값 계산
        # 초등학생 설명: AI한테 "왜 이렇게 결정했어?" 물어보는 과정이에요
        explainer   = shap.Explainer(model, X)
        shap_values = explainer(X)

        # 그래프 생성 및 저장
        plt.figure(figsize=(10, 6))
        shap.summary_plot(shap_values, X, show=False)
        plt.tight_layout()
        plt.savefig(output_path, dpi=150, bbox_inches="tight")
        plt.close()

        logger.info(f"✅ SHAP 그래프 저장 완료: {output_path}")
        return output_path

    except ImportError:
        # shap 라이브러리가 없을 때
        logger.warning("⚠️ shap 라이브러리 없음 → pip install shap 실행 후 사용 가능해요")
        return ""
    except Exception as e:
        logger.error(f"❌ SHAP 생성 실패: {e}")
        return ""


def get_feature_importance(model, feature_names: list) -> dict:
    """
    각 특성(열)의 중요도를 퍼센트로 계산

    초등학생 설명:
        "나이가 40%, 흡연이 35%, 비만이 25% 영향을 줬어요"
        처럼 어떤 항목이 AI 판단에 얼마나 중요한지 알려줘요.
        중요도 합계는 항상 100%예요!

    Args:
        model         : feature_importances_ 속성이 있는 모델
                        (RandomForest, GradientBoosting 등)
        feature_names : 특성 이름 목록 (예: ["나이", "BMI", "혈압"])

    Returns:
        {특성이름: 중요도%} 딕셔너리 (중요도 높은 순 정렬)

    사용 예시:
        importance = get_feature_importance(model, ["나이", "BMI"])
        # 결과: {"나이": 45.2, "BMI": 33.1, ...}

    주의:
        RandomForest, GradientBoosting 등만 지원
        LogisticRegression은 feature_importances_ 없음 → 빈 dict 반환
    """
    try:
        # 모델에서 각 특성의 중요도 추출
        importances = model.feature_importances_
        total       = sum(importances) or 1   # 0으로 나누기 방지

        # 퍼센트로 변환 후 중요도 높은 순 정렬
        importance_dict = {
            name: round(imp / total * 100, 2)
            for name, imp in zip(feature_names, importances)
        }
        sorted_dict = dict(sorted(
            importance_dict.items(),
            key=lambda x: -x[1]   # 내림차순 정렬
        ))

        logger.info(f"⚖️ 특성 중요도 계산 완료: {len(sorted_dict)}개 특성")
        return sorted_dict

    except AttributeError:
        # feature_importances_ 속성이 없는 모델 (LogisticRegression 등)
        logger.warning("⚠️ 이 모델은 특성 중요도를 지원하지 않아요 (RandomForest 권장)")
        return {}
    except Exception as e:
        logger.error(f"❌ 특성 중요도 계산 실패: {e}")
        return {}

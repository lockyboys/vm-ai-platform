# core/automl_engine.py ★ 7.20.0
# AutoML 엔진
# 초등학생 설명: 여러 AI 모델을 시험해보고, 시험 점수가 제일 좋은 모델을 골라줘요.

from typing import Dict, Any
from utils import logger


def run_automl(X_train, X_test, y_train, y_test, task_type: str = "classification") -> Dict[str, Any]:
    """여러 모델을 비교해서 가장 좋은 모델을 반환해요."""
    from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor, ExtraTreesClassifier, ExtraTreesRegressor
    from sklearn.linear_model import LogisticRegression, LinearRegression
    from sklearn.metrics import accuracy_score, r2_score

    if task_type == "regression":
        candidates = {
            "RandomForestRegressor": RandomForestRegressor(n_estimators=80, random_state=42),
            "ExtraTreesRegressor": ExtraTreesRegressor(n_estimators=80, random_state=42),
            "LinearRegression": LinearRegression(),
        }
        scorer = lambda model: r2_score(y_test, model.predict(X_test))
    else:
        candidates = {
            "RandomForestClassifier": RandomForestClassifier(n_estimators=80, random_state=42),
            "ExtraTreesClassifier": ExtraTreesClassifier(n_estimators=80, random_state=42),
            "LogisticRegression": LogisticRegression(max_iter=1000),
        }
        scorer = lambda model: accuracy_score(y_test, model.predict(X_test))

    best = {"model_name": None, "score": -999, "model": None, "all_scores": {}}
    for name, model in candidates.items():
        try:
            model.fit(X_train, y_train)
            score = float(scorer(model))
            best["all_scores"][name] = round(score, 4)
            logger.info(f"🤖 AutoML 모델 시험: {name} = {score:.4f}")
            if score > best["score"]:
                best.update({"model_name": name, "score": score, "model": model})
        except Exception as e:
            logger.warning(f"⚠️ AutoML 모델 스킵: {name} | {e}")
    return best

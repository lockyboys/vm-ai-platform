# ml/trainer.py ★ 7.16.4
# ⭐ 4가지 학습 방식 통합 엔진
# 🆕 지도학습 / 비지도학습 / 준지도학습 / 강화학습 전부 지원
# 초등학생 설명: AI를 4가지 방법으로 가르칠 수 있어요!
#   지도학습   = 문제+정답 같이 줘서 공부 (가장 일반적)
#   비지도학습 = 정답 없이 혼자 패턴 발견
#   준지도학습 = 일부만 정답 주고 나머지는 혼자 유추
#   강화학습   = 잘하면 칭찬, 못하면 벌칙으로 스스로 개선

import os, json, joblib
from datetime import datetime
from utils import logger
from config import MODEL_PATH
from services.db.db_service import save_model_history as save_model_history_db
from services.history_service import save_model_history


# ══════════════════════════════════════════════
# 1️⃣  지도학습 (Supervised Learning)
# ══════════════════════════════════════════════
def supervised_train(X, y, task_type: str = "classification",
                     feature_cols: list = None) -> dict:
    """
    지도학습 — 문제(X)와 정답(y)을 같이 줘서 학습
    초등학생 설명: 선생님이 문제랑 답을 같이 알려주면서 공부하는 방식이에요!
    가중치(어떤 특성이 중요한지)는 AI가 자동으로 계산해요.
    """
    from sklearn.model_selection import train_test_split
    from sklearn.preprocessing import StandardScaler
    from sklearn.metrics import accuracy_score, r2_score

    logger.info(f"🎓 지도학습 시작 | 태스크={task_type}")

    # 결측치 자동 처리
    import pandas as pd
    X = pd.DataFrame(X).fillna(X.mean() if hasattr(X, 'mean') else 0)

    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

    # AutoML: 여러 모델 자동 비교해서 가장 좋은 것 선택
    best_model, best_score, best_name = _automl_select(X_train, y_train, X_test, y_test, task_type)

    # 특성 중요도(가중치) — AI가 자동 계산
    importance = {}
    if hasattr(best_model, "feature_importances_") and feature_cols:
        imps  = best_model.feature_importances_
        total = sum(imps) or 1
        importance = dict(sorted(
            {c: round(i/total*100, 2) for c, i in zip(feature_cols, imps)}.items(),
            key=lambda x: -x[1]
        ))

    path = _save_model(best_model, best_name)

    # DB + JSON 파일로 학습 이력 저장 (DB 없어도 JSON 파일에 항상 기록!)
    save_model_history_db(best_name, task_type, "supervised", best_score,
                          feature_cols or [], str(y.name if hasattr(y, 'name') else "target"))
    save_model_history(best_name, task_type, "supervised", best_score,
                       feature_cols or [], str(y.name if hasattr(y, 'name') else "target"))

    logger.info(f"✅ 지도학습 완료 | 모델={best_name} | 정확도={best_score:.3f}")
    return {
        "학습방식": "지도학습",
        "모델명": best_name,
        "정확도": round(best_score, 4),
        "특성_중요도(AI자동계산)": importance,
        "모델_경로": path,
        "태스크": task_type,
    }


def _automl_select(X_train, y_train, X_test, y_test, task_type):
    """
    AutoML — 여러 모델을 자동으로 시험해서 가장 좋은 것 선택
    초등학생 설명: 여러 선생님한테 가르쳐달라고 해보고 제일 잘 가르쳐주는 선생님 고르기!
    """
    from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor, GradientBoostingClassifier, GradientBoostingRegressor
    from sklearn.linear_model import LogisticRegression, Ridge
    from sklearn.metrics import accuracy_score, r2_score

    if task_type == "classification":
        candidates = {
            "RandomForest":       RandomForestClassifier(n_estimators=100, random_state=42),
            "GradientBoosting":   GradientBoostingClassifier(n_estimators=100, random_state=42),
            "LogisticRegression": LogisticRegression(max_iter=500, random_state=42),
        }
        score_fn = accuracy_score
    else:
        candidates = {
            "RandomForestRegressor":     RandomForestRegressor(n_estimators=100, random_state=42),
            "GradientBoostingRegressor": GradientBoostingRegressor(n_estimators=100, random_state=42),
            "Ridge":                     Ridge(),
        }
        score_fn = r2_score

    best_model, best_score, best_name = None, -999, ""
    for name, model in candidates.items():
        try:
            model.fit(X_train, y_train)
            score = score_fn(y_test, model.predict(X_test))
            logger.info(f"  🔬 {name}: {score:.3f}")
            if score > best_score:
                best_model, best_score, best_name = model, score, name
        except Exception as e:
            logger.warning(f"  ⚠️ {name} 실패: {e}")

    return best_model, best_score, best_name


# ══════════════════════════════════════════════
# 2️⃣  비지도학습 (Unsupervised Learning)
# ══════════════════════════════════════════════
def unsupervised_train(X, n_clusters: int = 3, feature_cols: list = None) -> dict:
    """
    비지도학습 — 정답 없이 혼자 패턴/그룹 발견
    초등학생 설명: 선생님 없이 혼자서 비슷한 것끼리 묶는 공부예요!
    예: 건강 데이터에서 "건강한 그룹", "보통 그룹", "위험 그룹" 자동 발견
    """
    from sklearn.cluster import KMeans
    from sklearn.preprocessing import StandardScaler
    from sklearn.metrics import silhouette_score
    import pandas as pd

    logger.info(f"🔍 비지도학습 시작 | 클러스터={n_clusters}")

    X_df = pd.DataFrame(X).fillna(0)
    scaler = StandardScaler()
    X_scaled = scaler.fit_transform(X_df)

    # 최적 클러스터 수 자동 탐색 (2~8개 중)
    best_k, best_score_val, best_model = n_clusters, -1, None
    for k in range(2, min(9, len(X_df))):
        try:
            km    = KMeans(n_clusters=k, random_state=42, n_init=10)
            labels = km.fit_predict(X_scaled)
            if len(set(labels)) > 1:
                s = silhouette_score(X_scaled, labels)
                if s > best_score_val:
                    best_k, best_score_val, best_model = k, s, km
        except Exception:
            continue

    labels     = best_model.labels_
    cluster_dist = {f"그룹_{i}": int((labels==i).sum()) for i in range(best_k)}

    path = _save_model(best_model, "KMeans")
    save_model_history("KMeans", "clustering", "unsupervised",
                       best_score_val, feature_cols or [], "없음(비지도)")

    logger.info(f"✅ 비지도학습 완료 | 최적클러스터={best_k} | Silhouette={best_score_val:.3f}")
    return {
        "학습방식": "비지도학습",
        "모델명": "KMeans",
        "최적_클러스터수": best_k,
        "실루엣_점수": round(best_score_val, 4),
        "클러스터_분포": cluster_dist,
        "모델_경로": path,
    }


# ══════════════════════════════════════════════
# 3️⃣  준지도학습 (Semi-Supervised Learning)
# ══════════════════════════════════════════════
def semi_supervised_train(X, y_partial, feature_cols: list = None) -> dict:
    """
    준지도학습 — 일부만 정답, 나머지는 AI가 유추
    초등학생 설명: 문제 100개 중 30개만 답을 알려주면, 나머지 70개 답을 스스로 맞춰요!
    레이블 없는 데이터는 -1로 표시해주세요.
    """
    from sklearn.semi_supervised import LabelPropagation
    from sklearn.metrics import accuracy_score
    import pandas as pd, numpy as np

    logger.info("🔀 준지도학습 시작")

    X_df = pd.DataFrame(X).fillna(0)
    y    = pd.Series(y_partial)

    labeled_mask   = y != -1
    labeled_count  = labeled_mask.sum()
    total_count    = len(y)

    logger.info(f"  라벨 있음: {labeled_count}개 / 전체: {total_count}개")

    model  = LabelPropagation(kernel="rbf", max_iter=1000)
    model.fit(X_df.values, y.values)

    # 라벨 있는 데이터로만 정확도 측정
    acc = accuracy_score(y[labeled_mask], model.predict(X_df[labeled_mask].values))

    path = _save_model(model, "LabelPropagation")
    save_model_history("LabelPropagation", "classification", "semi_supervised",
                       acc, feature_cols or [], "partial_label")

    logger.info(f"✅ 준지도학습 완료 | 정확도={acc:.3f}")
    return {
        "학습방식": "준지도학습",
        "모델명": "LabelPropagation",
        "정확도(라벨있는데이터)": round(acc, 4),
        "라벨있는_데이터수": int(labeled_count),
        "전체_데이터수": total_count,
        "모델_경로": path,
    }


# ══════════════════════════════════════════════
# 4️⃣  강화학습 (Reinforcement Learning)
# ══════════════════════════════════════════════
def reinforcement_train(X, y, feature_cols: list = None, episodes: int = 50) -> dict:
    """
    강화학습 — 잘하면 보상, 못하면 벌칙으로 스스로 개선
    초등학생 설명: 게임에서 점수를 올리듯, AI가 스스로 더 좋은 방법을 찾아가요!
    여기서는 하이퍼파라미터를 보상 신호로 자동 최적화해요.
    """
    from sklearn.ensemble import RandomForestClassifier
    from sklearn.model_selection import cross_val_score
    import numpy as np, pandas as pd

    logger.info(f"🎮 강화학습 시작 | 에피소드={episodes}")

    X_df = pd.DataFrame(X).fillna(0)
    y_s  = pd.Series(y)

    # 하이퍼파라미터 탐색 공간 (행동 공간)
    param_space = {
        "n_estimators": [50, 100, 150, 200],
        "max_depth":    [3, 5, 7, 10, None],
        "min_samples_split": [2, 5, 10],
    }

    best_score_val, best_params, history = 0, {}, []

    import random
    for ep in range(min(episodes, 20)):  # 최대 20 에피소드
        # 랜덤 행동 (하이퍼파라미터 선택)
        params = {k: random.choice(v) for k, v in param_space.items()}
        try:
            model = RandomForestClassifier(**params, random_state=42)
            score = cross_val_score(model, X_df, y_s, cv=3, scoring="accuracy").mean()

            # 보상: 이전보다 좋으면 +1, 나쁘면 -1
            reward = 1 if score > best_score_val else -1
            history.append({"에피소드": ep+1, "점수": round(score,4), "보상": reward, "파라미터": params})

            if score > best_score_val:
                best_score_val, best_params = score, params
                logger.info(f"  🏆 에피소드 {ep+1}: 최고점 갱신! {score:.3f}")
        except Exception as e:
            logger.warning(f"  ⚠️ 에피소드 {ep+1} 실패: {e}")

    # 최적 파라미터로 최종 학습
    final_model = RandomForestClassifier(**best_params, random_state=42)
    final_model.fit(X_df, y_s)
    path = _save_model(final_model, "RL_OptimizedRF")

    save_model_history("RL_OptimizedRF", "classification", "reinforcement",
                       best_score_val, feature_cols or [], str(y_s.name or "target"))

    logger.info(f"✅ 강화학습 완료 | 최적정확도={best_score_val:.3f} | 최적파라미터={best_params}")
    return {
        "학습방식": "강화학습",
        "모델명": "RL_OptimizedRF",
        "최적_정확도": round(best_score_val, 4),
        "최적_파라미터": best_params,
        "학습_히스토리": history[-10:],  # 마지막 10개만
        "모델_경로": path,
    }


# ══════════════════════════════════════════════
# 공통 유틸
# ══════════════════════════════════════════════
def _save_model(model, name: str) -> str:
    """모델 버전 관리 저장"""
    os.makedirs(MODEL_PATH, exist_ok=True)
    ts   = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = os.path.join(MODEL_PATH, f"{name}_{ts}.pkl")
    joblib.dump(model, path)
    joblib.dump(model, os.path.join(MODEL_PATH, "latest_model.pkl"))
    logger.info(f"💾 모델 저장: {path}")
    return path

def load_model():
    path = os.path.join(MODEL_PATH, "latest_model.pkl")
    if not os.path.exists(path):
        logger.warning("⚠️ 저장된 모델 없음")
        return None
    return joblib.load(path)

def auto_retrain(df, target_col: str = None, feature_cols: list = None,
                 learning_type: str = "supervised") -> dict:
    """
    학습 방식 선택 후 자동 재학습
    초등학생 설명: 새 데이터가 생기면 자동으로 AI를 다시 훈련해요!
    """
    import pandas as pd
    from core.target_detector import find_target, get_task_type

    if target_col is None:
        target_col = find_target(df)
    if feature_cols is None:
        feature_cols = [c for c in df.select_dtypes(include="number").columns if c != target_col]

    X = df[feature_cols]
    task_type = get_task_type(df, target_col)

    if learning_type == "supervised":
        y = df[target_col]
        return supervised_train(X, y, task_type, feature_cols)
    elif learning_type == "unsupervised":
        return unsupervised_train(X, feature_cols=feature_cols)
    elif learning_type == "semi_supervised":
        import numpy as np
        y = df[target_col].copy()
        # 50% 랜덤으로 라벨 제거 (데모)
        mask = np.random.rand(len(y)) < 0.5
        y[mask] = -1
        return semi_supervised_train(X, y, feature_cols)
    elif learning_type == "reinforcement":
        y = df[target_col]
        return reinforcement_train(X, y, feature_cols)
    else:
        return supervised_train(X, df[target_col], task_type, feature_cols)

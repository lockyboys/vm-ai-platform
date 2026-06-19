# pipeline.py ★ 7.16.4 — 전체 AI 시스템 핵심 엔진
# ⭐ 지도/비지도/준지도/강화학습 + AutoML + SHAP + AGI + DB 전부 통합
# 초등학생 설명: 공장 컨베이어 벨트처럼 데이터가 들어오면 자동으로 분석→학습→저장→리포트!
import time, os
import pandas as pd
from utils import logger, log_event, get_timestamp, ensure_dirs, read_file_auto, file_hash
from config import DATA_PATH, UPLOAD_PATH
from core.analyzer       import run as analyze
from core.metrics        import calculate
from core.shap_service   import generate_shap, get_feature_importance
from ml.trainer          import auto_retrain
from agents.orchestrator import AGIOrchestrator
from agents.self_improve_agent import SelfImproveAgent
from services.db.db_service import save_both, save_pipeline_result
from services.history_service import save_pipeline_history, save_model_history

_orch     = None
_improver = SelfImproveAgent()

def get_orchestrator():
    global _orch
    if _orch is None:
        _orch = AGIOrchestrator()
    return _orch

def run_pipeline(file_path: str = None, user_id: str = "anonymous",
                 target_col: str = None, feature_cols: list = None,
                 learning_type: str = "supervised") -> dict:
    """
    전체 AI 파이프라인 실행
    초등학생 설명: 재료(데이터)를 넣으면 결과(분석+학습+리포트)가 자동으로 나와요!

    파라미터:
        file_path     : CSV 파일 경로 (None이면 기본 데이터 사용)
        user_id       : 사용자 ID
        target_col    : 정답 열 이름 (None이면 자동 탐지)
        feature_cols  : 학습에 쓸 열 목록 (None이면 자동 선택)
        learning_type : supervised / unsupervised / semi_supervised / reinforcement
    """
    start = time.time()
    ensure_dirs()
    logger.info(f"🚀 7.20.0 파이프라인 시작 | user={user_id} | 학습방식={learning_type}")

    # ── 1. 파일 로드 ──────────────────────────────────────
    if file_path is None:
        file_path = os.path.join(DATA_PATH, "smoking_health_data.csv")
    if not os.path.exists(file_path):
        return {"error": f"파일 없음: {file_path}"}

    df = read_file_auto(file_path)
    fhash = file_hash(file_path)
    logger.info(f"📂 데이터 로드: {len(df)}행 {len(df.columns)}열")

    # ── 2. 분석 ───────────────────────────────────────────
    analysis = analyze(df, target_col=target_col, feature_cols=feature_cols)
    score    = calculate(analysis)

    # 분석 결과에서 타겟/피처 가져오기
    auto_target   = analysis["타겟_열"]
    auto_features = analysis["피처_열"]

    # ── 3. AI 학습 ────────────────────────────────────────
    ml_result  = {}
    shap_path  = ""
    importance = {}
    accuracy   = 0.0

    try:
        ml_result = auto_retrain(df,
                                 target_col    = auto_target,
                                 feature_cols  = auto_features,
                                 learning_type = learning_type)
        accuracy  = ml_result.get("정확도", ml_result.get("실루엣_점수", 0.0)) or 0.0

        # SHAP (지도/강화학습만)
        if learning_type in ("supervised", "reinforcement") and accuracy > 0:
            from ml.trainer import load_model
            model = load_model()
            if model and auto_features:
                X = df[auto_features].fillna(0)
                shap_path  = generate_shap(model, X)
                importance = get_feature_importance(model, auto_features)
    except Exception as e:
        logger.error(f"❌ 학습 실패: {e}")
        ml_result = {"error": str(e)}

    # ── 4. 자기개선 에이전트 ──────────────────────────────
    improve_result = {}
    if accuracy > 0 and learning_type == "supervised":
        improve_result = _improver.review(accuracy, analysis["태스크_유형"])

    # ── 5. AGI 종합 판단 ──────────────────────────────────
    agi_result = get_orchestrator().run(
        "데이터 분석 및 인사이트 도출",
        {"analysis": analysis, "score": score, "accuracy": accuracy}
    )

    # ── 6. PDF 리포트 생성 ────────────────────────────────
    pdf_path = _generate_pdf(analysis, score, ml_result, importance, user_id)

    # ── 7. 결과 정리 ──────────────────────────────────────
    elapsed = round(time.time() - start, 2)
    result  = {
        "user_id":        user_id,
        "파일":           os.path.basename(file_path),
        "파일_해시":      fhash,
        "학습_방식":      learning_type,
        "타겟_열":        auto_target,
        "피처_열":        auto_features,
        "분석결과":       analysis,
        "점수":           score,
        "ML결과":         ml_result,
        "특성_중요도":    importance,
        "SHAP_경로":      shap_path,
        "PDF_경로":       pdf_path,
        "자기개선":       improve_result,
        "AGI_판단":       agi_result.get("결과", {}),
        "처리시간_초":    elapsed,
        "완료시각":       get_timestamp(),
    }

    # ── 8. DB 저장 ────────────────────────────────────────
    db_status = save_both("pipeline_results", {
        k: v for k, v in result.items()
        if not isinstance(v, (dict, list)) or k in ("점수", "ML결과")
    })
    save_pipeline_result(user_id, os.path.basename(file_path),
                         analysis.get("태스크_유형", "classification"),
                         learning_type, accuracy, result)
    result["DB_저장"] = db_status

    # 🆕 JSON 파일로 이력 저장 (DB 없어도 항상 남음!)
    save_pipeline_history(
        user_id       = user_id,
        file_name     = os.path.basename(file_path),
        task_type     = analysis.get("태스크_유형","classification"),
        learning_type = learning_type,
        accuracy      = accuracy,
        elapsed       = elapsed,
        result        = result,
    )
    log_event("pipeline_7.20.0", {"user": user_id, "accuracy": accuracy, "elapsed": elapsed})
    logger.info(f"🎉 파이프라인 완료! {elapsed}초 | 정확도={accuracy:.3f}")
    return result


def _generate_pdf(analysis, score, ml_result, importance, user_id) -> str:
    """PDF 리포트 자동 생성"""
    try:
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
        from reportlab.lib.styles import getSampleStyleSheet
        from reportlab.lib import colors
        from reportlab.lib.pagesizes import A4
        import os
        from config import OUTPUT_PATH
        from utils import get_ts_file

        path   = os.path.join(OUTPUT_PATH, "reports", f"report_{user_id}_{get_ts_file()}.pdf")
        doc    = SimpleDocTemplate(path, pagesize=A4)
        styles = getSampleStyleSheet()
        story  = []

        story.append(Paragraph("🧠 VM Project 7.20.0 AI 분석 리포트", styles["Title"]))
        story.append(Spacer(1, 12))
        story.append(Paragraph(f"생성 시각: {get_timestamp()}", styles["Normal"]))
        story.append(Paragraph(f"사용자: {user_id}", styles["Normal"]))
        story.append(Spacer(1, 12))

        story.append(Paragraph("📊 데이터 요약", styles["Heading2"]))
        data = [["항목", "값"],
                ["행 수",   str(analysis.get("총_행수", ""))],
                ["열 수",   str(analysis.get("총_열수", ""))],
                ["타겟 열", str(analysis.get("타겟_열", ""))],
                ["태스크",  str(analysis.get("태스크_유형", ""))],
                ["데이터 품질", str(score.get("데이터_품질_점수", ""))],
                ["종합 등급", str(score.get("종합_등급", ""))]]
        t = Table(data, colWidths=[200, 250])
        t.setStyle(TableStyle([
            ("BACKGROUND", (0,0), (-1,0), colors.HexColor("#7c3aed")),
            ("TEXTCOLOR",  (0,0), (-1,0), colors.white),
            ("GRID",       (0,0), (-1,-1), 0.5, colors.grey),
            ("ROWBACKGROUNDS", (0,1), (-1,-1), [colors.white, colors.HexColor("#f3f0ff")]),
        ]))
        story.append(t)
        story.append(Spacer(1, 12))

        if ml_result and "정확도" in ml_result:
            story.append(Paragraph("🤖 AI 학습 결과", styles["Heading2"]))
            story.append(Paragraph(f"모델: {ml_result.get('모델명','')}", styles["Normal"]))
            story.append(Paragraph(f"정확도: {ml_result.get('정확도', 0):.2%}", styles["Normal"]))

        if importance:
            story.append(Spacer(1, 12))
            story.append(Paragraph("⚖️ 특성 중요도 (AI 자동 계산)", styles["Heading2"]))
            for feat, val in list(importance.items())[:10]:
                story.append(Paragraph(f"  • {feat}: {val}%", styles["Normal"]))

        doc.build(story)
        logger.info(f"📄 PDF 생성: {path}")
        return path
    except Exception as e:
        logger.warning(f"⚠️ PDF 생성 실패: {e}")
        return ""

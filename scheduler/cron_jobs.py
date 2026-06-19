# scheduler/cron_jobs.py ★ 7.16.4
# ⭐ Cron 자동 스케줄러 — 데이터가 쌓일수록 자동으로 재학습해서 정확도 향상!
# 초등학생 설명: 알람시계처럼 정해진 시간에 AI가 자동으로 공부해요!
# 🆕 crontab 자동 등록 기능 포함

import os, sys, time
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils import logger, log_event, get_timestamp
from config import DATA_PATH, LOG_PATH
from services.db.db_service import get_model_history

# ── 스케줄 작업 정의 ──────────────────────────────────────

def job_daily_retrain():
    """
    매일 새벽 2시 자동 재학습
    초등학생 설명: 밤에 자는 동안 AI가 자동으로 공부해서 다음 날 더 똑똑해져요!
    모든 학습 방식(4가지)을 순서대로 실행해요.
    """
    logger.info("⏰ [CRON] 일일 자동 재학습 시작")
    data_file = os.path.join(DATA_PATH, "smoking_health_data.csv")

    if not os.path.exists(data_file):
        logger.warning("⚠️ [CRON] 학습 데이터 없음 — 건너뜀")
        _log_cron("daily_retrain", "스킵", "데이터 파일 없음")
        return

    from pipeline import run_pipeline
    results = {}

    for ltype in ["supervised", "unsupervised", "semi_supervised", "reinforcement"]:
        try:
            logger.info(f"  🔄 {ltype} 재학습 중...")
            r = run_pipeline(file_path=data_file, user_id="cron", learning_type=ltype)
            acc = r.get("ML결과", {}).get("정확도",
                  r.get("ML결과", {}).get("실루엣_점수",
                  r.get("ML결과", {}).get("최적_정확도", 0))) or 0
            results[ltype] = round(float(acc), 4)
            logger.info(f"  ✅ {ltype} 완료 | 정확도={acc:.3f}")
        except Exception as e:
            results[ltype] = f"실패: {e}"
            logger.error(f"  ❌ {ltype} 실패: {e}")

    _log_cron("daily_retrain", "완료", str(results))
    logger.info(f"🎉 [CRON] 일일 재학습 완료: {results}")


def job_self_improve():
    """
    3시간마다 자기개선 에이전트 실행
    초등학생 설명: 3시간마다 "지금보다 더 잘할 수 있을까?" 체크하고 개선해요!
    """
    logger.info("🧠 [CRON] 자기개선 체크")
    history = get_model_history(limit=5)
    if not history:
        logger.info("  ℹ️ 학습 이력 없음")
        return

    from agents.self_improve_agent import SelfImproveAgent
    latest_acc = history[0].get("accuracy", 0) if history else 0
    agent      = SelfImproveAgent()
    review     = agent.review(latest_acc)
    logger.info(f"  📊 자기개선 분석: {review['권장_행동']} | 추세={review['정확도_추세']}")
    _log_cron("self_improve", "완료", str(review))


def job_hourly_health_check():
    """
    매시간 시스템 상태 확인
    초등학생 설명: 1시간마다 "모든 게 잘 돌아가고 있나?" 확인해요.
    """
    import subprocess
    services = {"flask": 8000, "mongodb": 27017, "mariadb": 3306}
    status   = {}
    for name, port in services.items():
        result = subprocess.run(["ss", "-tlnp"], capture_output=True, text=True)
        status[name] = "정상" if str(port) in result.stdout else "오프라인"
    logger.info(f"💓 [CRON] 상태확인: {status}")
    _log_cron("health_check", "완료", str(status))


def job_weekly_report():
    """
    매주 월요일 오전 9시 — 주간 정확도 리포트 생성
    초등학생 설명: 매주 "이번 주 AI가 얼마나 향상됐는지" 리포트를 만들어요!
    """
    logger.info("📊 [CRON] 주간 리포트 생성")
    history = get_model_history(limit=50)
    if not history:
        return

    scores = [h.get("accuracy", 0) for h in history]
    report = {
        "주간_평균_정확도": round(sum(scores)/len(scores), 4),
        "최고_정확도":     round(max(scores), 4),
        "최저_정확도":     round(min(scores), 4),
        "총_학습_횟수":    len(history),
        "생성시각":        get_timestamp(),
    }
    from utils import save_json
    from config import OUTPUT_PATH
    save_json(os.path.join(OUTPUT_PATH, "reports", "weekly_report.json"), report)
    _log_cron("weekly_report", "완료", str(report))
    logger.info(f"✅ [CRON] 주간 리포트: {report}")


def _log_cron(job_name: str, status: str, message: str):
    """
    Cron 실행 이력을 DB + JSON 파일 동시 저장
    초등학생 설명: DB가 없어도 JSON 파일에 항상 기록이 남아요!
    """
    # 1. JSON 파일 저장 (무조건!)
    from services.history_service import save_cron_history
    save_cron_history(job_name, status, message)

    # 2. DB 저장 (있으면 추가 저장)
    try:
        import mysql.connector
        from config import MYSQL_CONFIG
        conn   = mysql.connector.connect(**MYSQL_CONFIG)
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO cron_logs (job_name, status, message) VALUES (%s,%s,%s)",
            (job_name, status, message[:500])
        )
        conn.commit(); cursor.close(); conn.close()
    except Exception as e:
        logger.warning(f"⚠️ cron_log DB 저장 실패 (JSON에는 저장됨): {e}")

    log_event(f"cron_{job_name}", {"status": status, "message": message})


# ── 스케줄러 실행 ─────────────────────────────────────────

def start_scheduler():
    """
    스케줄러 시작 — schedule 라이브러리 사용
    초등학생 설명: 알람을 여러 개 맞춰두는 것처럼 자동 작업을 등록해요!
    """
    try:
        import schedule
    except ImportError:
        logger.error("❌ schedule 미설치. pip install schedule")
        return

    # 작업 등록
    schedule.every().day.at("02:00").do(job_daily_retrain)       # 매일 새벽 2시
    schedule.every(3).hours.do(job_self_improve)                  # 3시간마다
    schedule.every().hour.do(job_hourly_health_check)             # 매시간
    schedule.every().monday.at("09:00").do(job_weekly_report)     # 매주 월요일

    logger.info("⏰ 스케줄러 등록 완료:")
    logger.info("  매일 02:00 → 4가지 학습 방식 자동 재학습")
    logger.info("  3시간마다 → 자기개선 에이전트")
    logger.info("  매시간    → 시스템 상태 확인")
    logger.info("  매주 월요일 09:00 → 주간 정확도 리포트")

    while True:
        schedule.run_pending()
        time.sleep(30)


def register_crontab():
    """
    🆕 crontab에 자동 등록
    초등학생 설명: 서버에 "이 시간에 이 일을 자동으로 해줘!" 등록하는 함수예요.
    실행: python -c "from scheduler.cron_jobs import register_crontab; register_crontab()"
    """
    import subprocess, os
    script_path = os.path.abspath(__file__)
    python_path = sys.executable
    project_dir = os.path.dirname(os.path.dirname(script_path))

    cron_entries = [
        f"0 2 * * * cd {project_dir} && {python_path} -c 'from scheduler.cron_jobs import job_daily_retrain; job_daily_retrain()' >> {project_dir}/logs/cron.log 2>&1",
        f"0 */3 * * * cd {project_dir} && {python_path} -c 'from scheduler.cron_jobs import job_self_improve; job_self_improve()' >> {project_dir}/logs/cron.log 2>&1",
        f"0 * * * * cd {project_dir} && {python_path} -c 'from scheduler.cron_jobs import job_hourly_health_check; job_hourly_health_check()' >> {project_dir}/logs/cron.log 2>&1",
        f"0 9 * * 1 cd {project_dir} && {python_path} -c 'from scheduler.cron_jobs import job_weekly_report; job_weekly_report()' >> {project_dir}/logs/cron.log 2>&1",
    ]

    current = subprocess.run(["crontab", "-l"], capture_output=True, text=True).stdout
    new_entries = [e for e in cron_entries if e not in current]
    if not new_entries:
        print("✅ crontab 이미 등록됨")
        return

    new_cron = current + "\n".join(new_entries) + "\n"
    proc = subprocess.run(["crontab", "-"], input=new_cron, text=True, capture_output=True)
    if proc.returncode == 0:
        print(f"✅ crontab 등록 완료! ({len(new_entries)}개 작업)")
        for e in new_entries:
            print(f"  {e}")
    else:
        print(f"❌ crontab 등록 실패: {proc.stderr}")


if __name__ == "__main__":
    start_scheduler()

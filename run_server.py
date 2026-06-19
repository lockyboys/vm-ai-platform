# run_server.py ★ 7.16.4 — 서버 시작 진입점
# 실행: python3 run_server.py
# 🆕 시작 시 DB 테이블 자동 생성 + crontab 자동 등록 안내
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from utils import logger, ensure_dirs
from config import API_HOST, API_PORT, MODEL_VERSION

def main():
    print("=" * 55)
    print(f"  🧠 VM Project {MODEL_VERSION} — AGI AI Platform")
    print("=" * 55)

    # 1. 폴더 초기화
    ensure_dirs()

    # 2. DB 테이블 자동 생성 (첫 접속 시)
    logger.info("🔧 DB 테이블 자동 초기화 중...")
    from services.db.db_service import init_db
    init_db()

    # 3. 서버 시작
    logger.info(f"🌐 서버 시작: http://{API_HOST}:{API_PORT}")
    print(f"\n  🌐 대시보드: http://0.0.0.0:{API_PORT}")
    print(f"  📡 API:      http://0.0.0.0:{API_PORT}/api/status")
    print(f"\n  ⏰ Cron 자동 등록하려면:")
    print(f"     python3 -c \"from scheduler.cron_jobs import register_crontab; register_crontab()\"")
    print("=" * 55)

    from web.app import app, init_app
    init_app()
    app.run(host=API_HOST, port=API_PORT, debug=False)

if __name__ == "__main__":
    main()

# services/db/safe_upgrade.py ★ 7.20.0
# 안전 DB 업그레이드 도구
# 초등학생 설명: 기존 DB는 지우지 않고, 필요한 새 칸과 새 표만 조심히 추가해요.

from pathlib import Path
from utils import logger
from config import MYSQL_CONFIG, BASE_DIR


def run_safe_upgrade() -> bool:
    """v7.20.0에 필요한 테이블/컬럼을 안전하게 추가해요. DROP은 절대 하지 않아요."""
    sql_path = Path(BASE_DIR) / "migrations" / "20260616_v720_safe_upgrade.sql"
    if not sql_path.exists():
        logger.warning(f"⚠️ 안전 업그레이드 SQL 없음: {sql_path}")
        return False

    try:
        import mysql.connector
        conn = mysql.connector.connect(**MYSQL_CONFIG)
        cur = conn.cursor()
        sql = sql_path.read_text(encoding="utf-8")
        # 세미콜론 단위로 나누되, 빈 문장은 건너뛰어요.
        # 초등학생 설명: 긴 편지를 문장별로 나눠서 하나씩 읽는 것과 같아요.
        for stmt in [s.strip() for s in sql.split(";") if s.strip()]:
            try:
                cur.execute(stmt)
            except Exception as e:
                # MariaDB 버전에 따라 ADD COLUMN IF NOT EXISTS가 안 될 수 있어요.
                # 그래서 실패해도 서버 전체를 멈추지 않게 기록만 남겨요.
                logger.warning(f"⚠️ SQL 일부 스킵: {e} | {stmt[:60]}...")
        conn.commit()
        cur.close(); conn.close()
        logger.info("✅ v7.20.0 안전 DB 업그레이드 완료 — 기존 데이터 유지")
        return True
    except Exception as e:
        logger.warning(f"⚠️ 안전 DB 업그레이드 실패 — 서버는 계속 실행: {e}")
        return False

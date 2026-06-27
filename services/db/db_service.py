# services/db/db_service.py ★ 7.16.4
# ⭐ DB 저장 서비스 — MongoDB + MariaDB 통합
# 🆕 7.16.4: 권한별 샘플 사용자 데이터 자동 초기화
#
# 초등학생 설명:
#   서랍장(MongoDB)과 엑셀(MariaDB) 두 곳에 동시에 저장해요!
#   처음 시작할 때 테스트용 계정도 자동으로 만들어줘요.
#
# [기본 제공 테스트 계정]
#   free@test.com       / test1234  → Free 플랜
#   pro@test.com        / test1234  → Pro 플랜
#   enterprise@test.com / test1234  → Enterprise 플랜
#   admin@test.com      / admin1234 → Enterprise (관리자)
#
# [버전 이력]
#   7.16.4 (2026-06-16): 권한별 샘플 사용자 데이터 추가
#   7.10.1 (2026-06-16): Cron 조회 권한 분리
#   7.10.0 (2026-06-15): 최초 생성

import json
from utils import logger
# from config import MONGO_URI, MONGO_DB, MYSQL_CONFIG
from config import MYSQL_CONFIG

# ─────────────────────────────────────────────────────────────────────────────
# 🗄️ MariaDB 테이블 자동 생성 DDL
# 초등학생 설명: 처음 집에 들어갈 때 방이 없으면 자동으로 방을 만들어줘요!
# ─────────────────────────────────────────────────────────────────────────────
INIT_SQL = """
CREATE TABLE IF NOT EXISTS users (
    id          INT AUTO_INCREMENT PRIMARY KEY,
    email       VARCHAR(255) UNIQUE NOT NULL     COMMENT '이메일 (로그인 ID)',
    password    VARCHAR(255) NOT NULL             COMMENT 'SHA-256 암호화 비밀번호',
    plan        VARCHAR(50)  DEFAULT 'free'       COMMENT '플랜: free/pro/enterprise',
    is_active   TINYINT(1)   DEFAULT 1           COMMENT '활성 여부 (1=활성, 0=비활성)',
    last_login  TIMESTAMP    NULL                 COMMENT '마지막 로그인 시각',
    created_at  TIMESTAMP    DEFAULT CURRENT_TIMESTAMP COMMENT '가입일'
);

CREATE TABLE IF NOT EXISTS pipeline_results (
    id          INT AUTO_INCREMENT PRIMARY KEY,
    user_id     VARCHAR(100)                     COMMENT '사용자 ID',
    file_name   VARCHAR(255)                     COMMENT '분석한 파일명',
    task_type   VARCHAR(50)                      COMMENT '태스크 유형 (classification/regression)',
    learning_type VARCHAR(50)                    COMMENT '학습 방식',
    accuracy    FLOAT                            COMMENT '정확도 (0~1)',
    data_json   MEDIUMTEXT                       COMMENT '전체 결과 JSON',
    created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS uploaded_files (
    id          INT AUTO_INCREMENT PRIMARY KEY,
    user_id     VARCHAR(100)                     COMMENT '업로드한 사용자 ID',
    file_name   VARCHAR(255)                     COMMENT '파일명',
    file_hash   VARCHAR(64) UNIQUE               COMMENT 'MD5 해시 (중복 감지 — UNIQUE로 같은 파일 1개만!)',
    save_path   VARCHAR(500)                     COMMENT '실제 저장 경로',
    row_count   INT                              COMMENT '행 수',
    col_count   INT                              COMMENT '열 수',
    col_info    TEXT                             COMMENT '컬럼 정보 JSON',
    plan        VARCHAR(50)                      COMMENT '업로드 시 플랜',
    uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY  uq_hash (file_hash)              -- 같은 파일 중복 방지!
);

CREATE TABLE IF NOT EXISTS model_history (
    id            INT AUTO_INCREMENT PRIMARY KEY,
    user_id       VARCHAR(100)                   COMMENT '학습한 사용자 ID',
    model_name    VARCHAR(100)                   COMMENT '모델 이름',
    task_type     VARCHAR(50)                    COMMENT '태스크 유형',
    learning_type VARCHAR(50)                    COMMENT '학습 방식',
    accuracy      FLOAT                          COMMENT '정확도',
    features      TEXT                           COMMENT '사용된 특성 목록 (JSON)',
    target_col    VARCHAR(100)                   COMMENT '타겟 열 이름',
    plan          VARCHAR(50)                    COMMENT '학습 시 플랜',
    trained_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS cron_logs (
    id        INT AUTO_INCREMENT PRIMARY KEY,
    job_name  VARCHAR(100)                       COMMENT 'Cron 작업 이름',
    status    VARCHAR(50)                        COMMENT '실행 결과 (완료/실패/스킵)',
    message   TEXT                               COMMENT '상세 메시지',
    ran_at    TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
"""

# ─────────────────────────────────────────────────────────────────────────────
# 👥 샘플 사용자 데이터 (권한별)
# 🆕 7.16.4: 첫 실행 시 자동으로 테스트 계정 생성
# 초등학생 설명: 처음 프로그램을 켜면 테스트용 사람들을 자동으로 만들어줘요!
# ─────────────────────────────────────────────────────────────────────────────
SAMPLE_USERS = [
    {
        "email":    "free@test.com",
        "password": "test1234",       # 암호화는 init_db()에서 자동 처리
        "plan":     "free",
        "memo":     "🟢 Free 플랜 테스트 계정 — 분류만 가능",
    },
    {
        "email":    "pro@test.com",
        "password": "test1234",
        "plan":     "pro",
        "memo":     "🟡 Pro 플랜 테스트 계정 — 분류+회귀+배치처리",
    },
    {
        "email":    "enterprise@test.com",
        "password": "test1234",
        "plan":     "enterprise",
        "memo":     "🟣 Enterprise 플랜 테스트 계정 — 전체 기능",
    },
    {
        "email":    "admin@test.com",
        "password": "admin1234",
        "plan":     "enterprise",
        "memo":     "🔑 관리자 계정 — 플랜 변경 권한 포함",
    },
]


# ─────────────────────────────────────────────────────────────────────────────
# 🚀 DB 초기화 (테이블 생성 + 샘플 데이터 삽입)
# ─────────────────────────────────────────────────────────────────────────────
def init_db() -> bool:
    """
    서버 시작 시 DB 자동 초기화
    초등학생 설명: 처음 켤 때 필요한 방(테이블)을 만들고
                  테스트용 사람들(샘플 계정)도 자동으로 넣어줘요!

    Returns:
        True = 성공, False = DB 연결 실패 (서버는 계속 실행됨)
    """
    try:
        import mysql.connector
        conn   = mysql.connector.connect(**MYSQL_CONFIG)
        cursor = conn.cursor()

        # 테이블 생성
        for stmt in INIT_SQL.strip().split(";"):
            stmt = stmt.strip()
            if stmt:
                cursor.execute(stmt)

        conn.commit()
        logger.info("✅ MariaDB 테이블 초기화 완료")

        # 샘플 사용자 데이터 삽입
        _insert_sample_users(cursor, conn)

        cursor.close()
        conn.close()
        return True

    except Exception as e:
        logger.warning(f"⚠️ MariaDB 초기화 실패 (DB 미연결): {e}")
        return False


def _insert_sample_users(cursor, conn) -> None:
    """
    권한별 샘플 사용자 자동 삽입
    초등학생 설명: 이미 있는 계정은 그냥 넘어가고,
                  없는 계정만 새로 만들어줘요!
    """
    from services.auth.auth_service import hash_password

    inserted = 0
    skipped  = 0

    for user in SAMPLE_USERS:
        try:
            # 이미 있으면 skip (중복 방지)
            cursor.execute(
                """
                SELECT user_id AS id
                FROM AU_USERS
                WHERE email = %s
            """,
                (user["email"],)
            )
            if cursor.fetchone():
                skipped += 1
                continue

            # 비밀번호 암호화 후 삽입
            cursor.execute(
                """
                INSERT INTO AU_USERS
                (
                    login_id,
                    user_name,
                    email,
                    password_hash,
                    plan_code,
                    is_active
                )
                VALUES
                (
                    %s,
                    %s,
                    %s,
                    %s,
                    UPPER(%s),
                    TRUE
                )
            """,
                (user["email"], user["email"].split("@")[0], user["email"], hash_password(user["password"]), user["plan"])
            )
            inserted += 1
            logger.info(f"  👤 샘플 계정 생성: {user['email']} [{user['plan']}]")

        except Exception as e:
            logger.warning(f"  ⚠️ 샘플 계정 생성 실패 ({user['email']}): {e}")

    conn.commit()

    if inserted > 0:
        logger.info(f"✅ 샘플 계정 {inserted}개 생성 완료")
        logger.info("─" * 50)
        logger.info("  📋 기본 제공 테스트 계정:")
        for u in SAMPLE_USERS:
            logger.info(f"    {u['memo']}")
            logger.info(f"    이메일: {u['email']} / 비밀번호: {u['password']}")
        logger.info("─" * 50)
    else:
        logger.info(f"ℹ️ 샘플 계정 이미 존재 ({skipped}개 skip)")


# ─────────────────────────────────────────────────────────────────────────────
# 🍃 MongoDB 저장/조회
# ─────────────────────────────────────────────────────────────────────────────
def save_to_mongo(collection: str, data: dict) -> bool:
    """
    MongoDB에 데이터 저장
    초등학생 설명: 서랍장에 물건 넣는 것처럼 JSON 데이터를 저장해요.
    """
    try:
        import pymongo
        client = pymongo.MongoClient(MONGO_URI, serverSelectionTimeoutMS=3000)
        client[MONGO_DB][collection].insert_one(data)
        logger.info(f"🍃 MongoDB 저장: {collection}")
        return True
    except Exception as e:
        logger.warning(f"⚠️ MongoDB 저장 실패: {e}")
        return False


def load_from_mongo(collection: str, query: dict = None, limit: int = 20) -> list:
    """
    MongoDB에서 데이터 조회
    초등학생 설명: 서랍장에서 원하는 물건을 꺼내는 거예요.
    """
    try:
        import pymongo
        client = pymongo.MongoClient(MONGO_URI, serverSelectionTimeoutMS=3000)
        docs   = list(
            client[MONGO_DB][collection]
            .find(query or {})
            .sort("_id", -1)
            .limit(limit)
        )
        for d in docs:
            d["_id"] = str(d["_id"])
        return docs
    except Exception as e:
        logger.warning(f"⚠️ MongoDB 조회 실패: {e}")
        return []


# ─────────────────────────────────────────────────────────────────────────────
# 🐬 MariaDB 저장/조회
# ─────────────────────────────────────────────────────────────────────────────
def save_to_mysql(table: str, data: dict) -> bool:
    """
    MariaDB에 JSON 형태로 저장
    초등학생 설명: 엑셀 표에 새로운 줄을 추가하는 것처럼 저장해요.
    """
    try:
        import mysql.connector
        conn   = mysql.connector.connect(**MYSQL_CONFIG)
        cursor = conn.cursor()
        cursor.execute(
            f"INSERT INTO {table} (data_json) VALUES (%s)",
            (json.dumps(data, ensure_ascii=False),)
        )
        conn.commit()
        cursor.close()
        conn.close()
        logger.info(f"🐬 MariaDB 저장: {table}")
        return True
    except Exception as e:
        logger.warning(f"⚠️ MariaDB 저장 실패: {e}")
        return False




def save_pipeline_result(user_id, file_name, task_type,
                         learning_type, accuracy, data) -> bool:
    """
    AI 분석 결과 저장 호환 함수

    목적:
        기존 코드가 save_pipeline_result()를 호출해도
        신규 AI Pipeline Service를 사용하도록 연결한다.

    관련 서비스:
        AIPipelineService

    변경이력:
        [v7.21] 2026-06-19
        - pipeline_results 직접 저장 제거
        - src/AI/services/ai_pipeline_service.py로 위임
    """
    try:
        from src.AI.services.ai_pipeline_service import AIPipelineService

        return AIPipelineService().save_pipeline_result(
            user_id=user_id,
            file_name=file_name,
            task_type=task_type,
            learning_type=learning_type,
            accuracy=accuracy,
            data=data
        )

    except Exception as e:
        logger.warning(f"⚠️ AI Pipeline Service 저장 실패: {e}")
        return False



def save_model_history(model_name, task_type, learning_type,
                       accuracy, features, target_col,
                       user_id="system", plan="free") -> bool:
    """
    모델 학습 이력 저장 — 시간이 지날수록 정확도 추이 확인 가능
    초등학생 설명: AI가 공부한 기록을 남겨요. 점점 나아지는지 볼 수 있어요!
    """
    try:
        import mysql.connector
        conn   = mysql.connector.connect(**MYSQL_CONFIG)
        cursor = conn.cursor()
        cursor.execute(
            """INSERT INTO AI_MODELS
               (
                   model_name,
                   model_version,
                   model_type_code,
                   algorithm_name,
                   accuracy,
                   file_path,
                   is_best,
                   is_active
               )
               VALUES
               (
                   %s,
                   'v1',
                   %s,
                   %s,
                   %s,
                   NULL,
                   FALSE,
                   TRUE
               )""",
            (model_name, task_type, learning_type, accuracy)
        )
        conn.commit()
        cursor.close()
        conn.close()
        logger.info(f"📈 모델 이력 저장: {model_name} | 정확도={accuracy:.3f}")
        return True
    except Exception as e:
        logger.warning(f"⚠️ model_history 저장 실패: {e}")
        return False


def get_model_history(limit: int = 50) -> list:
    """
    모델 정확도 히스토리 조회
    초등학생 설명: AI가 지금까지 공부한 기록을 보여줘요!
    """
    try:
        import mysql.connector
        conn   = mysql.connector.connect(**MYSQL_CONFIG)
        cursor = conn.cursor(dictionary=True)
        cursor.execute(
            """
            SELECT
                model_id AS id,
                model_name,
                model_type_code AS task_type,
                algorithm_name AS learning_type,
                accuracy,
                file_path,
                is_best,
                is_active,
                created_at AS trained_at
            FROM AI_MODELS
            ORDER BY created_at DESC
            LIMIT %s
        """,
            (limit,)
        )
        rows = cursor.fetchall()
        cursor.close()
        conn.close()
        return rows
    except Exception as e:
        logger.warning(f"⚠️ model_history 조회 실패: {e}")
        return []


def save_both(collection_or_table: str, data: dict) -> dict:
    """
    MongoDB + MariaDB 동시 저장
    초등학생 설명: 같은 내용을 서랍장이랑 엑셀 두 곳에 동시에 넣어요!
    """
    return {
        "MongoDB": "성공" if save_to_mongo(collection_or_table, data.copy()) else "실패",
        "MariaDB": "성공" if save_to_mysql(collection_or_table, data.copy()) else "실패",
    }


def get_user_by_email(email: str) -> dict:
    """
    이메일로 사용자 조회
    초등학생 설명: "이 이메일 쓰는 사람 누구야?" 찾아주는 함수예요.
    """
    try:
        import mysql.connector
        conn   = mysql.connector.connect(**MYSQL_CONFIG)
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT
                user_id AS id,
                email,
                password_hash AS password,
                LOWER(plan_code) AS plan,
                is_active
            FROM AU_USERS
            WHERE email = %s
        """, (email,))
        user = cursor.fetchone()
        cursor.close()
        conn.close()
        return user
    except Exception as e:
        logger.warning(f"⚠️ 사용자 조회 실패: {e}")
        return None


def get_all_users() -> list:
    """
    전체 사용자 목록 조회 (관리자용)
    초등학생 설명: 회원 명단 전체를 보여줘요!
    """
    try:
        import mysql.connector
        conn   = mysql.connector.connect(**MYSQL_CONFIG)
        cursor = conn.cursor(dictionary=True)
        cursor.execute(
            """
            SELECT
                user_id AS id,
                email,
                LOWER(plan_code) AS plan,
                is_active,
                created_at
            FROM AU_USERS
            ORDER BY created_at DESC
        """
        )
        users = cursor.fetchall()
        cursor.close()
        conn.close()
        return users
    except Exception as e:
        logger.warning(f"⚠️ 사용자 목록 조회 실패: {e}")
        return []

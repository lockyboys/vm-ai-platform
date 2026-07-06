# =============================================================================
# config.py ★ 7.20.0  —  VM Project 7.20.0 전체 설정 통합 관리
# =============================================================================
# 📌 이 파일 하나로 모든 설정을 관리해요!
# 📌 참고: Smart File Organizer config.py 구조 반영
#
# 초등학생 설명:
#   게임 설정창처럼 여기서 숫자나 이름을 바꾸면
#   프로그램 전체가 바뀌어요! 코드를 고칠 필요가 없어요.
#
# [변경 이력]
#   2026-06-16 v7: Smart File Organizer 구조 참고, 섹션별 분리, 주석 강화
#   2026-06-15 v6: 환경변수(.env) 지원 추가
#   2026-06-10 v1: 최초 생성
# =============================================================================

import os
import sys
import logging
import multiprocessing
import queue
from pathlib import Path

from dotenv import load_dotenv
load_dotenv()

# ─────────────────────────────────────────────────────────────────────────────
# 📦 앱 기본 정보
# 초등학생 설명: 이 프로그램의 이름표 같은 것이에요!
# ─────────────────────────────────────────────────────────────────────────────
APP_NAME        = "VM Project AI Platform"
APP_VERSION     = "7.20.0"   # ← 버전 변경 시 여기만 수정!
APP_DESCRIPTION = "범용 CSV AI 분석 플랫폼 (지도/비지도/준지도/강화학습)"

# ─────────────────────────────────────────────────────────────────────────────
# 📌 버전 관리 규칙 (Semantic Versioning)
# 초등학생 설명: 버전 번호는 "큰변화.중간변화.작은변화" 순서예요!
#
#   형식: [주버전].[부버전].[패치버전]
#   예시:  7      . 10    . 0
#
#   🔴 주버전 (맨 앞 숫자) — 크게 바뀔 때 올려요
#      예: 아키텍처 전면 변경, 4가지 학습 방식 추가, AGI 통합
#      7.16.4 → 8.0.0
#
#   🟡 부버전 (가운데 숫자) — 기능/요구사항 추가될 때 올려요
#      예: 새 API 추가, 권한 시스템 변경, 페이지 추가
#      7.16.4 → 7.16.4
#
#   🟢 패치버전 (맨 뒤 숫자) — 자잘한 수정/버그 fix 때 올려요
#      예: 주석 수정, 가격 변경, 오타 수정, 색깔 변경
#      7.16.4 → 7.16.4
#
# [버전별 변경 이력은 README_v7.md 참고]
# ─────────────────────────────────────────────────────────────────────────────

# 버전 파싱 헬퍼 (자동 분리)
_ver = APP_VERSION.split(".")
VERSION_MAJOR = int(_ver[0]) if len(_ver) > 0 else 7   # 주버전
VERSION_MINOR = int(_ver[1]) if len(_ver) > 1 else 10  # 부버전
VERSION_PATCH = int(_ver[2]) if len(_ver) > 2 else 0   # 패치버전

# 이 파일이 있는 폴더의 절대 경로 (배포해도 경로가 안 바뀌어요)
# 초등학생 설명: "내가 어디 있는지" 항상 알 수 있는 GPS 같은 것이에요!
BASE_DIR = Path(__file__).parent.absolute()


# ─────────────────────────────────────────────────────────────────────────────
# 📝 로그(기록) 설정
# 초등학생 설명: AI가 뭘 했는지 일기처럼 남기는 설정이에요!
# ─────────────────────────────────────────────────────────────────────────────

# 로그 파일을 만들지 말지 결정해요 (True = 만들기, False = 안 만들기)
LOG_FILE_YN     = True

# 로그 파일 이름에 날짜를 붙일지 결정해요
# True 이면 → app_20260616_143022.log 처럼 날짜가 붙어요
LOG_DATE_YN     = True

# 로그 파일이 저장될 폴더 경로
LOG_DIR_NAME    = "logs"
BASE_LOG_DIR    = BASE_DIR / LOG_DIR_NAME

# 로그 파일 이름 앞에 붙는 글자 (prefix)
LOG_FILE_PREFIX = "vm_7.20.0"

# 실제 로그 파일 경로 (프로그램이 시작할 때 자동으로 채워져요)
LOG_FILE_NAME   = None

# 로그를 며칠 동안 보관할지 결정해요 (7 = 일주일)
# 초등학생 설명: 7일 지난 일기는 자동으로 버려요!
LOG_RETENTION_DAYS = 7

# 로그 출력 형식 (날짜/시간/레벨/파일명:줄번호 순)
LOG_FORMAT = "[%(asctime)s] [%(levelname)s] [%(filename)s:%(lineno)d] %(message)s"
LOG_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"


# ─────────────────────────────────────────────────────────────────────────────
# 🗄️ 데이터베이스 설정
# 초등학생 설명: 데이터를 저장하는 창고 주소와 열쇠예요!
# ─────────────────────────────────────────────────────────────────────────────

# 🍃 MongoDB — JSON 형태 데이터 저장 (비정형 데이터, AI 결과 등)
# 초등학생 설명: 서랍장처럼 뭐든 넣을 수 있는 창고예요!
MONGO_URI = os.getenv("MONGO_URI", "mongodb://127.0.0.1:27017")
MONGO_DB  = os.getenv("MONGO_DB",  "vm_project")   # ← MariaDB와 동일한 이름!

# DB 연결 시도 타임아웃 (밀리초 단위, 3000 = 3초)
# 초등학생 설명: 3초 안에 연결 안 되면 포기하고 다음으로 넘어가요!
MONGO_TIMEOUT_MS = 3000

# 🐬 MariaDB — 표 형태 데이터 저장 (사용자 정보, 결과 정리 등)
# 초등학생 설명: 엑셀처럼 행/열로 정리해서 저장하는 창고예요!
MYSQL_CONFIG = {
    "host": os.getenv("MYSQL_HOST"),
    "user": os.getenv("MYSQL_USER"),
    "password": os.getenv("MYSQL_PASSWORD"),
    "database": os.getenv("MYSQL_DB"),
}
# DB 연결 실패 시 재시도 횟수
# 초등학생 설명: 문이 잠겨 있으면 몇 번 더 두드려볼지 결정해요!
DB_RETRY_COUNT       = 3
DB_RETRY_DELAY_SEC   = 1.0


# ─────────────────────────────────────────────────────────────────────────────
# 🔐 보안 설정
# 초등학생 설명: 로그인 도장(토큰)을 만드는 비밀 열쇠예요!
#               실서비스에서는 반드시 복잡한 값으로 바꾸세요!
# ─────────────────────────────────────────────────────────────────────────────
SECRET_KEY         = os.getenv("SECRET_KEY", "change-me-in-production!")
TOKEN_EXPIRE_HOURS = int(os.getenv("TOKEN_EXPIRE_HOURS", "24"))

# 비밀번호 암호화 방식 (SHA-256 사용)
# 초등학생 설명: 비밀번호를 알아볼 수 없는 암호문으로 바꿔요!
PASSWORD_HASH_ALGO = "sha256"


# ─────────────────────────────────────────────────────────────────────────────
# 💰 요금제(플랜) 설정
# 초등학생 설명: 어떤 회원이 어떤 기능을 쓸 수 있는지 결정해요!
# ─────────────────────────────────────────────────────────────────────────────
PLAN_PRICES = {
    "free":       0,       # 무료
    "pro":        5000,    # 월 5,000원
    "enterprise": 10000,   # 월 10,000원
}

# 환불 가능 기간 (일 단위)
REFUND_DAYS = 7


# ─────────────────────────────────────────────────────────────────────────────
# 📂 폴더(디렉토리) 경로 설정
# 초등학생 설명: 파일들이 어느 방에 들어가는지 결정해요!
# ─────────────────────────────────────────────────────────────────────────────
LOG_PATH       = str(BASE_DIR / "logs")       # 로그 저장 폴더
OUTPUT_PATH    = str(BASE_DIR / "outputs")    # 결과물 저장 폴더
MODEL_PATH     = str(BASE_DIR / "models")     # AI 모델 저장 폴더
DATA_PATH      = str(BASE_DIR / "data")       # 입력 데이터 폴더
UPLOAD_PATH    = str(BASE_DIR / "uploads")    # 업로드된 파일 폴더
DATA_LAKE_PATH = str(BASE_DIR / "data_lake")  # 원본 데이터 보관 폴더

# 출력 결과 하위 폴더
OUTPUT_CHARTS_DIR  = str(BASE_DIR / "outputs" / "charts")   # 그래프 저장
OUTPUT_REPORTS_DIR = str(BASE_DIR / "outputs" / "reports")  # 리포트 저장

# 한 번에 만들어야 할 폴더 목록 (ensure_dirs()가 이걸 보고 만들어요)
# 초등학생 설명: 집 지을 때 필요한 방 목록이에요!
REQUIRED_DIRS = [
    LOG_PATH,
    OUTPUT_PATH,
    OUTPUT_CHARTS_DIR,
    OUTPUT_REPORTS_DIR,
    MODEL_PATH,
    DATA_PATH,
    UPLOAD_PATH,
    DATA_LAKE_PATH,
]


# ─────────────────────────────────────────────────────────────────────────────
# 🌐 서버 설정
# 초등학생 설명: 서버가 어디서 누구 말을 들을지 결정해요!
# ─────────────────────────────────────────────────────────────────────────────
API_HOST = os.getenv("API_HOST", "0.0.0.0")   # 0.0.0.0 = 모든 주소에서 접속 허용
API_PORT = int(os.getenv("API_PORT", "8000"))  # 포트 번호 (8000번 문)
DEBUG    = os.getenv("DEBUG", "false").lower() == "true"

# 파일 업로드 최대 크기 (바이트 단위, 50MB)
# 초등학생 설명: 50MB보다 큰 파일은 받지 않아요!
MAX_UPLOAD_SIZE_BYTES = 50 * 1024 * 1024

# 허용하는 파일 확장자 (CSV만 허용)
ALLOWED_EXTENSIONS = {"csv", "xlsx", "xls", "tsv"}

# CORS 허용 도메인 (프론트엔드가 다른 주소에 있을 때 필요)
CORS_ORIGINS = ["*"]


# ─────────────────────────────────────────────────────────────────────────────
# 🤖 AI / 머신러닝 설정
# 초등학생 설명: AI를 가르칠 때 어떻게 가르칠지 결정하는 설정이에요!
# ─────────────────────────────────────────────────────────────────────────────
MODEL_VERSION    = "7.20.0"
MAX_MEMORY_SIZE  = 10000   # 에이전트 기억 최대 개수

# 자동 재학습 정확도 기준
# 초등학생 설명: 75점 이하면 다시 공부해야 해요!
RETRAIN_THRESHOLD = 0.75

# AutoML에서 시도할 모델 목록
# 초등학생 설명: 여러 선생님 중 제일 잘 가르치는 선생님을 자동으로 골라요!
AUTOML_CLASSIFIERS = [
    "RandomForest",
    "GradientBoosting",
    "LogisticRegression",
]
AUTOML_REGRESSORS = [
    "RandomForestRegressor",
    "GradientBoostingRegressor",
    "Ridge",
]

# 강화학습 에피소드 수 (많을수록 더 잘 찾지만 느려요)
RL_EPISODES = 20

# 교차 검증 폴드 수
CV_FOLDS = 3

# 학습/테스트 데이터 분할 비율 (0.2 = 20%를 테스트에 사용)
TEST_SIZE = 0.2

# 랜덤 시드 (같은 값이면 항상 같은 결과가 나와요)
# 초등학생 설명: 주사위를 같은 방식으로 던지게 해주는 값이에요!
RANDOM_SEED = 42


# ─────────────────────────────────────────────────────────────────────────────
# ⏰ Cron(자동 스케줄) 설정
# 초등학생 설명: 알람시계처럼 "몇 시에 뭘 해" 정해두는 설정이에요!
# ─────────────────────────────────────────────────────────────────────────────

# 일일 자동 재학습 시각 (새벽 2시)
CRON_DAILY_RETRAIN_TIME  = "02:00"

# 자기개선 에이전트 실행 주기 (3시간마다)
CRON_SELF_IMPROVE_HOURS  = 3

# 시스템 상태 확인 주기 (분 단위, 60 = 매시간)
CRON_HEALTH_CHECK_MIN    = 60

# 주간 리포트 생성 (매주 월요일 오전 9시)
CRON_WEEKLY_REPORT_DAY   = "monday"
CRON_WEEKLY_REPORT_TIME  = "09:00"


# ─────────────────────────────────────────────────────────────────────────────
# 🏥 Self-Healing (자동 복구) 설정
# 초등학생 설명: 서버가 꺼지면 자동으로 다시 켜줘요!
# ─────────────────────────────────────────────────────────────────────────────

# 몇 번 실패해야 재시작할지 결정해요
HEALING_FAIL_THRESHOLD = 3

# 상태 확인 주기 (초 단위)
HEALING_CHECK_INTERVAL = 60

# 감시할 서비스 목록 (이름: 포트번호)
MONITORED_SERVICES = {
    "flask":   8000,
    "mongod":  27017,
    "mariadb": 3306,
}


# ─────────────────────────────────────────────────────────────────────────────
# ⚙️ 병렬 처리 최적화
# 초등학생 설명: 여러 일을 동시에 처리하는 일꾼 수예요!
# ─────────────────────────────────────────────────────────────────────────────

# CPU 코어 수에 맞게 자동 설정 (최대 8개)
# 초등학생 설명: 컴퓨터가 얼마나 많은 일을 동시에 할지 정해요!
MAX_WORKERS = min(multiprocessing.cpu_count(), 8)


# ─────────────────────────────────────────────────────────────────────────────
# 🌍 전역 상태 관리 변수 (Global State)
# 초등학생 설명: 프로그램이 돌아가면서 기억해야 할 것들을 담는 변수예요!
# [주의] 이 값들은 프로그램이 실행되면서 자동으로 바뀌어요. 직접 수정하지 마세요!
# ─────────────────────────────────────────────────────────────────────────────

# 프로그램 종료 시 표준 스트림 복구를 위한 원본 백업
# 초등학생 설명: 원래 터미널 화면을 기억해뒀다가 나중에 복구해요!
ORIGINAL_STDOUT = sys.stdout
ORIGINAL_STDERR = sys.stderr

# 비동기 로깅을 위한 메시지 큐 (멀티프로세스 환경용)
# 초등학생 설명: 로그 메시지가 줄 서서 기다리는 대기열이에요!
LOG_QUEUE    = None   # 프로그램 시작 시 utils.py가 채워줘요
LOG_LISTENER = None   # 큐에서 로그를 꺼내 파일에 쓰는 일꾼


# ─────────────────────────────────────────────────────────────────────────────
# 🌍 서버 주소 전역 변수 — 여기만 바꾸면 전체 반영!
# 초등학생 설명: 이사 가면 주소가 바뀌듯이 서버 주소가 바뀌면
#               여기 한 곳만 바꾸면 프로그램 전체에 반영돼요!
#
# [사용 방법]
#   ① 로컬 개발:  SERVER_HOST = "127.0.0.1"
#   ② GCP VM:     SERVER_HOST = "34.64.209.152"  ← 현재 설정
#   ③ 도메인:     SERVER_HOST = "myai.example.com"
#
# [변경 이력]
#   2026-06-16: 전역 변수로 분리 (IP 하드코딩 제거)
# ─────────────────────────────────────────────────────────────────────────────

# ✅ 여기만 바꾸면 끝! (IP 또는 도메인)
SERVER_HOST = os.getenv("SERVER_HOST", "34.64.209.152")

# 포트 (API_PORT와 동일하게 맞춰요)
SERVER_PORT = int(os.getenv("SERVER_PORT", "8000"))

# 프로토콜 (http 또는 https)
# 초등학생 설명: http는 일반 도로, https는 보안 터널이에요!
SERVER_PROTOCOL = os.getenv("SERVER_PROTOCOL", "http")

# 전체 서버 주소 (자동 조합 — 직접 수정 X)
# 예: http://34.64.209.152:8000
SERVER_BASE_URL = f"{SERVER_PROTOCOL}://{SERVER_HOST}:{SERVER_PORT}"

# API 기본 경로
SERVER_API_URL = f"{SERVER_BASE_URL}/api"

# ─── 환경별 빠른 전환 프리셋 ─────────────────────────────
# 아래 함수로 환경 전환 가능:
#   python -c "from config import set_env; set_env('local')"
#
# 초등학생 설명: "집(로컬)", "학교(GCP)", "회사(도메인)" 중
#               어디서 쓸지 빠르게 바꾸는 스위치예요!

ENV_PRESETS = {
    # 로컬 개발 환경 (내 컴퓨터)
    "local": {
        "SERVER_HOST":     "127.0.0.1",
        "SERVER_PORT":     8000,
        "SERVER_PROTOCOL": "http",
    },
    # GCP VM (현재 운영 서버)
    "gcp": {
        "SERVER_HOST":     "34.64.209.152",
        "SERVER_PORT":     8000,
        "SERVER_PROTOCOL": "http",
    },
    # 도메인 사용 시 (HTTPS)
    "production": {
        "SERVER_HOST":     "your-domain.com",  # ← 도메인으로 변경
        "SERVER_PORT":     443,
        "SERVER_PROTOCOL": "https",
    },
}

def set_env(env_name: str) -> None:
    """
    환경 전환 함수 — 한 줄로 서버 주소 전체 변경
    초등학생 설명: "지금 어디서 쓸 건지" 알려주면 주소를 자동으로 바꿔줘요!

    사용법:
        from config import set_env
        set_env('local')   # 내 컴퓨터
        set_env('gcp')     # GCP VM
        set_env('production')  # 실서비스 도메인
    """
    import sys
    preset = ENV_PRESETS.get(env_name)
    if not preset:
        raise ValueError(f"❌ 알 수 없는 환경: {env_name} (가능: {list(ENV_PRESETS.keys())})")

    # 현재 모듈의 전역 변수를 동적으로 업데이트
    this = sys.modules[__name__]
    for key, val in preset.items():
        setattr(this, key, val)

    # BASE_URL 재조합
    this.SERVER_BASE_URL = f"{this.SERVER_PROTOCOL}://{this.SERVER_HOST}:{this.SERVER_PORT}"
    this.SERVER_API_URL  = f"{this.SERVER_BASE_URL}/api"

    print(f"✅ 환경 전환 완료: [{env_name}] → {this.SERVER_BASE_URL}")

# ============================================================
# v7.21 Directory Standard
# 모든 로컬 디렉토리는 여기서만 선언한다.
# 코드 안에서 "uploads", "/data/models" 같은 하드코딩 금지.
# ============================================================

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent

DATA_ROOT = Path("/data")

# 업무분류 루트
CM_DIR = DATA_ROOT / "CM"
AU_DIR = DATA_ROOT / "AU"
RL_DIR = DATA_ROOT / "RL"
MN_DIR = DATA_ROOT / "MN"
SV_DIR = DATA_ROOT / "SV"
DT_DIR = DATA_ROOT / "DT"
AI_DIR = DATA_ROOT / "AI"
RP_DIR = DATA_ROOT / "RP"
DP_DIR = DATA_ROOT / "DP"
BK_DIR = DATA_ROOT / "BK"
LG_DIR = DATA_ROOT / "LG"
AD_DIR = DATA_ROOT / "AD"

# 실제 사용 디렉토리
DT_UPLOAD_DIR = DT_DIR / "uploads"
DT_DATASET_DIR = DT_DIR / "datasets"

AI_MODEL_DIR = AI_DIR / "models"
AI_AUTOML_DIR = AI_DIR / "automl"
AI_SHAP_DIR = AI_DIR / "shap"
AI_RL_DIR = AI_DIR / "reinforcement"

RP_REPORT_DIR = RP_DIR / "reports"

BK_BACKUP_DIR = BK_DIR / "backups"

LG_LOG_DIR = LG_DIR / "logs"

TEMP_DIR = DATA_ROOT / "temp"
EXPORT_DIR = DATA_ROOT / "exports"

# 전체 생성 대상
STANDARD_DIRS = [
    CM_DIR, AU_DIR, RL_DIR, MN_DIR, SV_DIR,
    DT_DIR, AI_DIR, RP_DIR, DP_DIR, BK_DIR, LG_DIR, AD_DIR,
    DT_UPLOAD_DIR, DT_DATASET_DIR,
    AI_MODEL_DIR, AI_AUTOML_DIR, AI_SHAP_DIR, AI_RL_DIR,
    RP_REPORT_DIR,
    BK_BACKUP_DIR,
    LG_LOG_DIR,
    TEMP_DIR, EXPORT_DIR,
]

# ============================================================
# v7.21 AI Job API Settings
# ============================================================

AI_JOB_DEFAULT_LIMIT = 100
AI_JOB_MAX_LIMIT = 500


# =========================================================
# SPS Asset / Runtime Directory Configuration
# =========================================================

BASE_DIR = Path(__file__).resolve().parent

# ---------------------------------------------------------
# Asset Root
# ---------------------------------------------------------
ASSET_ROOT_DIR = Path(
    os.getenv("ASSET_ROOT_DIR", BASE_DIR / "assets")
)

ICON_DIR = os.getenv("ICON_DIR", "icons")
IMAGE_DIR = os.getenv("IMAGE_DIR", "images")
DOCUMENT_DIR = os.getenv("DOCUMENT_DIR", "documents")
AUDIO_DIR = os.getenv("AUDIO_DIR", "audio")
VIDEO_DIR = os.getenv("VIDEO_DIR", "video")
MODEL_DIR = os.getenv("MODEL_DIR", "models")
TEMPLATE_DIR = os.getenv("TEMPLATE_DIR", "templates")

# ---------------------------------------------------------
# Runtime Root
# ---------------------------------------------------------
OUTPUT_DIR = Path(os.getenv("OUTPUT_DIR", BASE_DIR / "output"))
UPLOAD_DIR = Path(os.getenv("UPLOAD_DIR", BASE_DIR / "uploads"))
SPS_TEMP_DIR = Path(os.getenv("TEMP_DIR", BASE_DIR / "temp"))
LOG_DIR = Path(os.getenv("LOG_DIR", BASE_DIR / "logs"))
BACKUP_DIR = Path(os.getenv("BACKUP_DIR", BASE_DIR / "backup"))
REPOSITORY_DIR = Path(os.getenv("REPOSITORY_DIR", BASE_DIR / "repository"))


def get_asset_path(asset_dir: str, file_name: str) -> Path:
    """
    DB에는 file_name만 저장한다.
    실제 폴더 위치는 .env/config.py에서 관리한다.
    """
    if not file_name:
        raise ValueError("file_name is required")

    if ".." in file_name or file_name.startswith(("/", "\\")):
        raise ValueError("Invalid file name")

    return ASSET_ROOT_DIR / asset_dir / file_name


def get_icon_path(file_name: str) -> Path:
    return get_asset_path(ICON_DIR, file_name)


def get_image_path(file_name: str) -> Path:
    return get_asset_path(IMAGE_DIR, file_name)


def get_document_path(file_name: str) -> Path:
    return get_asset_path(DOCUMENT_DIR, file_name)


def get_audio_path(file_name: str) -> Path:
    return get_asset_path(AUDIO_DIR, file_name)


def get_video_path(file_name: str) -> Path:
    return get_asset_path(VIDEO_DIR, file_name)


def get_model_path(file_name: str) -> Path:
    return get_asset_path(MODEL_DIR, file_name)


def get_template_path(file_name: str) -> Path:
    return get_asset_path(TEMPLATE_DIR, file_name)
# =========================================================
# SPS Asset / Runtime Directory Configuration
# =========================================================

BASE_DIR = Path(__file__).resolve().parent

# ---------------------------------------------------------
# Asset Root
# ---------------------------------------------------------
ASSET_ROOT_DIR = Path(
    os.getenv("ASSET_ROOT_DIR", BASE_DIR / "assets")
)

ICON_DIR = os.getenv("ICON_DIR", "icons")
IMAGE_DIR = os.getenv("IMAGE_DIR", "images")
DOCUMENT_DIR = os.getenv("DOCUMENT_DIR", "documents")
AUDIO_DIR = os.getenv("AUDIO_DIR", "audio")
VIDEO_DIR = os.getenv("VIDEO_DIR", "video")
MODEL_DIR = os.getenv("MODEL_DIR", "models")
TEMPLATE_DIR = os.getenv("TEMPLATE_DIR", "templates")

# ---------------------------------------------------------
# Runtime Root
# ---------------------------------------------------------
OUTPUT_DIR = Path(os.getenv("OUTPUT_DIR", BASE_DIR / "output"))
UPLOAD_DIR = Path(os.getenv("UPLOAD_DIR", BASE_DIR / "uploads"))
SPS_TEMP_DIR = Path(os.getenv("TEMP_DIR", BASE_DIR / "temp"))
LOG_DIR = Path(os.getenv("LOG_DIR", BASE_DIR / "logs"))
BACKUP_DIR = Path(os.getenv("BACKUP_DIR", BASE_DIR / "backup"))
REPOSITORY_DIR = Path(os.getenv("REPOSITORY_DIR", BASE_DIR / "repository"))


def get_asset_path(asset_dir: str, file_name: str) -> Path:
    """
    DB에는 file_name만 저장한다.
    실제 폴더 위치는 .env/config.py에서 관리한다.
    """
    if not file_name:
        raise ValueError("file_name is required")

    if ".." in file_name or file_name.startswith(("/", "\\")):
        raise ValueError("Invalid file name")

    return ASSET_ROOT_DIR / asset_dir / file_name


def get_icon_path(file_name: str) -> Path:
    return get_asset_path(ICON_DIR, file_name)


def get_image_path(file_name: str) -> Path:
    return get_asset_path(IMAGE_DIR, file_name)


def get_document_path(file_name: str) -> Path:
    return get_asset_path(DOCUMENT_DIR, file_name)


def get_audio_path(file_name: str) -> Path:
    return get_asset_path(AUDIO_DIR, file_name)


def get_video_path(file_name: str) -> Path:
    return get_asset_path(VIDEO_DIR, file_name)


def get_model_path(file_name: str) -> Path:
    return get_asset_path(MODEL_DIR, file_name)


def get_template_path(file_name: str) -> Path:
    return get_asset_path(TEMPLATE_DIR, file_name)

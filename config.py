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
INSURANCE_POLICY_DIR = BASE_DIR / "insurance_policies"


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
# Ollama 공통 실행 설정
OLLAMA_ENDPOINT = os.getenv("OLLAMA_ENDPOINT", "http://127.0.0.1:11435")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "gemma4:latest")
OLLAMA_NUM_GPU = int(os.getenv("OLLAMA_NUM_GPU", "24"))
OLLAMA_NUM_CTX = int(os.getenv("OLLAMA_NUM_CTX", "8192"))
OLLAMA_NUM_BATCH = int(os.getenv("OLLAMA_NUM_BATCH", "32"))
OLLAMA_NUM_PREDICT = int(os.getenv("OLLAMA_NUM_PREDICT", "4096"))
OLLAMA_TEMPERATURE = float(os.getenv("OLLAMA_TEMPERATURE", "0"))
OLLAMA_KEEP_ALIVE = os.getenv("OLLAMA_KEEP_ALIVE", "30m")
OLLAMA_WORKERS = int(os.getenv("OLLAMA_WORKERS", "4"))
OLLAMA_TIMEOUT_SECONDS = int(os.getenv("OLLAMA_TIMEOUT_SECONDS", "29900"))
# 블라인드 리뷰 지시문(2026-11-01 LuckyBoys). 82건 모두 같은 문구를 각각 독립 호출로 보낸다.
# 문제별 힌트(범주·앱·주입 결함·문제 수)는 절대 넣지 않는다(블라인드 유지).
# - review   : 기존 문구. Gemini 80/82, gemma4:e4b 27/82 결과의 기준선이므로 글자 하나도 바꾸지 않는다.
# - bug_focus: 버그 집중형. 칭찬·일반 개선 제안을 막고 위치·원인·잘못된 동작을 적게 한다.
# - checklist: 4관점 점검표(2026-11-01 LuckyBoys). 12b 기본 검토 문법 6/20 원인 = 결함을 아예 언급하지 않음(분석
#              FastAPI/LangGraph/analyze_syntax_misses_20261101.py). 구문·실행 예외·느린 부분·틀린 결과를 같은 무게로
#              차례로 확인하게 한다. 범주 이름(문법·성능·논리)·앱 이름·문제 수는 쓰지 않는다(블라인드 유지).
# 사용처: harness/apps/blind_review_20261027/blind_worker.py resolve_prompt, harness/mcp/tools/blind_review_jobs_v2.submit
BLIND_REVIEW_PROMPTS = {
    "review": "이 프로그램을 검토해 주세요.",
    "bug_focus": ("이 프로그램의 버그를 찾아 주세요. 버그마다 ① 위치(함수명·코드 조각) ② 원인 ③ 잘못된 동작을 적고, "
                  "칭찬·일반 개선 제안은 쓰지 마세요. 버그가 없으면 '버그 없음'이라고 답하세요."),
    "checklist": ("이 프로그램을 검토해 주세요. 먼저 ① 코드가 그대로 해석·실행 가능한지(구문) ② 실행 중 예외가 나는지 "
                  "③ 불필요하게 느린 부분 ④ 결과가 틀리는 부분을 차례로 확인하고, 문제마다 위치·원인을 적으세요. "
                  "문제가 없으면 '문제 없음'이라고 답하세요."),
    # checklist_rules(2026-11-01 LuckyBoys 선택 A): 12b 점검표 논리 13/20 — 놓친 7건 중 6건이 표준 규칙을 알아야
    #   보이는 결함(analyze_logic_misses_20261101.py). ①~④는 checklist 와 같고 ⑤만 추가(효과 분리).
    #   앱 종류가 드러나는 단어(게임·계산·점수 등)는 쓰지 않는다(블라인드 유지).
    "checklist_rules": ("이 프로그램을 검토해 주세요. 먼저 ① 코드가 그대로 해석·실행 가능한지(구문) ② 실행 중 예외가 나는지 "
                        "③ 불필요하게 느린 부분 ④ 결과가 틀리는 부분 ⑤ 이런 종류의 프로그램이 일반적으로 따르는 "
                        "표준 규칙·관례와 다르게 동작하는 부분을 차례로 확인하고, 문제마다 위치·원인을 적으세요. "
                        "문제가 없으면 '문제 없음'이라고 답하세요."),
}
BLIND_REVIEW_DEFAULT_PROMPT = "review"  # 지시문을 지정하지 않은 제출·예전 job 이어서 실행은 기존 문구
# 블라인드 리뷰 실행 대상·모델(2026-11-01 LuckyBoys: GPU 서버 gemma4:12b-it-q4_K_M 실험).
# - laptop: 노트북 RTX 3060 6GB, 역방향 터널(ssh -N -R 11435:127.0.0.1:11434) → 기존 OLLAMA_ENDPOINT 그대로.
# - gpu   : GPU 서버(L4), 개발서버→GPU 정방향 터널(ssh -N -L 11436:127.0.0.1:11434 ... jeajea_park@<GPU IP>).
#           GPU IP는 켤 때마다 바뀌지만 터널 로컬 포트(11436)는 고정이라 주소를 바꿀 필요가 없다.
# 목록에 없는 대상은 워커·제출 도구가 거부한다(임의 URL로 82건을 보내지 않게).
BLIND_REVIEW_OLLAMA_ENDPOINTS = {
    "laptop": OLLAMA_ENDPOINT,
    "gpu": os.getenv("BLIND_REVIEW_GPU_OLLAMA_ENDPOINT", "http://127.0.0.1:11436"),
}
BLIND_REVIEW_DEFAULT_OLLAMA_TARGET = "laptop"  # 대상 미지정 제출·예전 job 이어서 실행 = 기존 동작
# 대상별 num_gpu(GPU에 올릴 층 수). 노트북 6GB는 OLLAMA_NUM_GPU(.env 28, 34는 CUDA OOM 실측),
# GPU 서버는 None = 옵션을 보내지 않아 Ollama가 전 층을 GPU에 올리게 한다(28층 제한 시 12b가 CPU로 밀려 느려짐).
BLIND_REVIEW_OLLAMA_NUM_GPU = {"laptop": OLLAMA_NUM_GPU, "gpu": None}
# 대상별 num_batch. 노트북은 OLLAMA_NUM_BATCH(32) 유지(기존 실행과 동일).
# GPU 서버는 None = 보내지 않음(Ollama 기본값). 2026-11-01 실측: gemma4:12b-it-q4_K_M 에 num_batch=32 를 주면
# "Failed to load CLIP model" 로 모델 로딩 실패(HTTP 500), 빼면 정상(curl A/B 시험, num_ctx 8192 는 무관).
BLIND_REVIEW_OLLAMA_NUM_BATCH = {"laptop": OLLAMA_NUM_BATCH, "gpu": None}
# 모델 이름 → 기대 지문(ollama /api/tags digest 실측 2026-11-01). 다르면 워커가 실행 전에 멈춘다(preflight_failed).
# gemma4:latest 는 노트북에서 gemma4:e4b 와 같은 지문(Q4_K_M 7.5B)이다.
# 12b 지문: GPU 서버 127.0.0.1:11436/api/tags 실측(FastAPI/LangGraph/check_gpu_server_ollama_20261101.py).
BLIND_REVIEW_MODEL_DIGESTS = {
    "gemma4:e4b": "dc35e8d9c6061baa6f0fa870975ab6932e2542b579b13ea0f199fa4bb7300c9c",
    "gemma4:latest": "dc35e8d9c6061baa6f0fa870975ab6932e2542b579b13ea0f199fa4bb7300c9c",
    "gemma4:12b-it-q4_K_M": "6114515d63c17436a7c0417d82820ac65ad643e2806c5a3c89cb62846436ed0b",
}


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
    "host": os.getenv("MARIADB_HOST"),
    "port": int(os.getenv("MARIADB_PORT", "3306")),
    "user": os.getenv("MARIADB_USERNAME"),
    "password": os.getenv("MARIADB_PASSWORD"),
    "database": os.getenv("COMMON_MARIADB_DATABASE"),
    "auth_plugin": "mysql_native_password"
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
SECRET_KEY         = os.getenv("SECRET_KEY")
TOKEN_EXPIRE_HOURS = int(os.getenv("TOKEN_EXPIRE_HOURS", "24"))

# 비밀번호 해시 방식: 인증 서비스가 PBKDF2-HMAC-SHA256을 사용한다.
PASSWORD_HASH_ALGO = "pbkdf2_sha256"


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
    str(INSURANCE_POLICY_DIR),
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
LOG_QUEUE    = None   # 프로그램 시작 시 common/common_function.py가 채워줘요
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
SERVER_HOST = os.getenv("SERVER_HOST", "127.0.0.1")

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

# ============================================================
# Multi-Persona Agent 호출 예산
# 숫자 상한은 이 공용 설정에서만 바꿉니다. agent 소스에는 기본 수치를 두지 않습니다.
# ============================================================

# 한 요청에서 모든 페르소나 LLM 호출(도구 후속 호출과 재요청 포함)의 최대 횟수입니다.
MULTI_PERSONA_MAX_PERSONA_CALLS = 6
# 계획 단계에서 선택할 서로 다른 페르소나 수의 상한입니다.
MULTI_PERSONA_MAX_PERSONAS = 4
# 한 요청에서 실제 실행할 Tavily 검색 호출의 최대 횟수입니다.
MULTI_PERSONA_MAX_TAVILY_CALLS = 3
# 계획·페르소나·검증 단계를 합친 전체 LLM 호출의 최대 횟수입니다.
MULTI_PERSONA_MAX_LLM_CALLS = 12
# 검증자 LLM을 포함한 검증 단계 호출의 최대 횟수입니다.
MULTI_PERSONA_MAX_VERIFIER_CALLS = 3
# 검증 응답이 비었을 때 페르소나에게 다시 요청할 수 있는 횟수입니다.
MULTI_PERSONA_MAX_VERIFIER_RETRIES = 2


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


# ============================================================
# SPS Object Definition / Identifier Runtime Defaults
# ============================================================

# 엔진 요청에서 감사 필드가 생략된 경우 사용하는 기본값입니다. 호출자가 전달한 값이 우선합니다.
SPS_OBJECT_DEFINITION_AUDIT_USER = "OBJECT_DEFINITION_ENGINE"
SPS_OBJECT_DEFINITION_PROGRAM_ID = "ObjectDefinitionEngine"
SPS_DEFAULT_CLIENT_IP = "127.0.0.1"

# Identifier sequence 갱신의 감사 필드 기본값입니다. 운영 호출별 식별 정보는 추후 인자로 전달합니다.
SPS_IDENTIFIER_AUDIT_USER = "IDENTIFIER_ENGINE"
SPS_IDENTIFIER_PROGRAM_ID = "IdentifierEngine"

# Direct Gemini commands use the deployed Gateway API; the signing key stays in service settings.
SPS_AGENT_GATEWAY_URL = os.getenv("SPS_AGENT_GATEWAY_URL", "https://sps-mcp-gateway-5v4kufkk.an.gateway.dev")
SPS_AGENT_GATEWAY_SUBJECT_ID = os.getenv("SPS_AGENT_GATEWAY_SUBJECT_ID", "jeaje")
SPS_AGENT_GATEWAY_TIMEOUT_SECONDS = 3600

# Review work runs independently; MCP request liveness is a separate 150-second rule.
# 승인 정책: 장기 실행 두 도구와 일반 작업 유닛의 수명을 분리한다.
SPS_SOURCE_EXECUTION_TIMEOUT_SECONDS = 3600
SPS_GENERAL_UNIT_RUNTIME_SECONDS = 3600
SPS_WORKER_RESULT_GRACE_SECONDS = 10
# 2026-11-02 LuckyBoys 결정: 리뷰 3590 + 결과 저장 여유 10 = 유닛 상한 3600.
# 리뷰 시간이 상한과 같으면(3600) systemd가 여유 시간 전에 워커를 죽여 result.json 없이 실패하므로
# 반드시 MULTI_PERSONA_REVIEW_TIMEOUT_SECONDS + SPS_WORKER_RESULT_GRACE_SECONDS <= SPS_GENERAL_UNIT_RUNTIME_SECONDS 를 지킨다.
MULTI_PERSONA_REVIEW_TIMEOUT_SECONDS = 3590
# Preserve the full report on disk and return a bounded preview through MCP.
MULTI_PERSONA_REVIEW_OUTPUT_CHARS = 12000
# 2026-11-10 LuckyBoys 결정(완전 자동): 검증된 리뷰 제안을 원본에 자동 적용한다.
# 적용 전 job 폴더에 original.py 백업 → 문법 컴파일 + 지정 pytest → 실패 시 자동 되돌림.
# False로 바꾸면 이전처럼 proposed.py만 남긴다(호출 시 auto_apply 인자로 개별 지정도 가능).
# ⚠ 주의: 호출 시 test_paths를 주지 않으면 문법 검사만 통과해도 원본이 바뀐다(테스트로 되돌릴 근거 없음).
#   중요한 파일은 반드시 test_paths=["tests/...", "harness/tests/..."]를 함께 넘길 것.
MULTI_PERSONA_REVIEW_AUTO_APPLY = True
# 자동 적용 후 pytest 최대 시간(초). 리뷰 남은 시간보다 길면 남은 시간으로 줄인다.
MULTI_PERSONA_AUTO_APPLY_TEST_TIMEOUT_SECONDS = 600
# 자동 적용 검증에 쓸 수 있는 테스트 폴더(이 밖의 경로는 거부).
MULTI_PERSONA_AUTO_APPLY_TEST_ROOTS = ("tests", "harness/tests")
# 2026-11-11 자동 적용 규칙(LuckyBoys 요청: 일부라도 반영). harness/mcp/tools/auto_apply.py가 읽는다.
#   "all_pass": 테스트 전부 통과해야 적용 / "improve": 원본 대비 퇴행 없이 통과 수가 늘면 적용(partial).
#   improve는 원본으로 테스트를 한 번 더 돌리므로 검증 시간이 약 2배가 된다.
MULTI_PERSONA_AUTO_APPLY_POLICY = "improve"
# 2026-11-11 실패 피드백 재시도(LuckyBoys 결정). review_python_source 워커가 읽는다.
#   자동 적용이 되돌려지거나 일부만 적용되면, 실패한 테스트 목록·메시지를 오류 로그로 만들어
#   직전 수정안과 함께 같은 AI에게 다시 리뷰시킨다. 1이면 재시도 없음(1차만).
# 2026-11-14 (LuckyBoys 결정): 2 → 3. 아래 온도표대로 1차 0.4 → 2차 0.2 → 3차 0.0 으로 세 번까지 시도한다.
# 2026-11-21 (LuckyBoys 요청 '고쳐질 때까지 반복'): 3 → 10. 이제 반복은 '전부 통과' 또는 '제자리걸음'
#   (아래 MULTI_PERSONA_SELFFIX_STAGNATION_ROUNDS)에서 끝나고, 이 값은 비용·시간을 막는 안전 상한일 뿐이다.
#   4라운드부터는 온도표의 마지막 값(0.0)을 쓴다.
MULTI_PERSONA_AUTO_APPLY_MAX_ROUNDS = 10
# 2026-11-14 라운드별 작업 담당 AI(페르소나) temperature. 1차는 리뷰 CLI 기본값(0.4)을 그대로 쓰고,
#   2차부터 이 값을 --agent-temperature로 넘긴다. 라운드가 더 많으면 마지막 값을 쓴다. 각 값은 0.0~1.0.
#   이유: 같은 AI도 매번 답이 달라 재시도할수록 답을 고정해 피드백에 맞춘 수정만 하게 한다.
MULTI_PERSONA_AUTO_APPLY_ROUND_TEMPERATURES = (0.4, 0.2, 0.0)
# 다음 라운드를 시작하려면 리뷰 제한 시간 중 이만큼은 남아 있어야 한다(초). 절반은 테스트·저장 여유로 남긴다.
MULTI_PERSONA_AUTO_APPLY_RETRY_MIN_SECONDS = 180
# 피드백에 넣을 실패 테스트 최대 개수(프롬프트가 너무 길어지지 않게).
MULTI_PERSONA_AUTO_APPLY_FEEDBACK_MAX_FAILURES = 40
# 2026-11-21 (LuckyBoys 승인 '실패 테스트 집중'): 피드백·focus.txt에 실패 테스트마다 붙일 테스트 코드 최대 줄 수.
#   assert 앞 줄(입력)과 E 줄(기대값)을 보여 줘 작은 모델도 무엇을 고쳐야 하는지 알게 한다. 0이면 붙이지 않음.
MULTI_PERSONA_AUTO_APPLY_FEEDBACK_CONTEXT_LINES = 12
# 2026-11-21 (LuckyBoys 승인 '추가 기능 차단'): 제안이 퇴행을 내면 바뀐 맨 바깥 함수·클래스를 하나씩 원본으로
#   되돌려 테스트해 볼 최대 개수(harness/mcp/tools/auto_apply.py). 0이면 끔(예전처럼 바로 전부 되돌림).
#   한 개당 pytest 1회가 더 든다(메모리 에이전트 테스트 기준 약 1초).
MULTI_PERSONA_AUTO_APPLY_REVERT_MAX_FUNCTIONS = 20
# 2026-11-21 (LuckyBoys 승인 '느린 모델 시간 배분'): 공급자 항목의 job_timeout_seconds가 넘을 수 없는 상한(초).
MULTI_PERSONA_REVIEW_PROVIDER_TIMEOUT_MAX_SECONDS = 30000
# 2026-11-21 (LuckyBoys 요청 '수정 중 상황을 만나면 어떻게 하는지 로직으로'): 상황별 대응표.
#   harness/mcp/tools/multi_persona_tools.py 의 _run_feedback_rounds 가 이 표대로만 움직인다.
#   행동: stop(멈춤) / next_round(다음 라운드) / retry_same_round(같은 라운드 다시, 한도 넘으면 다음 라운드).
#   상황마다 허용 행동이 정해져 있어(예: 성공은 stop만, 크레딧 부족은 stop만) 잘못 적으면 AI를 부르기 전에 거부한다.
MULTI_PERSONA_SELFFIX_ACTIONS = {
    "all_passed": "stop",                    # 테스트 전부 통과 = 성공
    "improved": "next_round",                # 일부 나아짐(부분 반영) → 남은 실패를 계속 고친다
    "no_gain": "next_round",                 # 나아지지 않음 → 피드백 주고 다시(제자리걸음 횟수에 셈)
    "regressed": "next_round",               # 다른 테스트를 깸 → 되돌린 뒤 피드백 주고 다시(제자리걸음에 셈)
    "format_rejected": "retry_same_round",   # 출력 형식 거부 → 같은 라운드 다시, 한도 넘으면 다음 라운드
    "cli_error": "stop",                     # 리뷰 CLI 비정상 종료 → 원인 확인이 먼저
    "provider_fatal": "stop",                # 크레딧 부족·키 오류·Ollama 메모리 부족 → 다시 불러도 같음
    "review_timeout": "stop",                # 리뷰 시간 초과 → 남은 시간 없음
    "time_low": "stop",                      # 다음 라운드를 시작할 시간이 모자람
}
# 2026-11-21 (LuckyBoys 선택 '전부 통과 or 제자리걸음'): 통과 테스트 수가 이 라운드 수만큼 연속으로 늘지 않으면 멈춘다.
#   1 이상 정수. 형식 거부로 수정안이 없던 라운드도 '늘지 않음'으로 센다.
MULTI_PERSONA_SELFFIX_STAGNATION_ROUNDS = 3
# 2026-11-14 (LuckyBoys 요청: 같은 이유로 못 고치는 일이 없게) 피드백 라운드의 답이 출력 검사에서 거부되면
# 거부 이유를 피드백에 넣어 같은 라운드를 이 횟수만큼 다시 시도한다. 0이면 예전처럼 바로 멈춘다.
# 사고 사례: job ca0a8c65(테트리스, Gemini) 2차 답은 맞게 고쳤는데 형식 검사에서 버려져 1건이 남았다.
MULTI_PERSONA_AUTO_APPLY_UNVERIFIED_RETRIES = 1
# 2026-11-10: apply_source_proposal(어느 AI든 수정 코드를 넘겨 적용하는 MCP 도구) 설정.
# MCP 요청 안에서 바로 pytest를 돌리므로 테스트 시간을 짧게 둔다(클라이언트 응답 대기 한도 고려).
APPLY_PROPOSAL_TEST_TIMEOUT_SECONDS = 120
# 제안 소스 최대 길이(문자). 비정상적으로 큰 입력으로 서버가 막히는 것을 막는다.
APPLY_PROPOSAL_MAX_CHARS = 500000
# 2026-11-10: 스스로 고치는 리뷰 앱의 LLM 선택(review_python_source provider 인자).
# 모든 CLI는 같은 계약을 지킨다: --source-path, --error-path, --output-dir 인자 /
# 세 제목 + 전체 소스 출력 / [출력 검증] 오류=[...] / [최종 검증된 답변]: 표시.
# cli: 실행할 리뷰 CLI / llm: CLI에 --provider로 넘길 LLM 이름(None이면 넘기지 않음, 전용 CLI).
# gemini·openai·claude는 같은 CLI를 쓰고 common/llm_provider.py가 LLM만 바꾼다.
MULTI_PERSONA_REVIEW_PROVIDERS = {
    "gemini": {"cli": "FastAPI/LangGraph/multi_persona/multi_persona_agent_gemini.py", "llm": "gemini"},
    "openai": {"cli": "FastAPI/LangGraph/multi_persona/multi_persona_agent_gemini.py", "llm": "openai"},
    "claude": {"cli": "FastAPI/LangGraph/multi_persona/multi_persona_agent_gemini.py", "llm": "claude"},
    # 2026-11-10 리뷰 경로 통일: ollama도 공용 CLI + common/llm_provider.py(11-01 튜닝 포함)를 쓴다.
    # 2026-11-21 (LuckyBoys 승인: ollama 3시간): gemma4:12b는 한 라운드에 30~45분이 걸려 3590초 안에 2라운드도
    #   못 끝냈다(job 16bef0c5). job_timeout_seconds가 있는 공급자만 이 작업 한도를 쓴다(다른 공급자는 3590초 그대로).
    "ollama": {"cli": "FastAPI/LangGraph/multi_persona/multi_persona_agent_gemini.py", "llm": "ollama",
               "job_timeout_seconds": 10800},
    # 이전 전용 CLI는 이름을 바꿔 남겨 둔다(비교·호환용).
    "ollama_gemma": {"cli": "FastAPI/LangGraph/multi_persona/multi_persona_agent_Ollama_Gemma4_e4b.py", "llm": None},
}
MULTI_PERSONA_REVIEW_DEFAULT_PROVIDER = "gemini"
# 2026-11-12 (LuckyBoys 선택 B): 소스 리뷰 job에서 Tavily 웹 검색 사용 여부. False면 공용 CLI에
# --no-web-search를 넘겨 검색 → router 재호출(토큰 낭비)을 막는다. 일반 질문 경로에는 영향 없음.
# 다시 켜려면 True로 바꾼다.
MULTI_PERSONA_REVIEW_WEB_SEARCH = False
# 2026-11-14 (LuckyBoys 요청): 다시 불러도 소용없는 LLM 공급자 오류(크레딧 소진·키 오류)는 바로 멈추고 보고한다.
# 오류 문장에 키(소문자로 비교)가 들어 있으면 값(보고용 이유)으로 판정한다. 429 같은 일시 오류는 넣지 않는다.
# 숫자 '402'만으로는 판정하지 않는다(일반 문장의 숫자와 헷갈리지 않게 공급자 오류 문구와 함께 적는다).
MULTI_PERSONA_FATAL_PROVIDER_ERRORS = {
    "credits are depleted": "LLM 크레딧 부족(402)",
    "402 resource_exhausted": "LLM 크레딧 부족(402)",
    "402 payment required": "LLM 크레딧 부족(402)",
    "invalid_api_key": "LLM API 키 오류(401)",
    "error code: 401": "LLM API 키 오류(401)",
    # 2026-11-16 (LuckyBoys 요청): 메모리 에이전트 시험에서 8번씩 반복 호출된 오류 추가.
    # Anthropic은 크레딧 부족을 402가 아니라 400 + 이 문구로 돌려준다.
    "credit balance is too low": "LLM 크레딧 부족(Anthropic)",
    # Ollama(llama-server)가 GPU 메모리를 못 잡으면 같은 요청을 다시 보내도 계속 실패한다.
    "out of memory": "Ollama GPU 메모리 부족",
    "out-of-memory": "Ollama GPU 메모리 부족",
    # Ollama 서버 내부 오류(llama-server 비정상 종료 등). 오류 문장 끝에 이 표시가 붙는다.
    "(status code: 500)": "Ollama 서버 오류(500)",
    # 2026-11-21 (LuckyBoys 선택 1안): 설정한 모델이 그 Ollama에 없음(404). pull 하기 전에는 다시 불러도 같다.
    #   Ollama 문장 예: model "gemma4:12b-it-q4_K_M" not found, try pulling it first (status code: 404)
    "try pulling it first": "Ollama 모델 없음(404)",
}
# 리뷰 CLI가 치명적 오류로 멈출 때 출력하는 표시 줄의 머리말과 종료 코드.
# 앱(harness/mcp/tools/multi_persona_tools.py)은 이 머리말로 멈춘 이유를 찾아 결과에 보고한다.
MULTI_PERSONA_FATAL_PROVIDER_MARKER = "[치명적 공급자 오류]"
MULTI_PERSONA_FATAL_PROVIDER_EXIT_CODE = 3
# 2026-11-21 (LuckyBoys 선택 1안): 스스로 고치는 앱이 Ollama 리뷰 전에 점검할 때 '리뷰에 쓰면 안 되는' 주소.
#   개발 서버 자체 Ollama(CPU 전용)는 리뷰 한 번에 40분 넘게 걸려 시간 초과로 끝났다(job 86dcf050).
#   자동 선택이 이 주소로 떨어지면(= 노트북 터널·AI 서버 터널이 끊김, AI 서버 IP 바뀜) AI를 부르지 않고 바로 멈춘다.
#   개발 서버 CPU로도 일부러 돌리려면 이 목록을 비우면 된다.
MULTI_PERSONA_OLLAMA_REJECT_URLS = ("http://127.0.0.1:11434",)
MULTI_PERSONA_OLLAMA_PREFLIGHT_TIMEOUT_SECONDS = 5  # /api/tags 대기(초)
# 2026-11-10: common/llm_provider.py가 읽는 LLM 공급자별 생성 정보(키 값은 환경변수에만 둔다).
# default_model이 빈 문자열이면 model_env 환경변수를 반드시 설정해야 한다(모델 이름을 추측하지 않음).
MULTI_PERSONA_LLM_PROVIDERS = {
    "gemini": {"module": "langchain_google_genai", "class": "ChatGoogleGenerativeAI",
               "model_env": "GEMINI_MODEL", "default_model": "gemini-2.5-flash",
               "key_envs": ["GEMINI_API_KEY", "GOOGLE_API_KEY"], "key_param": "api_key"},
    # 2026-11-10: gpt-6.1-terra는 temperature 인자를 거부한다(400 "Unsupported parameter") → False.
    "openai": {"module": "langchain_openai", "class": "ChatOpenAI",
               "model_env": "OPENAI_MODEL", "default_model": "",
               "key_envs": ["OPENAI_API_KEY"], "key_param": "api_key",
               "supports_temperature": False},
    # langchain_anthropic 패키지와 ANTHROPIC_API_KEY가 준비되면 바로 동작한다(2026-11-10 기준 둘 다 없음).
    # 2026-11-10: claude-opus-5-5는 temperature 인자를 거부한다(400) → supports_temperature False.
    "claude": {"module": "langchain_anthropic", "class": "ChatAnthropic",
               "model_env": "ANTHROPIC_MODEL", "default_model": "",
               "key_envs": ["ANTHROPIC_API_KEY"], "key_param": "api_key",
               "supports_temperature": False},
    "ollama": {"module": "langchain_ollama", "class": "ChatOllama",
               "model_env": "OLLAMA_MODEL", "default_model": "",
               "key_envs": [], "key_param": ""},
}
MULTI_PERSONA_LLM_DEFAULT_PROVIDER = "gemini"

# Shared transient workers use the account and protected files supplied by the operator.
SPS_MCP_WORKER_USER = "jeaje"
SPS_MCP_WORKER_SECRETS_FILE = "/etc/sps-harness/secrets.env"
# PARTNER는 하나의 LangGraph 구현을 유지하고 이 설정으로 Gemini/Ollama만 선택합니다.
SPS_SOURCE_PARTNER_MODEL_PROVIDER = os.getenv(
    "SPS_SOURCE_PARTNER_MODEL_PROVIDER", "gemini").strip().lower()
SPS_MAIN_ORCHESTRATOR_MODEL = os.getenv("GEMINI_MODEL", "gemini-3.5-flash")
SPS_SOURCE_PARTNER_OLLAMA_MODEL = os.getenv(
    "SPS_SOURCE_PARTNER_OLLAMA_MODEL", os.getenv("OLLAMA_MODEL", "gemma4:e4b")).strip()
# 2026-11-01 LuckyBoys: 빈 값이면 아래 SPS_SOURCE_PARTNER_OLLAMA_CANDIDATES에서 자동 선택한다.
# 값을 지정하면(환경변수) 자동 선택 없이 그 주소만 쓴다(수동 고정). 예전 기본값(127.0.0.1:11434 고정)은
# 개발 서버 CPU Ollama로만 붙어 GPU 0%·로딩 18~30초였다(harness/memory/ollama_latency_diagnose_20261101_c.json).
SPS_SOURCE_PARTNER_OLLAMA_BASE_URL = os.getenv(
    "SPS_SOURCE_PARTNER_OLLAMA_BASE_URL", os.getenv("OLLAMA_BASE_URL", "")).strip()
SPS_SOURCE_PARTNER_OLLAMA_TIMEOUT_SECONDS = float(os.getenv(
    "SPS_SOURCE_PARTNER_OLLAMA_TIMEOUT_SECONDS", os.getenv("OLLAMA_TIMEOUT", "300")))
# 2026-11-01 LuckyBoys: Gemini 대기 시간을 Ollama와 분리한다. 환경변수로 바꿀 수 있고 기본값은 기존과 같은 300초.
# 이유: 프로브가 Gemini에도 Ollama 값을 써서, Ollama 값을 늘리면 Gemini 장애 감지도 같이 늦어졌다(Gemini 실측 9초).
# 사용처: harness/scripts/probe_partner_providers_20261025.py의 _provider_timeout()
SPS_SOURCE_PARTNER_GEMINI_TIMEOUT_SECONDS = float(os.getenv(
    "SPS_SOURCE_PARTNER_GEMINI_TIMEOUT_SECONDS", "300"))
SPS_MAIN_ORCHESTRATOR_TIMEOUT_SECONDS = 120
# /api/gemini/chat 인증용 공유 비밀키. 비어 있으면 서버가 모든 요청을 거부한다(기본값 거부).
SPS_MAIN_ORCHESTRATOR_API_KEY = os.getenv("SPS_MAIN_ORCHESTRATOR_API_KEY", "")
SPS_MAIN_ORCHESTRATOR_HOST = os.getenv("SPS_MAIN_ORCHESTRATOR_HOST", "127.0.0.1")
# 8080은 nginx(sps-mcp-router.conf)가 이미 점유 중이라 충돌한다. 비어 있는 내부 포트를 기본값으로 둔다.
SPS_MAIN_ORCHESTRATOR_PORT = int(os.getenv("SPS_MAIN_ORCHESTRATOR_PORT", "8081"))


# 자율 소스 수정(harness/source_repair.py 하나로 통일): 아래 파일만 수정할 수 있습니다.
# 설정/인증/검증기/테스트는 수정 대상에 넣지 않으며, 검증 통과 시 git add까지만 하고 커밋하지 않습니다.
# 2026-10-25: 공개 문서 수집 자율 수리(AUTODISCOVER_SELF_REPAIR.allowed_paths)도 같은 엔진을 쓰도록 두 파일 추가.
SPS_SOURCE_REPAIR_ALLOWED_PATHS = (
    "FastAPI/LangGraph/sps_main_orchestrator.py",
    "FastAPI/LangGraph/Agent_Import_PFDs/LangGraph_Network_Sniffer.py",
    "FastAPI/LangGraph/Agent_Import_PFDs/profile_autodiscover.py",
    "FastAPI/LangGraph/Agent_Import_PFDs/public_document_catalog_collector.py",
)
SPS_SOURCE_REPAIR_MAX_BYTES = 200000
# 회귀 테스트 한 회의 제한. 수정 전/후와 dry-run 검증에 각각 적용합니다.
SPS_SOURCE_REPAIR_TEST_TIMEOUT_SECONDS = 5
SPS_SOURCE_REPAIR_AUDIT_DIR = "harness/memory/source_repairs"
# Tavily 웹 검색 공통 설정(common.common_function.web_search).
# 20261025 | 요청: LuckyBoys | 작성: Claude | 수집 온보딩(공시실 URL 탐색)과 페르소나 체인 도구가 함께 쓴다.
# 키 값은 소스·설정에 두지 않는다. 아래는 환경변수 '이름'일 뿐이며 값은 langchain_tavily가 직접 읽는다.
SPS_WEB_SEARCH = {
    "api_key_env": "TAVILY_API_KEY",          # 키를 담은 환경변수 이름(값 아님)
    "max_results": 5,                         # 기본 결과 수
    "max_results_cap": 10,                    # 호출자가 더 달라고 해도 넘지 않는 상한(비용·토큰 억제)
    "max_query_chars": 500,                   # 검색어 길이 상한(잘못된 입력 차단)
    "onboard_query": "{company} {keyword} 공시실",   # 온보딩 검색어 틀(특정 사이트 이름 하드코딩 없음)
}
# 보험사뿐 아니라 공사/정부/복지관 등 공개 문서 수집에 같은 저장 설정을 사용합니다.
SPS_DOCUMENT_DOWNLOAD_DIR = BASE_DIR / "downloaded_docs"


# 긴 Python 소스 리뷰의 요청별 입력/출력 예산. GPU 메모리와 함께 실측합니다.
MULTI_PERSONA_OLLAMA_CONTEXT = 65536
MULTI_PERSONA_OLLAMA_OUTPUT = 32768

# SSH 대상은 중앙 설정으로 관리하고 비밀키는 경로로만 참조합니다.
SPS_SSH_TARGETS = {
    "gpu": {
        "host": os.getenv("SPS_GPU_SSH_HOST", "8.230.3.46"),   # 2026-11-16 AI 서버 재기동으로 IP 변경(이전 34.64.134.46)
        "user": os.getenv("SPS_GPU_SSH_USER", "jeajea_park"),
        "port": int(os.getenv("SPS_GPU_SSH_PORT", "22")),
        "identity_file": os.getenv("SPS_GPU_SSH_IDENTITY_FILE", "/home/jeaje/.ssh/google_compute_engine"),
        "known_hosts": os.getenv("SPS_GPU_SSH_KNOWN_HOSTS", "/home/jeaje/.ssh/known_hosts"),
        "root": os.getenv("SPS_GPU_PROJECT_ROOT", "/data/vm_project"),
        "python": os.getenv("SPS_GPU_PYTHON", "/data/vm_project/venv/bin/python"),
    },
}
# 2026-11-01 LuckyBoys: PARTNER Ollama 주소 자동 선택 후보(앞에서부터 /api/version 확인, 처음 응답하는 곳 사용).
# 1) GPU 서버: 켤 때마다 IP가 바뀌므로 SPS_GPU_SSH_HOST 하나만 바꾸면 ssh 접속과 Ollama 주소가 함께 바뀐다.
# 2) 노트북 RTX 3060 6GB: 노트북에서 ssh -N -R 11435:127.0.0.1:11434 로 연 역방향 터널 포트.
# 3) 개발 서버 자체 Ollama(CPU 전용): 마지막 대안.
# 환경변수 SPS_SOURCE_PARTNER_OLLAMA_CANDIDATES(쉼표 구분)로 목록 전체를 바꿀 수 있다. 사용처: common_function.resolve_ollama_base_url
SPS_SOURCE_PARTNER_OLLAMA_CANDIDATES = tuple(url.strip() for url in os.getenv(
    "SPS_SOURCE_PARTNER_OLLAMA_CANDIDATES",
    f"http://{SPS_SSH_TARGETS['gpu']['host']}:11434,http://127.0.0.1:11435,http://127.0.0.1:11434",
).split(",") if url.strip())
# 후보 하나를 확인할 때 기다리는 시간(초). 꺼진 GPU 서버에서 오래 멈추지 않도록 짧게 둔다.
SPS_SOURCE_PARTNER_OLLAMA_PROBE_TIMEOUT_SECONDS = float(os.getenv(
    "SPS_SOURCE_PARTNER_OLLAMA_PROBE_TIMEOUT_SECONDS", "3"))
# 개별 SSH는 150초 이내 응답하며 장기 모델 작업은 원격에서 별도로 실행합니다.
SPS_SSH_JOB_TIMEOUT_SECONDS = SPS_SOURCE_EXECUTION_TIMEOUT_SECONDS
SPS_SSH_REQUEST_TIMEOUT_SECONDS = 120
# 종목 선별 공통 설정: 비밀값은 기존 서비스 환경변수에서만 읽고 출력하지 않습니다.
STOCK_ANALYSIS = {
    "lookback": 30, "base_days": 5, "breakout_days": 20,
    "volume_multiple": 1.5, "max_drawdown": 0.10, "max_pe": 25.0,
    "stale_days": 7, "evidence_stale_days": 120,
    "timeout": 15, "max_pages": 5, "request_interval": 0.6,
    "kis_base_url": "https://openapi.koreainvestment.com:9443",
    "kis_app_key_env": "KIS_APP_KEY", "kis_app_secret_env": "KIS_APP_SECRET",
    # 필요한 두 시세 API만 허용합니다. 계좌 조회나 주문 API는 포함하지 않습니다.
    "kis_routes": {
        "KR": ("/uapi/domestic-stock/v1/quotations/inquire-daily-itemchartprice", "FHKST03010100"),
        "US": ("/uapi/overseas-price/v1/quotations/dailyprice", "HHDFS76240000"),
    },
}
# SPS Harness MCP 소스 도구 자동 감사 설정(harness/mcp/source_audit.py가 사용).
# - verified_query_id: cm_verified_sql_query에 등록된 harness_source_audit INSERT Query ID.
#   (2026-10-24 재등록, 11개 파라미터: id, user_id, file_name, task_type, learning_type, accuracy,
#    created_by, updated_by, program_id, client_ip, 중복검사 id. 이전 ..._00004는 id 컬럼이 없어 폐기 대상)
# - identifier_object_code: 행 id(Level 4)를 발급할 sp_object Object 코드(SP_SR_SOURCE_AUDIT_20261024_00001).
# - agent_session_id: user_id에 넣을 AI 에이전트 세션 ID({AI 모델 ID}_{YYYYMMDD}_{HHMMSS} KST).
#   MCP 서버는 호출한 에이전트를 알 수 없으므로 환경변수로 지정한다.
# - requester_id: created_by/updated_by에 넣을 요청자. 환경변수로 바꿀 수 있다.
SOURCE_AUDIT = {
    "verified_query_id": os.getenv(
        "SPS_SOURCE_AUDIT_QUERY_ID", "CM_CO_HARNESS_SOURCE_AUDIT_CREATE_L4_20261024_183559_00006"
    ),
    "identifier_object_code": "SOURCE_AUDIT",
    "agent_session_id": os.getenv("SPS_SOURCE_AUDIT_AGENT_SESSION_ID", "SPS_HARNESS_MCP"),
    "requester_id": os.getenv("SPS_SOURCE_AUDIT_REQUESTER_ID", "jeaje"),
    "program_id": "SPS_HARNESS_SOURCE_AUDIT",
    "client_ip": "127.0.0.1",
}
# 공개 문서 카탈로그 수집기(FastAPI/LangGraph/Agent_Import_PFDs/public_document_catalog_collector.py) 공통 설정.
# - 2026-10-25 사용자 지침 4: 수집기 안에 박혀 있던 상한·기준값을 루트 config로 옮김.
# - max_time_limit_seconds: 워커 1회 실행 최대 시간(LuckyBoys 승인 30,000초).
# - max_pdf_bytes / min_free_disk_bytes: 비정상 대용량 응답 차단 / 서버 디스크 고갈 방지 기준.
# - profile_dir: 사이트별 수집 프로파일(JSON) 폴더. 엔진은 사이트를 모르고 이 데이터만 해석한다.
# - output_subdir: config.OUTPUT_PATH 아래 결과 폴더 이름.
# - systemd_run_command / service_user: start 모드가 MCP 서비스와 분리된 유닛으로 워커를 띄울 때 사용.
#   (MCP 재시작 시 워커가 같이 꺼져 방치되던 문제 방지. sudo -n이라 비밀번호를 묻지 않고 실패하면 즉시 오류)
PUBLIC_DOCUMENT_COLLECTOR = {
    "max_time_limit_seconds": 30000,
    "max_pdf_bytes": 512 * 1024 ** 2,
    "min_free_disk_bytes": 1024 ** 3,
    "profile_dir": BASE_DIR / "FastAPI/LangGraph/Agent_Import_PFDs/profiles",
    "output_subdir": "insurance_docs",
    # 20261030 | 요청: LuckyBoys | 작성: Claude — 별도 작업에 키 파일 2개를 넘긴다(값은 소스에서 읽지 않음).
    # 이유: 없으면 자기 수리(Gemini)·웹 검색(Tavily)이 "API key required"로 즉시 실패(10/25·10/29 삼성화재 재현).
    # 형식은 프로젝트 기존 실행 예시(multi_persona_agent_gemini.py 상단 주석)와 같다.
    "systemd_run_command": ["sudo", "-n", "systemd-run", "--collect", "--quiet",
                            "-p", f"EnvironmentFile={BASE_DIR / '.env'}",
                            "-p", "EnvironmentFile=/etc/sps-harness/secrets.env"],
    "service_user": os.getenv("SPS_COLLECTOR_SERVICE_USER", "jeaje"),
    "unit_prefix": "sps-collector-",
}
# 수집 프로파일 자동 탐색기(FastAPI/LangGraph/Agent_Import_PFDs/profile_autodiscover.py) 설정. 2026-10-25 추가.
# - 브라우저(Playwright)로 시작 페이지를 클릭하며 요청을 기록 → 프로파일 추론 → PDF 1건 실검증.
# - max_depth: 목록을 몇 단계까지 클릭해 내려갈지 / click_wait_ms: 클릭 후 다음 요청을 기다리는 시간
# - max_elements: 한 화면에서 비교할 요소 수 상한 / max_attempts: 검증 실패 시 다른 항목으로 재탐색 횟수
# - work_subdir: config.OUTPUT_PATH 아래 캡처·후보·증빙 저장 폴더
PROFILE_AUTODISCOVER = {
    "max_depth": 8,
    "click_wait_ms": 10000,
    "page_timeout_ms": 45000,
    "max_elements": 3000,
    "max_attempts": 3,
    "validate_documents_per_seed": 3,   # 실검증 시 시작 페이지마다 시도할 문서 수(한 건 성공이면 통과)
    # 다른 항목으로 재탐색하면 풀릴 수 있는 오류(정규식). 여기에 없는 오류는 '처음 보는 유형'으로 보고
    # 재시도 없이 즉시 NEEDS_NEW_RULE로 멈춘다(2026-10-25 LuckyBoys 지시: 헛된 3회 반복 금지).
    "retryable_error_patterns": [
        r"Timeout", r"timed out", r"Connection(Reset|Refused|Error)", r"URLError", r"RemoteDisconnected",
        r"HTTP Error (429|5\d\d)", r"empty list at", r"no valid document for seed",
    ],
    "delay_seconds": 0.3,
    "timeout_seconds": 45,
    "user_agent": "Mozilla/5.0 (SPS public disclosure collector)",
    "work_subdir": "insurance_docs/_autodiscover",
}
# 실행 도구(mcp_codex_apps_run_python_source) 위험 명령 승인 설정(harness/mcp/tools/command_approval.py). 2026-10-25 추가.
# LuckyBoys: "승인 기능을 붙이고 무슨 명령어를 쓰는지 반드시 표시". 실행할 파일과 그 파일이 import하는 프로젝트 모듈에서
# 아래 명령·모듈을 찾으면 결과에 표시하고, approved_commands로 '찾은 이름 전체'를 넘겨야만 실행한다.
# - shell_commands: 따옴표 문자열의 첫 단어로 쓰인 명령(subprocess 인자 등) / python_modules: 네트워크·원격 접속 모듈
# - max_import_depth: 따라가며 읽는 import 깊이(연결 파일 → harness/scripts 실제 소스까지 보려고 3)
SPS_EXECUTION_APPROVAL = {
    "shell_commands": [
        "sudo", "su", "ssh", "scp", "sftp", "rsync", "curl", "wget", "nc", "ncat", "telnet",
        "systemctl", "systemd-run", "kill", "pkill", "killall", "reboot", "shutdown", "docker", "crontab",
    ],
    "python_modules": [
        "requests", "httpx", "aiohttp", "urllib.request", "http.client", "paramiko", "fabric",
        "socket", "smtplib", "ftplib",
    ],
    "max_import_depth": 3,
}
# SPS 13개 페르소나 원문 프롬프트 위치(common/persona_source.py PersonaSource 기본값). 2026-10-25 추가.
# 스킬 references 원문과 sha256 동일(harness/scripts/sync_persona_prompts.py로 복사·검증). 모든 페르소나 런타임이 공유.
SPS_PERSONA_PROMPTS = {
    "persona_dir": BASE_DIR / "harness/personas/references",
}
# 자동 탐색 자기 수리 루프(harness/mcp/agents/autodiscover_self_repair.py — Harness 소스라 haness에 둠, 수집기는 경로로 연결). 2026-10-25 추가.
# auto 결과가 NEEDS_NEW_RULE(처음 보는 실패)이면 PARTNER 에이전트(harness/mcp/agents/source_partner_agent.py)에
# 증빙을 넘겨 코드를 고치게 하고, 테스트가 통과한 변경만 적용·git add 한다(커밋 안 함: LuckyBoys "자동 적용 + add만").
# - enabled: false면 수리 없이 NEEDS_NEW_RULE 그대로 보고 / max_repair_rounds: 한 번 실행에서 수리 시도 횟수
# - agent_timeout_seconds / agent_recursion_limit: 에이전트 1회 실행 시간·도구 왕복 상한
# - allowed_paths: 에이전트가 patch할 수 있는 유일한 소스. 그 밖 파일 patch·기존 테스트 수정은 적용 '전에' 거부된다
#   (source_partner_agent의 allowed_source_paths). harness/tests/ 아래는 '새 파일 추가'만 허용
# - report_dir: 수리 증빙(repair_<시각>.json) 저장 위치. Harness 산출물이라 harness/reports 아래(일반 지침 10)
# - autodiscover_script: 수리 전후 새 프로세스로 실행할 탐색기 경로(FastAPI 쪽 원래 위치 그대로 연결)
# - regression_tests: 수리 뒤 반드시 통과해야 하는 기존 테스트(실패하면 원복하고 REPAIR_FAILED)
# - auto_timeout_seconds: 수리 전후 auto를 새 프로세스로 돌릴 때 시간 상한(고친 코드를 새로 읽기 위해 별도 프로세스)
AUTODISCOVER_SELF_REPAIR = {
    "enabled": True,
    "max_repair_rounds": 2,   # 1라운드 고정 순서 체인, 2라운드 ORCHESTRATOR 자율 계획(LuckyBoys 2026-10-25)
    "agent_timeout_seconds": 900,
    # 수리 체인 LangGraph 단계 상한. 64→20 (LuckyBoys 2026-11-14: 체인이 맴돌지 않게 최대 20, 테스트 test_repair_chain_recursion_cap_20261114.py)
    "agent_recursion_limit": 20,
    "autodiscover_script": BASE_DIR / "FastAPI/LangGraph/Agent_Import_PFDs/profile_autodiscover.py",
    "allowed_paths": [
        "FastAPI/LangGraph/Agent_Import_PFDs/profile_autodiscover.py",
        "FastAPI/LangGraph/Agent_Import_PFDs/public_document_catalog_collector.py",
    ],
    "regression_tests": [
        "harness/tests/test_public_document_catalog_collector.py",
        "harness/tests/test_collector_seedless_post_download.py",
        "harness/tests/test_collector_self_heal.py",
        "harness/tests/test_collector_worker_self_heal.py",
        "harness/tests/test_profile_autodiscover_inference.py",
        "harness/tests/test_autodiscover_failure_classification.py",
        "harness/tests/test_autodiscover_self_repair.py",
    ],
    "report_dir": BASE_DIR / "harness/reports/autodiscover_repair",
    # 페르소나 체인(2026-10-25 LuckyBoys 승인): SPS ORCHESTRATOR 스킬 실행 방식 그대로, 원문 프롬프트를 시스템 프롬프트로 쓴다.
    # persona_dir의 <이름>.md는 스킬 references 원문과 sha256 동일(harness/scripts/sync_persona_prompts.py로 복사·검증).
    # LuckyBoys 2026-10-25: "고정 순서 체인은 처음 한 번만, 두 번째는 ORCHESTRATOR 자율, 마지막만 지정".
    # - first_round_plan: 1라운드 고정 순서(뒤에 PARTNER 통합 자동). autonomous_from_round 이상은 ORCHESTRATOR가
    #   persona_dir의 13개 원문 중 필요한 페르소나와 순서를 직접 정한다. 프로그램이 지정하는 것은 마지막 PARTNER뿐.
    # - max_personas: ORCHESTRATOR 제외 호출 상한(마지막 PARTNER 포함, 스킬 기본 5). 회귀 테스트는 항상 프로그램이 실행.
    "persona_dir": SPS_PERSONA_PROMPTS["persona_dir"],   # 공통 위치를 그대로 쓴다(중복 경로 금지)
    "first_round_plan": ["BUG_HUNTER", "PARTNER", "REVIEWER", "TESTER"],
    "autonomous_from_round": 2,
    "max_personas": 5,
    "regression_timeout_seconds": 600,
    "auto_timeout_seconds": 1800,
}

# 로컬 8003 API의 터미널 검증 설정. 비밀키 값은 저장하지 않고 보호 파일 경로만 지정한다.
AGENT_CLI = {
    "endpoint": "http://127.0.0.1:8003/api/agent/context",
    "timeout_seconds": 90,
    "auth_env_file": "/etc/sps-harness/secrets.env",
    "token_lifetime_seconds": 180,
    "max_query_length": 12000,
}

# Executable persona routing budgets. Plans are selected by the orchestrator,
# not by this configuration; long workers are polled without holding MCP open.
SPS_PERSONA_SOURCE = {
    "max_personas": 5,
    "max_role_calls": 10,
    "max_llm_calls": 45,
    "check_timeout_seconds": 25,
    "model_timeout_seconds": 90,
    "job_timeout_seconds": 600,
    "graph_recursion_limit": 160,
    "max_file_bytes": 24000,
    "max_output_tokens": 4096,
    "max_plan_rounds": 2,
}

# 2026-11-10 LuckyBoys: 범용 자기 수리 엔진(harness/mcp/agents/self_repair_engine.py) 설정.
# "어디서나 쓰는 스스로 고치는 앱": 등록된 대상 실행 → 판정 → 실패 시 페르소나 수리 체인 → git add(커밋 없음) → 재실행.
# - enabled: False 면 판정만 하고 수리하지 않는다
# - default_max_rounds: 대상 스펙에 max_rounds 가 없을 때 쓰는 수리 라운드 수(엔진 상한 5, 비용 보호)
# - report_dir: 수리 증빙 JSON 저장 위치(대상 이름별 하위 폴더)
# - job_dir: self_repair_run 백그라운드 job 의 request/result 저장 위치(0600 파일)
# - job_timeout_seconds: 독립 systemd 유닛 전체 상한(실행 + 수리 + 재실행 포함)
# - max_evidence_chars: 수리 작업문에 넣는 실행 출력 끝부분 길이
# - repository_table: MariaDB 등록소 테이블 이름(2차 DDL 승인 전에는 미생성 → repository 백엔드는 명확히 거부)
SELF_REPAIR = {
    "enabled": True,
    "default_max_rounds": 2,
    "report_dir": "harness/reports/self_repair",
    "job_dir": "harness/memory/self_repair_jobs",
    "job_timeout_seconds": 36000,
    "max_evidence_chars": 4000,
    "repository_table": "sps_self_repair_target",
}

# 2026-11-10 LuckyBoys: document_collect 대상(수집 건수가 목표보다 적어도 수리)이 쓰는 수집기 실행 설정.
# - collector_script: 사이트 비종속 수집기(FastAPI 쪽 원래 위치 그대로 연결, 사이트 이름 하드코딩 없음)
# - collect_time_limit_seconds: 수집기 1회 실행 상한(수집기 자체 상한보다 크면 작은 값을 쓴다, 이어받기 지원)
# - collector_grace_seconds: 수집기 프로세스 강제 종료 전 결과(status.json) 저장 여유
SELF_REPAIR_COLLECT = {
    "collector_script": BASE_DIR / "FastAPI/LangGraph/Agent_Import_PFDs/public_document_catalog_collector.py",
    "collect_time_limit_seconds": 30000,
    "collector_grace_seconds": 60,
    # 2026-11-12 LuckyBoys: self_repair_collect_tools 가 읽는데 없던 키(KeyError, KNOWN_BROKEN 해소).
    # job_timeout_seconds 는 LuckyBoys 지정 36,000초, job_dir 은 엔진(self_repair_jobs)과 섞이지 않게 별도 폴더.
    "job_timeout_seconds": 36000,
    "job_dir": "harness/memory/self_repair_collect_jobs",
}

# >>> SELF_REPAIR_TARGETS (generated)
# 자동 생성: self_repair_target_register 가 관리한다. 손으로 고치지 말 것.
SELF_REPAIR_TARGETS = {
    "document_collect": {
        "name": "document_collect",
        "command": {"module": "harness.mcp.tools.document_collect_target"},
        "args_template": ["--collect", "{name}", "{company_name}", "{expected_min_count}"],
        "params": ["name", "company_name", "expected_min_count"],
        "verdict": {"type": "json_min", "source": "stdout", "field": "success",
                    "min_param": "expected_min_count"},
        "scope": {
            "allowed_paths": [
                "FastAPI/LangGraph/Agent_Import_PFDs/public_document_catalog_collector.py",
                "FastAPI/LangGraph/Agent_Import_PFDs/profile_autodiscover.py",
            ],
            "regression_tests": [
                "harness/tests/test_public_document_catalog_collector.py",
                "harness/tests/test_collector_seedless_post_download.py",
                "harness/tests/test_collector_self_heal.py",
                "harness/tests/test_collector_worker_self_heal.py",
                "harness/tests/test_profile_autodiscover_inference.py",
                "harness/tests/test_autodiscover_failure_classification.py",
                "harness/tests/test_autodiscover_self_repair.py",
                "harness/tests/test_document_collect_target_20261111.py",
            ],
        },
        "max_rounds": 2,
        "timeout_seconds": 36000,
    },
}
# <<< SELF_REPAIR_TARGETS
# 2026-11-14 (LuckyBoys 요청): git_stage_manage(action="uncommit") — 커밋을 풀어 staged로 되돌리기.
# 한 번에 풀 수 있는 최대 커밋 수(실수로 오래된 기록까지 푸는 것 방지).
GIT_UNCOMMIT_MAX_COMMITS = 30
# 풀기 전 HEAD를 남겨 두는 백업 ref 머리말(뒤에 -YYYYMMDD-HHMMSS). 되돌리기: git reset --soft <백업 ref>
GIT_UNCOMMIT_BACKUP_REF_PREFIX = "refs/harness-backup/uncommit"
# 2026-11-15 (LuckyBoys 결정): 허용 목록 sudo 실행(common.sudo_runner.run_allowed_sudo).
# 새 MCP 도구 없이 mcp_codex_apps_run_python_source의 위험 명령 승인(approval_commands)을 거친 뒤에만 실행된다.
# 키: 명령 앞부분(고정), 값: 그 뒤에 올 수 있는 인자(모두 이 목록 안, 하나 이상). 값이 빈 튜플이면 인자 없이만.
# 뺀 것(LuckyBoys 결정): rm -rf, kill, python3 -c, cat(보호 파일) — 무엇이든 할 수 있게 되는 명령.
SUDO_ALLOWED_SERVICES = (
    "sps-harness.service", "sps-gemini-agent.service", "sps-multi-persona.service",
    "fastapi-insurance-rag.service", "mongod",
)
SUDO_ALLOWED_COMMANDS = {
    # 서비스 재시작·시작·정지·자동 시작 켜기/끄기·상태 확인
    ("systemctl", "restart"): SUDO_ALLOWED_SERVICES,
    ("systemctl", "start"): SUDO_ALLOWED_SERVICES,
    ("systemctl", "stop"): SUDO_ALLOWED_SERVICES,
    ("systemctl", "enable"): SUDO_ALLOWED_SERVICES,
    ("systemctl", "enable", "--now"): SUDO_ALLOWED_SERVICES,
    ("systemctl", "disable"): SUDO_ALLOWED_SERVICES,
    ("systemctl", "is-enabled"): SUDO_ALLOWED_SERVICES,
    ("systemctl", "is-active"): SUDO_ALLOWED_SERVICES,
    ("systemctl", "status", "--no-pager"): SUDO_ALLOWED_SERVICES,
    # 서비스 설정 다시 읽기(인자 없음)
    ("systemctl", "daemon-reload"): (),
    # sudo 권한 확인(인자 없음)
    ("-l",): (),
    # Ulixee Hero(Chrome) 실행에 필요한 라이브러리(2026-11-15: libcups.so.2 누락). OS 버전에 따라 이름이 다름.
    ("apt-get", "install", "-y"): ("libcups2", "libcups2t64"),
}
# sudo 명령 하나의 최대 실행 시간(초)
SUDO_TIMEOUT_SECONDS = 600


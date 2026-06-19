# utils.py ★ 7.16.4
# ⭐ 공통 도구 모음 — 자잘한 함수는 전부 여기에!
#
# 초등학생 설명:
#   학교 필통처럼 자주 쓰는 도구를 한 곳에 모았어요.
#   여러 파일에서 "from utils import ..." 로 가져다 써요.
#
# 포함된 기능:
#   📝 JSON 읽기/쓰기
#   📋 이벤트 로그 기록
#   ⏰ 타임스탬프 생성
#   📁 폴더 자동 생성
#   📄 CSV 인코딩 자동감지 읽기
#   🔑 파일 MD5 해시 계산
#   📦 중첩 dict 평탄화
#
# 참고: Smart File Organizer utils.py 구조 반영
#
# [버전 이력]
#   7.16.4 (2026-06-16): 주석 전면 강화, Smart File Organizer 구조 참고
#   7.0.0  (2026-06-15): CSV 인코딩 자동감지 / 파일 해시 / dict 평탄화 추가
#   6.0.0  (이전):       기본 JSON/로그 유틸

import json, os, logging, hashlib
from datetime import datetime
from typing import Any
from config import LOG_PATH, OUTPUT_PATH, REQUIRED_DIRS, STANDARD_DIRS, LOG_FORMAT, LOG_DATE_FORMAT


# ─────────────────────────────────────────────────────────────────────────────
# 📝 로거(기록기) 설정
# 초등학생 설명: AI가 한 일을 파일과 화면에 동시에 기록해요!
# ─────────────────────────────────────────────────────────────────────────────

# 로그 폴더 없으면 자동 생성
os.makedirs(LOG_PATH, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format=LOG_FORMAT,
    datefmt=LOG_DATE_FORMAT,
    handlers=[
        # 파일에 기록 (logs/app.log)
        logging.FileHandler(
            os.path.join(LOG_PATH, "app.log"),
            encoding="utf-8"
        ),
        # 터미널에도 출력
        logging.StreamHandler(),
    ],
)

# 전체 프로젝트에서 공용으로 쓰는 로거
# 사용법: from utils import logger; logger.info("메시지")
logger = logging.getLogger("vm_7.16.4")


# ─────────────────────────────────────────────────────────────────────────────
# 📄 JSON 파일 읽기/쓰기
# 초등학생 설명: 파일에서 데이터를 꺼내오고 저장하는 함수예요!
# ─────────────────────────────────────────────────────────────────────────────

def load_json(path: str) -> Any:
    """
    JSON 파일 읽기

    초등학생 설명:
        파일에 저장된 데이터를 꺼내오는 함수예요.
        마치 서랍에서 물건을 꺼내는 것과 같아요.

    Args:
        path : 읽을 JSON 파일 경로

    Returns:
        파일 내용 (dict, list 등)

    Raises:
        FileNotFoundError : 파일이 없을 때
        json.JSONDecodeError : JSON 형식이 잘못됐을 때
    """
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_json(path: str, data: Any) -> None:
    """
    JSON 파일 저장

    초등학생 설명:
        데이터를 파일에 저장하는 함수예요.
        마치 서랍에 물건을 넣는 것과 같아요.
        폴더가 없으면 자동으로 만들어요.

    Args:
        path : 저장할 파일 경로 (폴더 없으면 자동 생성)
        data : 저장할 데이터 (dict, list 등)
    """
    # 저장할 폴더가 없으면 자동 생성
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        # ensure_ascii=False: 한글이 깨지지 않게 저장
        # indent=4: 들여쓰기 4칸으로 보기 좋게 저장
        json.dump(data, f, indent=4, ensure_ascii=False)


# ─────────────────────────────────────────────────────────────────────────────
# 📋 이벤트 로그 기록
# 초등학생 설명: 중요한 일이 일어나면 일기처럼 남겨요!
# ─────────────────────────────────────────────────────────────────────────────

def log_event(name: str, data: dict) -> None:
    """
    이벤트를 타임스탬프 JSON 파일로 기록

    초등학생 설명:
        "언제 어떤 일이 있었는지" 날짜/시간이 찍힌 일기처럼 저장해요.
        나중에 문제가 생기면 이 기록을 보고 원인을 찾을 수 있어요.

    파일명 형식: {name}_{YYYYMMDD_HHMMSS}.json
    예시: pipeline_7.16.4_20260616_143022.json

    Args:
        name : 이벤트 이름 (예: "pipeline_7.16.4", "cron_daily_retrain")
        data : 기록할 데이터 딕셔너리 (자동으로 logged_at 필드 추가됨)
    """
    ts   = get_ts_file()
    path = os.path.join(LOG_PATH, f"{name}_{ts}.json")

    # logged_at 자동 추가
    data["logged_at"] = ts
    save_json(path, data)
    logger.info(f"📝 이벤트 기록: {name}")


# ─────────────────────────────────────────────────────────────────────────────
# ⏰ 타임스탬프 (시간 문자열) 생성
# 초등학생 설명: "지금 몇 시야?" 알려주는 함수예요!
# ─────────────────────────────────────────────────────────────────────────────

def get_timestamp() -> str:
    """
    읽기 좋은 형식의 현재 시각 반환

    초등학생 설명:
        "2026-06-16 14:30:22" 처럼 사람이 읽기 편한 형식으로 알려줘요.

    Returns:
        "YYYY-MM-DD HH:MM:SS" 형식의 문자열
    """
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def get_ts_file() -> str:
    """
    파일 이름에 쓸 수 있는 타임스탬프 반환

    초등학생 설명:
        파일 이름에는 ":" 같은 특수문자를 쓸 수 없어서,
        "20260616_143022" 처럼 숫자와 언더바만 써요.

    Returns:
        "YYYYMMDD_HHMMSS" 형식의 문자열 (파일명에 안전)
    """
    return datetime.now().strftime("%Y%m%d_%H%M%S")


# ─────────────────────────────────────────────────────────────────────────────
# 📁 폴더 자동 생성
# 초등학생 설명: 필요한 방들을 미리 만들어두는 함수예요!
# ─────────────────────────────────────────────────────────────────────────────

def ensure_dirs() -> None:
    """
    config.py의 REQUIRED_DIRS 목록에 있는 폴더 전부 자동 생성

    초등학생 설명:
        집을 짓기 전에 방들을 먼저 만들어두는 것과 같아요.
        이미 있는 폴더는 그냥 넘어가요 (exist_ok=True).

    생성 대상:
        config.py의 REQUIRED_DIRS 목록 참고
        (logs, outputs, outputs/charts, outputs/reports, models, data, uploads 등)
    """
    all_dirs = list(REQUIRED_DIRS) + [str(d) for d in STANDARD_DIRS]

    for d in all_dirs:
        os.makedirs(d, exist_ok=True)

    logger.info(f"📁 폴더 초기화 완료 ({len(all_dirs)}개)")


# ─────────────────────────────────────────────────────────────────────────────
# 📄 CSV 인코딩 자동감지 읽기
# 초등학생 설명: 한글 깨짐 없이 CSV를 읽는 함수예요!
# ─────────────────────────────────────────────────────────────────────────────

def read_csv_safe(path: str):
    """
    인코딩 자동감지 CSV 읽기 (한글 깨짐 방지)

    초등학생 설명:
        한글 책을 읽으려면 알맞은 안경을 써야 하듯이,
        CSV 파일도 알맞은 인코딩 방식으로 읽어야 해요.
        여러 방식을 자동으로 시도해서 가장 잘 맞는 걸 골라요!

    시도 순서:
        1. utf-8       (표준 유니코드)
        2. utf-8-sig   (BOM 포함 UTF-8, 엑셀 저장 시 자주 생김)
        3. cp949       (Windows 한글)
        4. euc-kr      (구형 한글)

    Args:
        path : 읽을 CSV 파일 경로

    Returns:
        pandas DataFrame

    Raises:
        ValueError : 4가지 방식 모두 실패 시
    """
    import pandas as pd

    for enc in ["utf-8", "utf-8-sig", "cp949", "euc-kr"]:
        try:
            df = pd.read_csv(path, encoding=enc)
            logger.info(f"📄 CSV 읽기 성공 [{enc}]: {os.path.basename(path)}")
            return df
        except (UnicodeDecodeError, Exception):
            # 이 인코딩으로 안 되면 다음 방식 시도
            continue

    # 4가지 모두 실패
    raise ValueError(
        f"CSV 인코딩 자동감지 실패: {path}\n"
        f"직접 인코딩을 지정하거나 파일을 UTF-8로 변환해주세요."
    )


# ─────────────────────────────────────────────────────────────────────────────
# 🔑 파일 MD5 해시 계산
# 초등학생 설명: 파일에 고유 번호를 붙여서 같은 파일인지 확인해요!
# ─────────────────────────────────────────────────────────────────────────────

def file_hash(path: str) -> str:
    """
    파일의 MD5 해시값 계산

    초등학생 설명:
        모든 파일에 고유한 지문(해시)을 만들어요.
        같은 파일이면 항상 같은 지문이 나와요!
        파일이 바뀌었는지 확인할 때 쓰여요.

    Args:
        path : 해시를 계산할 파일 경로

    Returns:
        32자리 16진수 문자열 (예: "5d41402abc4b2a76b9719d911017c592")

    사용 예시:
        h1 = file_hash("data/old.csv")
        h2 = file_hash("data/new.csv")
        if h1 == h2:
            print("같은 파일이에요!")
    """
    h = hashlib.md5()
    with open(path, "rb") as f:
        # 8KB씩 읽어서 처리 (큰 파일도 메모리 절약)
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()


# ─────────────────────────────────────────────────────────────────────────────
# 📦 중첩 딕셔너리 평탄화
# 초등학생 설명: 서랍 안의 서랍에 있는 걸 꺼내서 한 줄로 늘어놓아요!
# ─────────────────────────────────────────────────────────────────────────────

def flatten_dict(d: dict, parent: str = "", sep: str = ".") -> dict:
    """
    중첩 딕셔너리를 1단계 평탄화

    초등학생 설명:
        {"a": {"b": 1}} → {"a.b": 1}
        처럼 안쪽에 있는 것들을 꺼내서 납작하게 만들어요!

    Args:
        d      : 평탄화할 딕셔너리
        parent : 부모 키 (재귀 호출용, 직접 설정 불필요)
        sep    : 키 구분자 (기본값: ".")

    Returns:
        평탄화된 딕셔너리

    사용 예시:
        flatten_dict({"a": {"b": 1, "c": 2}, "d": 3})
        # 결과: {"a.b": 1, "a.c": 2, "d": 3}
    """
    items = []
    for k, v in d.items():
        # 부모 키가 있으면 "부모.자식" 형태로 연결
        new_key = f"{parent}{sep}{k}" if parent else k
        if isinstance(v, dict):
            # 중첩 딕셔너리면 재귀 호출
            items.extend(flatten_dict(v, new_key, sep).items())
        else:
            items.append((new_key, v))
    return dict(items)


# ─────────────────────────────────────────────────────────────────────────────
# 📊 엑셀(xlsx/xls) 파일 읽기 (🆕 7.16.4)
# 초등학생 설명: 엑셀 파일도 CSV처럼 읽을 수 있어요!
# ─────────────────────────────────────────────────────────────────────────────

def read_excel_safe(path: str, sheet_name=0):
    """
    엑셀 파일 안전하게 읽기 (xlsx/xls 모두 지원)
    초등학생 설명: 엑셀 파일을 열어서 데이터를 꺼내요.

    지원 엔진:
        .xlsx → openpyxl (최신 엑셀)
        .xls  → xlrd 또는 openpyxl (구형 엑셀)
    """
    import pandas as pd
    ext = os.path.splitext(path)[1].lower()

    # 엔진 순서대로 시도
    engines = []
    if ext == '.xls':
        engines = ['xlrd', 'openpyxl']   # 구형은 xlrd 먼저
    else:
        engines = ['openpyxl', 'xlrd']   # 신형은 openpyxl 먼저

    last_err = None
    for engine in engines:
        try:
            df = pd.read_excel(path, sheet_name=sheet_name, engine=engine)
            logger.info(f"📊 엑셀 읽기 성공 [{engine}]: {os.path.basename(path)}")
            return df
        except ImportError:
            continue   # 라이브러리 없으면 다음 엔진 시도
        except Exception as e:
            last_err = e
            continue

    # 모든 엔진 실패 시 CSV로 시도 (마지막 수단)
    try:
        df = pd.read_csv(path, encoding='utf-8-sig')
        logger.warning(f"⚠️ 엑셀 읽기 실패 → CSV로 대체 읽기 성공")
        return df
    except Exception:
        raise ValueError(
            f"엑셀 파일 읽기 실패: {last_err} / 해결: pip3 install openpyxl"
        )


def get_excel_sheets(path: str) -> list:
    """
    엑셀 파일의 시트 목록 반환
    초등학생 설명: 엑셀 파일에 탭이 몇 개 있는지 알려줘요!
    """
    import pandas as pd
    ext = os.path.splitext(path)[1].lower()
    engines = ['openpyxl', 'xlrd'] if ext != '.xls' else ['xlrd', 'openpyxl']

    for engine in engines:
        try:
            xl = pd.ExcelFile(path, engine=engine)
            return xl.sheet_names
        except (ImportError, Exception):
            continue
    logger.warning(f"⚠️ 시트 목록 조회 실패")
    return []


def read_file_auto(path: str, sheet_name=0):
    """
    파일 확장자 보고 CSV/엑셀 자동 선택해서 읽기
    초등학생 설명: 파일 종류를 보고 알맞은 방법으로 자동으로 열어요!

    지원 형식:
        .csv          → CSV 읽기 (인코딩 자동감지)
        .xlsx / .xls  → 엑셀 읽기
        .tsv          → 탭 구분 CSV

    Returns:
        pandas DataFrame
    """
    import pandas as pd
    ext = os.path.splitext(path)[1].lower()

    if ext in ['.xlsx', '.xls']:
        return read_excel_safe(path, sheet_name)
    elif ext == '.tsv':
        for enc in ["utf-8", "utf-8-sig", "cp949", "euc-kr"]:
            try:
                df = pd.read_csv(path, sep='\t', encoding=enc)
                logger.info(f"📄 TSV 읽기 성공 [{enc}]: {os.path.basename(path)}")
                return df
            except Exception:
                continue
        raise ValueError(f"TSV 읽기 실패: {path}")
    else:
        return read_csv_safe(path)

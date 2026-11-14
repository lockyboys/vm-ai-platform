"""어려운 자가 수정 시험(오류 100개) 채점 공용 모듈 (2026-11-11, LuckyBoys 요청).

- 채점 식(CASES)은 _build/<program>_cases_src.py, 기대값·오류 지도는 build_hard.py가 만든
  _build/<program>_expected.json · _build/<program>_bugmap.json 에서 읽는다.
- 식은 eval로 실행하며 전역 이름은 m(채점 대상 모듈), attempt(예외를 값으로 바꿈),
  B(대상 모듈과 무관한 보드 생성기) 세 개만 준다. 식 하나당 1초 제한(무한 반복 오류 대비).
- 대상 모듈 import는 프로세스마다 한 번(상태 누적 오류를 실제 사용 순서대로 드러내기 위해).
"""
import ast
import importlib
import json
import math
import signal
from pathlib import Path

BUILD_DIR = Path(__file__).resolve().parent / "_build"
PROGRAMS = ("calc_engine", "tetris_engine")
CASE_TIMEOUT_SECONDS = 1


class CaseTimeout(Exception):
    """식 하나가 제한 시간을 넘김."""


def _on_alarm(*_):
    raise CaseTimeout()


def attempt(fn):
    """함수를 실행해 값 또는 ('raises', 예외 이름)을 돌려준다(오류 뒤 상태 검사용)."""
    try:
        return fn()
    except Exception as exc:  # noqa: BLE001 - 예외 종류 자체를 기록하는 것이 목적
        return ("raises", type(exc).__name__)


def B(text):
    """테스트용 보드: 'xx..|.x..' 처럼 '|'로 행 구분, 'x'=블록(1), 그 밖=빈칸(0)."""
    return [[1 if ch == "x" else 0 for ch in row] for row in text.split("|")]


def cases(program):
    """채점 식 목록."""
    module = importlib.import_module(f"FastAPI.LangGraph.selffix_demo.hard._build.{program}_cases_src")
    return module.CASES


def expected(program):
    """식별 기대값 [('ok', 값) | ('raises', 예외 이름)]. 값은 repr로 저장돼 있어 literal_eval로 되살린다."""
    raw = json.loads((BUILD_DIR / f"{program}_expected.json").read_text(encoding="utf-8"))
    return [(kind, value if kind == "raises" else ast.literal_eval(value)) for kind, value in raw]


def bugmap(program):
    """오류 100개 목록(번호·분야·함수·설명·채점 식 번호)."""
    return json.loads((BUILD_DIR / f"{program}_bugmap.json").read_text(encoding="utf-8"))


def run_case(module, expr):
    """식 하나를 실행해 ('ok', 값) 또는 ('raises', 예외 이름)."""
    previous = signal.signal(signal.SIGALRM, _on_alarm)
    signal.alarm(CASE_TIMEOUT_SECONDS)
    try:
        return ("ok", eval(expr, {"m": module, "attempt": attempt, "B": B}))  # noqa: S307 - 고정된 채점 식만 실행
    except CaseTimeout:
        return ("raises", "Timeout")
    except Exception as exc:  # noqa: BLE001
        return ("raises", type(exc).__name__)
    finally:
        signal.alarm(0)
        signal.signal(signal.SIGALRM, previous)


def close(a, b):
    """기대값 비교: bool은 동일성, 실수는 상대오차 1e-9, 목록·튜플은 타입까지 재귀 비교."""
    if isinstance(a, bool) or isinstance(b, bool):
        return a is b
    if isinstance(a, (int, float)) and isinstance(b, (int, float)):
        return math.isclose(a, b, rel_tol=1e-9, abs_tol=1e-12)
    if isinstance(a, (list, tuple)) and isinstance(b, (list, tuple)):
        return type(a) is type(b) and len(a) == len(b) and all(close(x, y) for x, y in zip(a, b))
    return a == b


def matches(got, want):
    """실행 결과가 기대값과 같은지."""
    return got[0] == want[0] and close(got[1], want[1])

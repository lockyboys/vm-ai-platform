"""오류 20개 시험 2회차 채점: combo20/calc_engine_gemini_run2.py (2026-11-14, LuckyBoys 요청).

- 앱 수정(검사 거부 시 재시도, 라운드별 temperature 0.4→0.2→0.0, 최대 3라운드) 후 처음부터 다시 고치는 시험.
- review_python_source(provider="gemini", auto_apply=True)의 test_paths로 쓴다(improve 규칙).
- 파일 이름이 test_로 시작하지 않아 전체 회귀에는 섞이지 않는다. 채점 식·기대값은 1회차와 같다.
"""
import importlib

import pytest

from FastAPI.LangGraph.selffix_demo.hard import bench_support as bs

PROGRAM = "calc_engine"
TARGET = "FastAPI.LangGraph.selffix_demo.hard.combo20.calc_engine_gemini_run2"
CASES = bs.cases(PROGRAM)
EXPECTED = bs.expected(PROGRAM)


@pytest.fixture(scope="module")
def target():
    """채점 대상 모듈을 한 번만 import한다(상태 누적 오류를 순서대로 드러내기 위해)."""
    return importlib.import_module(TARGET)


@pytest.mark.parametrize("index", range(len(CASES)), ids=[f"c{i:03d}" for i in range(len(CASES))])
def test_case(target, index):
    """식 하나의 실행 결과가 정답 구현의 결과와 같아야 한다."""
    got = bs.run_case(target, CASES[index])
    assert bs.matches(got, EXPECTED[index]), f"{CASES[index]} -> {got!r}, 기대 {EXPECTED[index]!r}"

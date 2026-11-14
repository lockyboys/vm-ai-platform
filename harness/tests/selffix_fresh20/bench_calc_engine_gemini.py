"""새 오류 20개(새 얽힌 10 + 처음 쓰는 한 줄 10) 시험 채점: fresh20/calc_engine_gemini.py (2026-11-14, LuckyBoys 요청).

- review_python_source(provider="gemini", auto_apply=True)의 test_paths로 쓴다(improve 규칙).
- 파일 이름이 test_로 시작하지 않아 전체 회귀에는 섞이지 않는다.
- 채점 식·기대값은 기존 오류 100개 시험과 같다. 오류 목록: hard/fresh20/calc_engine_bugmap.json
"""
import importlib

import pytest

from FastAPI.LangGraph.selffix_demo.hard import bench_support as bs

PROGRAM = "calc_engine"
TARGET = "FastAPI.LangGraph.selffix_demo.hard.fresh20.calc_engine_gemini"
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

"""어려운 자가 수정 시험 채점: calc_engine_gemini.py (2026-11-11, LuckyBoys 요청).

- review_python_source(provider="gemini", auto_apply=True)의 test_paths로 쓴다.
  이 파일이 모두 통과해야 AI 수정안이 원본에 남고, 하나라도 실패하면 자동으로 되돌린다.
- 파일 이름이 test_로 시작하지 않아 전체 회귀(pytest harness/tests)에는 섞이지 않는다.
- 채점 식·기대값은 FastAPI/LangGraph/selffix_demo/hard/_build/ 에 있다(build_hard.py가 생성).
"""
import importlib

import pytest

from FastAPI.LangGraph.selffix_demo.hard import bench_support as bs

PROGRAM = "calc_engine"
TARGET = "FastAPI.LangGraph.selffix_demo.hard.calc_engine_gemini"
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

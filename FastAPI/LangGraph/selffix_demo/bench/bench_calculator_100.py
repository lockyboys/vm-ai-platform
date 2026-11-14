"""계산기 자가 수정 채점용 테스트 100건 (2026-11-10, LuckyBoys 요청: AI 4종 비교).

목적
- review_python_source가 AI(Gemini·ChatGPT·Claude·Ollama)로 만든 제안 소스(proposed.py)를
  같은 100건으로 채점해 "무엇을 고쳤고 무엇을 못 고쳤는지"를 건별로 본다.
- 기준은 원본 calculator.py의 docstring(명세)이다. 원본에 일부러 넣은 결함
  (subtract가 a+b, divide(0)이 ZeroDivisionError)은 여기서 실패로 드러나야 한다.

구성(합계 100)
- add 15 / subtract 15 / multiply 15 / divide 15(정상 12 + 0 나누기 ValueError 3)
- calculate 정상 식 20 / calculate 잘못된 입력 ValueError 20

주의
- 파일 이름이 test_로 시작하지 않아 전체 회귀(pytest harness/tests)에 섞이지 않는다.
  채점 스크립트가 파일 경로를 직접 넘겨 실행한다.
- 실수 비교는 pytest.approx로 한다(0.1+0.2 같은 부동소수 오차 때문).
"""
import pytest

from FastAPI.LangGraph.selffix_demo import calculator as calc

# (a, b, 기대값) — 덧셈 15건: 0, 음수, 소수, 큰 수, 작은 수 포함
ADD_CASES = [
    (2, 3, 5), (0, 0, 0), (-1, 1, 0), (-2, -3, -5), (1.5, 2.5, 4),
    (0.1, 0.2, 0.3), (1e10, 1, 1e10 + 1), (100, -50, 50), (-0.5, 0.5, 0), (7, 0, 7),
    (0, 7, 7), (123, 456, 579), (-100, -100, -200), (2.25, 0.75, 3), (1e-3, 1e-3, 2e-3),
]
# 뺄셈 15건: 원본 결함(a+b)이면 b가 0이 아닌 경우 대부분 실패해야 한다
SUBTRACT_CASES = [
    (5, 3, 2), (3, 5, -2), (0, 0, 0), (-1, -1, 0), (10, -5, 15),
    (-5, 10, -15), (2.5, 0.5, 2), (0.3, 0.1, 0.2), (100, 1, 99), (1e6, 1, 999999),
    (0, 7, -7), (7, 0, 7), (-2.5, -2.5, 0), (1, 1e-9, 1 - 1e-9), (50, 50, 0),
]
# 곱셈 15건
MULTIPLY_CASES = [
    (4, 2.5, 10), (0, 5, 0), (5, 0, 0), (-2, 3, -6), (-2, -3, 6),
    (1.5, 1.5, 2.25), (1e5, 1e5, 1e10), (7, 1, 7), (1, 7, 7), (-1, -1, 1),
    (0.1, 10, 1), (3, -0.5, -1.5), (12, 12, 144), (2, 0.25, 0.5), (-4, 0, 0),
]
# 나눗셈 정상 12건
DIVIDE_CASES = [
    (9, 3, 3), (1, 2, 0.5), (-9, 3, -3), (9, -3, -3), (-9, -3, 3), (0, 5, 0),
    (7, 2, 3.5), (1, 3, 1 / 3), (2.5, 0.5, 5), (1e6, 1e3, 1e3), (5, 0.1, 50), (-1, 4, -0.25),
]
# 0으로 나누기 3건: 명세상 ValueError (원본 결함은 ZeroDivisionError → 실패해야 함)
DIVIDE_ZERO_CASES = [(1, 0), (0, 0), (-5, 0.0)]
# calculate 정상 식 20건: (식, 기대값). split()이라 공백·탭 여러 개도 허용된다
CALC_OK_CASES = [
    ("3 + 4", 7), ("7 - 2", 5), ("10 - 20", -10), ("1.5 * 4", 6), ("9 / 3", 3),
    ("-3 + -4", -7), ("0 * 99", 0), ("2.5 + 2.5", 5), ("100 / 8", 12.5), ("1e3 + 1", 1001),
    ("  3   +   4  ", 7), ("-1 - -1", 0), ("0 - 5", -5), ("6 * -2", -12), ("7 / 2", 3.5),
    ("0.1 + 0.2", 0.3), ("5 - 5", 0), ("1000000 * 1000000", 1e12), ("-8 / 2", -4), ("3\t+\t4", 7),
]
# calculate 잘못된 입력 20건: 형식 오류·모르는 연산자·숫자 아님·0 나누기 → 모두 ValueError
CALC_BAD_CASES = [
    "", "1 +", "1 % 2", "a + 1", "1 + b", "1 ++ 2", "1 + 2 + 3", "+", "1 2", "1 x 2",
    "1 ^ 2", "1 // 2", "abc", "1 / 0", "5 / 0.0", "   ", "1+2", "one + two", "1 + 2 3", "1 ** 2",
]


@pytest.mark.parametrize("a,b,expected", ADD_CASES)
def test_add(a, b, expected):
    """add(a, b) == a + b."""
    assert calc.add(a, b) == pytest.approx(expected)


@pytest.mark.parametrize("a,b,expected", SUBTRACT_CASES)
def test_subtract(a, b, expected):
    """subtract(a, b) == a - b (원본 결함 검출용)."""
    assert calc.subtract(a, b) == pytest.approx(expected)


@pytest.mark.parametrize("a,b,expected", MULTIPLY_CASES)
def test_multiply(a, b, expected):
    """multiply(a, b) == a * b."""
    assert calc.multiply(a, b) == pytest.approx(expected)


@pytest.mark.parametrize("a,b,expected", DIVIDE_CASES)
def test_divide(a, b, expected):
    """divide(a, b) == a / b (b != 0)."""
    assert calc.divide(a, b) == pytest.approx(expected)


@pytest.mark.parametrize("a,b", DIVIDE_ZERO_CASES)
def test_divide_by_zero_value_error(a, b):
    """명세: 0으로 나누면 ValueError (ZeroDivisionError는 ValueError의 하위가 아니므로 실패)."""
    with pytest.raises(ValueError):
        calc.divide(a, b)


@pytest.mark.parametrize("expression,expected", CALC_OK_CASES)
def test_calculate_ok(expression, expected):
    """'숫자 연산자 숫자' 식을 계산한다."""
    assert calc.calculate(expression) == pytest.approx(expected)


@pytest.mark.parametrize("expression", CALC_BAD_CASES)
def test_calculate_bad_value_error(expression):
    """잘못된 입력은 모두 ValueError여야 한다(다른 예외·정상 반환이면 실패)."""
    with pytest.raises(ValueError):
        calc.calculate(expression)

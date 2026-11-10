"""시연용 계산기 테스트 — 자동 수정 후 이 테스트가 통과해야 수정이 유지된다 (2026-11-10)."""
import pytest

from FastAPI.LangGraph.selffix_demo import calculator as calc


def test_basic_operations():
    assert calc.add(2, 3) == 5
    assert calc.subtract(5, 3) == 2
    assert calc.multiply(4, 2.5) == 10
    assert calc.divide(9, 3) == 3


def test_calculate_expression():
    assert calc.calculate("7 - 2") == 5
    assert calc.calculate("1.5 * 4") == 6


@pytest.mark.parametrize("bad", ["", "1 +", "1 % 2", "a + 1"])
def test_bad_expression_rejected(bad):
    """잘못된 입력: 형식 오류, 모르는 연산자, 숫자가 아닌 값."""
    with pytest.raises(ValueError):
        calc.calculate(bad)


def test_divide_by_zero_is_value_error():
    with pytest.raises(ValueError):
        calc.divide(1, 0)

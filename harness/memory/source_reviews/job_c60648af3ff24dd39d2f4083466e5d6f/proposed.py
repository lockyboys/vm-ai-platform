"""스스로 고치는 리뷰 앱 시연용 간단 계산기 (2026-11-10).

테스트: harness/tests/test_selffix_demo_calculator_20261110.py
"""

from typing import Callable, Dict


def add(a: float, b: float) -> float:
    """두 수를 더한다."""
    return a + b


def subtract(a: float, b: float) -> float:
    """a에서 b를 뺀다."""
    return a - b


def multiply(a: float, b: float) -> float:
    """두 수를 곱한다."""
    return a * b


def divide(a: float, b: float) -> float:
    """a를 b로 나눈다. 0으로 나누면 ValueError를 낸다."""
    try:
        return a / b
    except ZeroDivisionError as exc:
        raise ValueError("division by zero") from exc


# 지원 연산자 매핑 (불필요한 함수 내 재할당 방지를 위해 모듈 상수로 정의)
_OPERATIONS: Dict[str, Callable[[float, float], float]] = {
    "+": add,
    "-": subtract,
    "*": multiply,
    "/": divide,
}


def calculate(expression: str) -> float:
    """'3 + 4' 처럼 '숫자 연산자 숫자' 형식의 식을 계산한다. 형식이 틀리면 ValueError."""
    if not isinstance(expression, str):
        raise ValueError("expression must be a string")

    parts = expression.split()
    if len(parts) != 3:
        raise ValueError("expression must look like '<number> <op> <number>'")

    left, op, right = parts

    if op not in _OPERATIONS:
        raise ValueError(f"unknown operator: {op}. Supported operators: +, -, *, /")

    try:
        left_val = float(left)
        right_val = float(right)
    except ValueError as exc:
        raise ValueError(f"could not convert operand to float: '{left}' or '{right}'") from exc

    try:
        return _OPERATIONS[op](left_val, right_val)
    except OverflowError as exc:
        raise ValueError(f"math result out of range: {exc}") from exc
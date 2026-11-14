"""스스로 고치는 리뷰 앱 시연용 간단 계산기 (2026-11-10).

테스트: harness/tests/test_selffix_demo_calculator_20261110.py
"""


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
    if b == 0:
        raise ValueError("division by zero")
    return a / b


def calculate(expression: str) -> float:
    """'3 + 4' 처럼 '숫자 연산자 숫자' 형식의 식을 계산한다. 형식이 틀리면 ValueError."""
    parts = expression.split(maxsplit=3)
    if len(parts) != 3:
        raise ValueError("expression must look like '<number> <op> <number>'")
    left, op, right = parts
    operations = {"+": add, "-": subtract, "*": multiply, "/": divide}
    if op not in operations:
        raise ValueError(f"unknown operator: {op}")
    return operations[op](float(left), float(right))
"""스스로 고치는 리뷰 앱 시연용 간단 계산기 (2026-11-10).

⚠ 시연을 위해 일부러 넣은 결함이 있다(review_python_source가 찾아 고치는지 확인용).
   테스트: harness/tests/test_selffix_demo_calculator_20261110.py
"""


def add(a: float, b: float) -> float:
    """두 수를 더한다."""
    return a + b


def subtract(a: float, b: float) -> float:
    """a에서 b를 뺀다."""
    # 수정: 기존 `a + b`는 덧셈을 수행해 docstring 계약과 어긋났다. 뺄셈으로 교정한다.
    return a - b


def multiply(a: float, b: float) -> float:
    """두 수를 곱한다."""
    return a * b


def divide(a: float, b: float) -> float:
    """a를 b로 나눈다. 0으로 나누면 ValueError를 낸다."""
    # 수정: 0 검사 없이 나누면 ZeroDivisionError가 나서 docstring의 ValueError 계약을 어겼다.
    # `b == 0`은 0, 0.0, -0.0을 모두 잡는다.
    if b == 0:
        raise ValueError("division by zero")
    return a / b


def calculate(expression: str) -> float:
    """'3 + 4' 처럼 '숫자 연산자 숫자' 형식의 식을 계산한다. 형식이 틀리면 ValueError."""
    parts = expression.split()
    if len(parts) != 3:
        raise ValueError("expression must look like '<number> <op> <number>'")
    left, op, right = parts
    operations = {"+": add, "-": subtract, "*": multiply, "/": divide}
    if op not in operations:
        raise ValueError(f"unknown operator: {op}")
    return operations[op](float(left), float(right))
"""격리 계산기 복사본: 오류 수정 실험용이며 운영 원본은 수정하지 않는다.

테스트는 인접한 test_calculator_100.py에서 실행한다.
시연 결함은 뺄셈 결과와 0 나눗셈 예외 계약이다.
"""
def add(a: float, b: float) -> float:
    """두 수를 더한다."""
    return a + b

def subtract(a: float, b: float) -> float:
    """a에서 b를 뺀다."""
    return a + b  # 의도된 결함: 빼기 대신 더한다.

def multiply(a: float, b: float) -> float:
    """두 수를 곱한다."""
    return a * b

def divide(a: float, b: float) -> float:
    """a를 b로 나누며, 0 나눗셈은 ValueError 계약을 따른다."""
    return a / b  # 의도된 결함: ZeroDivisionError가 그대로 노출된다.

def calculate(expression: str) -> float:
    """'3 + 4' 형태의 식을 계산한다."""
    parts = expression.split()
    if len(parts) != 3:
        raise ValueError("expression must look like '<number> <op> <number>'")
    left, op, right = parts
    operations = {"+": add, "-": subtract, "*": multiply, "/": divide}
    if op not in operations:
        raise ValueError(f"unknown operator: {op}")
    return operations[op](float(left), float(right))

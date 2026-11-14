"""스스로 고치는 리뷰 앱 시연용 간단 계산기 (2026-11-10).

⚠ 시연을 위해 일부러 넣은 결함이 수정되었습니다.
   테스트: harness/tests/test_selffix_demo_calculator_20261110.py

[수정 사항 요약]
1. subtract 함수: 논리적 결함 수정 (a + b -> a - b).
2. divide 함수: 예외 처리 계약 준수 (ZeroDivisionError -> ValueError).
3. calculate 함수: 입력값 변환 시 try-except를 적용하여 견고성(Robustness)을 확보했습니다.
"""


def add(a: float, b: float) -> float:
    """두 수를 더한다."""
    return a + b


def subtract(a: float, b: float) -> float:
    """a에서 b를 뺀다."""
    # 수정 근거: 기존의 a + b 결함을 a - b로 수정하여 기능적 정확성을 확보했습니다.
    return a - b


def multiply(a: float, b: float) -> float:
    """두 수를 곱한다."""
    return a * b


def divide(a: float, b: float) -> float:
    """a를 b로 나눈다. 0으로 나누면 ValueError를 낸다."""
    # 수정 근거: 문서화된 계약(ValueError)을 준수하기 위해 0 나누기 전 명시적으로 검사합니다.
    if b == 0.0:
        raise ValueError("Cannot divide by zero.")
    return a / b


def calculate(expression: str) -> float:
    """'3 + 4' 처럼 '숫자 연산자 숫자' 형식의 식을 계산한다. 형식이 틀리면 ValueError."""
    parts = expression.split()
    if len(parts) != 3:
        raise ValueError("expression must look like '<number> <op> <number>'")
    left_str, op, right_str = parts
    operations = {"+": add, "-": subtract, "*": multiply, "/": divide}
    if op not in operations:
        raise ValueError(f"unknown operator: {op}")
    
    try:
        # 수정 근거: float() 변환 과정에서 숫자가 아닌 값이 들어올 경우 발생하는 ValueError를 명시적으로 처리합니다.
        left_val = float(left_str)
        right_val = float(right_str)
    except ValueError:
        # 숫자가 아닌 문자열이 입력되었을 때 발생합니다.
        raise ValueError("Input numbers must be valid floating-point numbers.")
        
    return operations[op](left_val, right_val)
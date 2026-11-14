## 1. 전문가적 견해 및 종합 평가

초안의 **PARTNER 수정본은 확인된 산술·예외 결함을 해결**합니다. 반면 PROMPT_ENGINEER와 REVIEWER 초안은 전체 수정 소스를 제공하지 않아 요청을 충족하지 못합니다. REVIEWER가 두 결함을 P0로 분류한 근거도 제공되지 않았습니다.

검토는 입력으로 제공된 소스와 초안에 한정했습니다. 실제 파일과 테스트는 확인하거나 실행하지 못했습니다. 경로에 LangGraph라는 이름이 있지만, 제공된 소스에 LangChain/LangGraph 사용은 보이지 않아 PROMPT_ENGINEER 설계 검토 대상은 아닙니다.

## 2. 위험도 및 진단 리포트

**수정 필요**

- **정확성 — `subtract`:** `a + b`를 반환하므로 `calculate("3 - 4")`도 잘못 계산합니다. `a - b`로 수정했습니다.
- **예외 계약 — `divide`:** `0.0` 또는 `-0.0`으로 나누면 문서의 `ValueError` 대신 `ZeroDivisionError`가 발생합니다. 이를 `ValueError`로 변환하도록 수정했습니다.
- **메모리 완화 — `calculate`:** 기존 `split()`은 잘못된 입력의 모든 토큰을 리스트에 만듭니다. 최대 세 번만 분할하도록 바꿔 리스트 원소 수를 제한했습니다. 다만 입력 문자열과 분할 결과의 크기는 여전히 입력 길이에 비례하므로, 신뢰할 수 없는 입력을 받는 환경에서는 호출 경계의 크기 제한을 별도로 검토해야 합니다.

**수정 불필요 또는 미확인**

- 동시성·리소스: 제공된 코드에는 공유 가변 상태나 직접 해제할 외부 리소스가 없습니다.
- 테스트: 뺄셈, 양·음의 0 제수 및 긴 입력에 대한 회귀 테스트 실행 결과는 **미확인**입니다. 실제 호출 경로의 입력 크기 제한도 확인하지 못했습니다.

## 3. 최종 수정 전체 소스 코드

```python
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
    try:
        return a / b
    except ZeroDivisionError as exc:
        raise ValueError("division by zero") from exc


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
```
## 1. 전문가적 견해 및 종합 평가

초안이 지적한 뺄셈 오류와 0 나누기 예외 계약 위반은 제공된 소스에서 확인됩니다. 초안의 일부는 전체 코드를 제공하지 않았으며, P0 평가는 실제 운영 영향이 확인되지 않아 근거가 부족합니다.

아래는 두 결함을 수정하고, `calculate`의 불필요한 토큰 할당을 줄인 제안 코드입니다. **실제 파일 확인·수정과 테스트 실행은 하지 않았습니다.**

제공된 소스에는 LangChain/LangGraph 사용이 없어 이 파일에 대한 PROMPT_ENGINEER 설계 검토는 적용되지 않습니다. 프로젝트 전체의 사용 여부는 미확인입니다.

## 2. 위험도 및 진단 리포트

| 분류 | 근거 및 조치 |
|---|---|
| 정확성 — 수정 | `subtract`가 `a + b`를 반환합니다. `a - b`로 변경합니다. 예를 들어 `subtract(3, 1)`은 기존에 4를 반환합니다. |
| 예외 계약 — 수정 | `divide`는 분모가 0이면 문서의 `ValueError` 대신 `ZeroDivisionError`를 냅니다. 0을 검사해 `ValueError`를 발생시킵니다. 음의 0도 포함됩니다. |
| 메모리 — 완화 | `calculate`의 `split()`은 토큰이 많은 입력에서 토큰별 문자열과 리스트를 생성합니다. `maxsplit=3`으로 제한해 네 부분까지만 생성하면서, 네 토큰 이상인 식은 기존처럼 거부합니다. 입력 길이 자체는 제한하지 않으므로 대형 입력에 따른 메모리 위험은 남습니다. 호출 환경의 크기 제한은 미확인입니다. |
| 동시성 — 수정 불필요 | 제공된 코드에는 공유 가변 상태가 없습니다. |
| 리소스 해제 — 수정 불필요 | 제공된 코드에는 파일이나 네트워크 연결 등 명시적으로 해제할 리소스가 없습니다. |
| 기타 예외 — 수정 불필요 | 잘못된 형식·연산자·숫자는 기존 코드에서 `ValueError`를 발생시킵니다. `float`가 허용하는 `inf`와 `nan`도 기존처럼 허용합니다. |

직접 호출과 `calculate` 경유 호출에서 뺄셈, 양수·음수 0 나누기, 정상 나눗셈 및 잘못된 형식을 회귀 테스트해야 합니다. 결과는 미확인입니다.

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
```
### 검증관 초안 검증 리포트

- **검증 근거**:
  - `subtract`: 초안에서 지적한 대로 뺄셈 함수에서 `a + b`를 수행하는 명백한 구현 결함(P0)이 확인되었으며, `a - b`로 수정이 필수적입니다.
  - `divide`: 독스트링에 "0으로 나누면 ValueError를 낸다"고 명시되어 있으나 실제로는 Python 기본 예외인 `ZeroDivisionError`가 발생하므로 계약(Contract) 위반(P1)입니다. `b == 0` 분기 검사를 통한 `ValueError` 명시적 발생 수정은 타당합니다.
  - `calculate`: `float(left)` 및 `float(right)`는 잘못된 문자열 입력 시 내장 `ValueError`를 발생시키므로 최소 수정 원칙 및 기존 계약을 충분히 만족합니다.
  - 리소스/동시성/메모리: 상태를 갖지 않는 순수 함수군으로 외부 I/O나 잠금(Lock)이 없어 메모리 누수 및 동시성 충돌 위험이 없습니다.
- **초안 결함 및 보완**:
  - 초안에 동일한 섹션(`## 1`, `## 2`, `## 3`)이 중복 생성되어 구조적 혼선이 발생했습니다. 단일한 3개 섹션 구조로 정리합니다.
  - LangGraph 에이전트 연동 관점의 프롬프트 및 도구 설계 검토(PROMPT_ENGINEER)를 1번 섹션에 명확히 통합 반영합니다.
- **미확인 사항**:
  - `harness/tests/test_selffix_demo_calculator_20261110.py`의 구체적인 에러 메시지 검증 규칙(정확한 문자열 매칭 여부)은 외부 파일이 제공되지 않아 직접 확인 불가합니다. (표준적인 `ValueError` 발생 규약 준수로 충족)

---

## 1. 전문가적 견해 및 종합 평가

본 모듈은 LangGraph 기반의 자가 수정(Self-fix) 워크플로 데모에서 도구(Tool)로 활용되는 연산 유틸리티입니다.

- **PROMPT_ENGINEER 설계 검토**:
  LangGraph의 ReAct 루프 및 LLM Tool Calling 환경에서 도구의 docstring과 에러 타입은 에이전트의 의사결정에 직접적인 영향을 미칩니다. `divide` 함수가 명세와 다르게 `ZeroDivisionError`를 전파할 경우, ReAct 노드의 예외 분기 정책(`except ValueError:`)과 불일치하여 에이전트가 실패 원인을 파악하지 못하고 무한 루프나 조기 중단을 초래할 수 있습니다. 또한 `subtract`의 연산 기호 오류는 잘못된 계산 결과를 LLM의 관찰(Observation) 값으로 전달하여 환각(Hallucination) 및 잘못된 후속 행동을 유발합니다. 따라서 본 결함 수정은 LLM 도구 인터페이스의 안정성을 확보하는 필수 작업입니다.
- **자원·동시성·예외 관리 종합**:
  모듈 내 모든 함수는 전역 상태를 공유하지 않는 순수 함수(Pure function)로 구현되어 있어 멀티스레드 환경에서도 스레드 안전성(Thread-safety)이 보장되며 가비지 컬렉션(GC) 대상 메모리 누수가 발생하지 않습니다. 파일, 소켓 등의 외부 리소스를 다루지 않으므로 리소스 해제 로직은 요구되지 않으며, 계약 위반에 해당하는 예외 처리만 최소한으로 보정합니다.

---

## 2. 위험도 및 진단 리포트

1. **`subtract` 연산자 오류 [위험도: High / P0]**
   - **진단**: `a + b`로 잘못 작성되어 뺄셈 연산의 논리적 정합성을 깨뜨리고 도구 호출 시 오답을 반환합니다.
   - **수정 계획**: `a - b`로 연산자 수정.
   - **근거**: 사칙연산 명세 및 기본 산술 정의 복구.

2. **`divide` 0 나눗셈 예외 규약 불일치 [위험도: High / P1]**
   - **진단**: 독스트링 규약상 "0으로 나누면 ValueError를 낸다"로 정의되어 있으나 가드 로직 부재로 내장 `ZeroDivisionError`가 전파됩니다.
   - **수정 계획**: `if b == 0:` 조건을 검사하여 `raise ValueError("Cannot divide by zero")` 실행.
   - **근거**: 호출자(테스트 러너 및 LangGraph 툴 노드)와의 예외 타입 계약 준수.

3. **`add`, `multiply`, `calculate` [위험도: None / 수정 불필요]**
   - **진단**: `add` 및 `multiply`는 사칙연산 명세를 올바르게 수행합니다. `calculate`는 공백 분리 실패 시 `ValueError`, 미지원 연산자 시 `ValueError`, 비숫자 피연산자 변환 시 `float()`에 의해 자연스럽게 `ValueError`가 전파되므로 함수 수정이 불필요합니다.

---

## 3. 최종 수정 전체 소스 코드

```python
"""스스로 고치는 리뷰 앱 시연용 간단 계산기 (2026-11-10).

⚠ 시연을 위해 일부러 넣은 결함이 있다(review_python_source가 찾아 고치는지 확인용).
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
        raise ValueError("Cannot divide by zero")
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
```
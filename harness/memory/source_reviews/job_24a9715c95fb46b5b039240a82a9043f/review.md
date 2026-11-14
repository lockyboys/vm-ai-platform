## 1. 전문가적 견해 및 종합 평가

**결론: 수정이 필요한 실제 결함은 2건(`subtract`, `divide`)입니다.** 아래 수정본으로 두 함수의 실행 코드를 고쳤습니다. 테스트를 실행하지 않았으므로 상태는 **검증 대기**입니다.

**초안 검증 결과**

| 초안 주장 | 판정 | 근거 |
|---|---|---|
| `subtract(5, 3)`이 `8`을 반환하고, `calculate("5 - 3")`은 `8.0`을 반환 | 확인 | 원본 15행이 `return a + b`이고, `calculate`는 `float`으로 변환해 전달함 |
| `divide(1, 0)`이 `ZeroDivisionError`를 냄 | 확인 | 원본 25행에 0 검사 없이 `a / b`를 실행함. Python 표준 동작이며 `0.0`도 같음 |
| `b == 0`이 `0`, `0.0`, `-0.0`을 모두 잡음 | 확인 | Python에서 `-0.0 == 0`은 `True`. `calculate("1 / -0.0")`도 `float("-0.0")` 변환 후 가드에 걸림 |
| `float("abc")`가 `ValueError`를 내서 `calculate` 계약과 일치 | 확인 | 표준 동작 |
| `"nan"`, `"inf"`, `"1e999"` 입력을 수용함 | 확인 | `float()`가 이 값들을 허용함. 명세에 금지 조항이 없어 결함으로 확정할 수 없음 |
| 메모리·동시성·리소스 결함 없음 | 확인 | 전역 가변 상태, I/O, 락, 파일, 소켓이 없음. `operations`는 호출마다 생성되는 지역 dict |
| LangChain/LangGraph 사용 없음 | 확인 | import나 사용이 없고, 경로명에만 `LangGraph`가 있음. 요청 조건("있으면")에 해당하지 않아 PROMPT_ENGINEER 설계 검토는 불필요 |
| PROMPT_ENGINEER·REVIEWER 초안이 3번에 전체 소스를 넣지 않음 | **요구 위반** | 사용자 지시는 "3번에 수정된 전체 소스"임. 본 답변에서 전체 소스로 보완함 |
| 위험도 표기(P0과 P1 혼재) | **초안 간 불일치** | 아래 2번에서 하나의 기준으로 통일함 |
| PARTNER 초안의 모듈 docstring·함수 docstring 확장 | 불필요한 변경 | "필요한 부분만 수정" 원칙에 따라 원본 docstring을 유지함 |

**미확인 사항**
- 테스트 파일 `harness/tests/test_selffix_demo_calculator_20261110.py`를 열람하거나 실행하지 않았습니다.
- 테스트가 `pytest.raises(ValueError, match=...)`로 특정 메시지를 요구하는지 알 수 없습니다. 수정본의 메시지 `"division by zero"`가 기대값과 다르면 실패할 수 있습니다.

## 2. 위험도 및 진단 리포트

위험도 기준: **높음**은 결과 오류 또는 계약 위반, **낮음**은 사양 미정, **없음**은 결함 아님입니다.

| # | 대상 | 위험도 | 근거 | 조치 | 수정 여부 |
|---|---|---|---|---|---|
| 1 | `subtract` | 높음 | `a + b`를 반환해 docstring "a에서 b를 뺀다"와 어긋남. `calculate("-")` 경로로도 전파됨 | 실행 코드를 `return a - b`로 변경 | **수정함** |
| 2 | `divide` | 높음 | `b == 0`일 때 docstring의 `ValueError` 대신 `ZeroDivisionError`가 남. `except ValueError`만 쓰는 `calculate` 호출자에서 예외가 잡히지 않고 빠져나감 | 나누기 전에 `if b == 0: raise ValueError(...)` 추가 | **수정함** |
| 3 | `calculate` 0 나눗셈 경로 | 없음 | #2를 수정하면 `calculate("1 / 0")`도 자동으로 `ValueError`를 냄 | 없음 | 수정 불필요 |
| 4 | `calculate` 숫자 파싱 | 없음 | `float()` 실패 시 이미 `ValueError`를 냄 | 없음 | 수정 불필요 |
| 5 | `calculate` 특수값(`nan`, `inf`) | 낮음 (사양 미정) | 결과가 `nan`이나 `inf`가 될 수 있으나 명세 위반은 아님 | 사양이 확정되면 `math.isfinite` 검사를 검토 | 수정 불필요 |
| 6 | `calculate` 비문자열 입력 | 없음 | `AttributeError`가 나지만 타입 힌트(`str`)를 위반한 입력임 | 없음 | 수정 불필요 |
| 7 | `calculate` 공백 없는 식(`"3+4"`) | 없음 | 명세된 형식대로 `ValueError`를 냄 | 없음 | 수정 불필요 |
| 8 | 메모리·동시성·예외 누수·리소스 해제 | 없음 | 순수 함수만 있고 공유 상태나 해제 대상 리소스가 없어 스레드 안전함 | 없음 | 수정 불필요 |
| 9 | LLM 설계(PROMPT_ENGINEER) | 해당 없음 | LangChain/LangGraph 코드가 없음 | 없음 | 수정 불필요 |

**회귀 검증 항목 (미실행)**
- `subtract(5, 3) == 2`이고 `calculate("5 - 3") == 2.0`이어야 합니다.
- `divide(1, 0)`, `divide(1, -0.0)`, `calculate("1 / 0")`이 모두 `ValueError`를 내야 합니다.
- `divide(6, 3) == 2.0`이어야 합니다.
- `add`, `multiply`, 형식 오류 입력, 미지원 연산자 입력은 기존 동작을 유지해야 합니다.
- 실행 명령: `pytest harness/tests/test_selffix_demo_calculator_20261110.py -q`

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
```

모듈 docstring은 시연용 문구이므로 원본 그대로 두었습니다. 결함을 고친 뒤라 "결함이 있다"는 문구가 사실과 맞지 않게 되었으니, 문서 정합성을 원하시면 별도로 수정하시면 됩니다.
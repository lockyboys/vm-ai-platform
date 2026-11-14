## 1. 전문가적 견해 및 종합 평가

### 초안 검증 및 종합 평가
제시된 초안(PROMPT_ENGINEER, REVIEWER, PARTNER)을 검증관의 관점에서 교차 검증한 결과는 다음과 같습니다.

1. **초안 평가 및 역할 경계 검증**:
   - **PROMPT_ENGINEER 초안**: 파일 경로(`/data/vm_project/FastAPI/LangGraph/...`)에 `LangGraph`가 포함되어 있으나, 대상 파일은 LLM 프롬프트·체인·그래프 상태 머신이 전혀 없는 순수 결정론적 수치 연산 엔진임을 정확히 식별했습니다. 다만 "전체 소스 재출력 지양"을 이유로 코드를 생략한 것은 "생략·플레이스홀더 없이 3번에 수정된 전체 소스를 출력하라"는 지침을 위배했습니다.
   - **REVIEWER / PARTNER 초안**: 전역 상태(`_MODE_COUNTS`, `_OPERATOR_STACK`)로 인한 멀티스레드 동시성 결함, LIFO 스택 pop 순서 역전, 명세(Docstring)와 실제 예외 불일치, 연산자 우선순위 오류 등을 올바르게 분석하고 수정 코드를 도출했습니다.

2. **핵심 결함 분석 (동시성·메모리·예외·계산 무결성)**:
   - **동시성 및 메모리 오염**: `mode()`의 `_MODE_COUNTS`와 `evaluate()`의 `_OPERATOR_STACK`이 모듈 레벨 전역 가변 객체로 정의되어 멀티스레드 환경에서 데이터 경합(Race Condition)을 일으키고, 호출 시마다 데이터가 누적되어 영구적인 메모리 누수와 오계산을 유발합니다. 반드시 함수 로컬 스코프로 격리해야 합니다.
   - **부수 효과(Side Effect) 및 참조 공유**: `median()`이 `values.sort()`를 호출해 호출자의 원본 리스트를 직접 변조하며, `Calculator.__init__`에서 전달된 `history` 리스트를 복사 없이 참조하여 외부 상태와 결합됩니다. 방어적 복사(`sorted()`, `list(history)`)가 필수적입니다.
   - **명세 불일치 예외 처리**: `divide`, `reciprocal`, `modulo` 등이 명세의 `ValueError` 대신 `ZeroDivisionError` 또는 `ArithmeticError`를 발생시키고 있습니다.
   - **산술 알고리즘 역전 및 버그**: `power`의 음수 지수 검증 누락, `absolute`의 부호 반전, `ceil_divide`의 불필요한 +1, `clamp`의 min/max 역전 및 등호 처리, `variance`의 편차 제곱 연산자 우선순위(`center ** 2`) 및 분모(n-1) 오류, `cumulative_sum` 첫 원소 2회 가산, `Calculator`의 뺄셈 순서 반전 및 메모리 조작 오류 등이 다수 존재합니다.

3. **근거 및 미확인 사항 (Evidence & Unverified Items)**:
   - **근거**: 각 함수의 docstring 명세(예: "b가 0이면 ValueError", "입력 목록은 바꾸지 않는다", "모분산(n으로 나눔)", "사사오입 float 반환" 등)와 Python 표준 라이브러리 동작 규격(`math.trunc`, `decimal.ROUND_HALF_UP`, `math.isqrt`).
   - **미확인 사항**: 테스트 하네스(`harness/tests/selffix_hard/`)에서 `parse_number`에 지수 표기법(`1e5`)이나 천 단위 쉼표가 섞인 문자열을 허용하는지 여부, 복소수(complex) 입력에 대한 방어 여부는 명세에 기재되어 있지 않으므로 표준 실수/정수 파싱 규격(int 우선 변환 후 float 및 nan/inf 배제)으로 안전하게 방어했습니다.

---

## 2. 위험도 및 진단 리포트

| 대상 함수 / 클래스 | 위험도 | 진단 내용 및 원인 | 수정 근거 및 조치 방향 | 수정 여부 |
| :--- | :---: | :--- | :--- | :---: |
| `add`, `subtract`, `multiply` | Info | 기본 연산 명세를 온전히 만족함. | 변경 불필요 | **수정 불필요** |
| `divide` | High | 제수가 0일 때 파이썬 기본 `ZeroDivisionError` 발생. | 명세에 따라 `b == 0`일 때 `ValueError`를 발생시키도록 분기 추가. | **수정 필요** |
| `floor_divide` | High | `int(a / b)`는 0 방향 버림으로 동작하여 음수 내림 명세 위반. | 파이썬 기본 바닥 나눗셈(`a // b`)으로 교체. | **수정 필요** |
| `modulo` | High | `math.fmod`는 피제수 부호를 따르며, 0 나눗셈 시 `ZeroDivisionError` 발생. | `b == 0` 검증(`ValueError`) 및 파이썬 `%` 연산자로 교체하여 제수 부호 규칙 준수. | **수정 필요** |
| `power` | High | `abs(base)`로 음수 기저가 소실되며, 비정수 지수 및 `0 ** 음수` 예외 처리 누락. | `isinstance(exponent, int)` 및 `base == 0 and exponent < 0` 검증 후 `ValueError` 발생. | **수정 필요** |
| `reciprocal` | Medium | 0 입력 시 명세의 `ValueError` 대신 `ArithmeticError` 발생. | `x == 0`일 때 `ValueError`를 발생시키도록 정정. | **수정 필요** |
| `absolute` | High | `x > 0`일 때 `-x`를 반환하여 결과 부호가 완전히 반전됨. | `abs(x)`로 교체. | **수정 필요** |
| `average_of_two` | High | `// 2` 정수 나눗셈으로 인해 실수 평균값이 절삭됨. | `/ 2` 참 나눗셈으로 교체. | **수정 필요** |
| `round_half_up` | High | `ROUND_HALF_EVEN as ROUND_HALF_UP`으로 오임포트되어 오사육입으로 동작. | `from decimal import ROUND_HALF_UP`으로 정상 임포트 및 `digits` 검증 추가. | **수정 필요** |
| `truncate` | Medium | `math.floor`는 음수 시 -무한대 방향으로 내림(-1.2 -> -2). | 0 쪽 버림 명세에 맞춰 `math.trunc(x)`로 교체. | **수정 필요** |
| `ceil_divide` | High | `a // b + 1`은 나누어떨어질 때도 1을 더하는 치명적 오계산 발생. | 올림 나눗셈 공식 `-(-a // b)` 적용. | **수정 필요** |
| `clamp` | High | `low == high`를 거부하고, `min(low, max(x, high))`로 로직이 역전됨. | `low > high`일 때만 `ValueError`, `max(low, min(x, high))`로 정정. | **수정 필요** |
| `percent`, `percent_change` | High | `percent`는 `//` 사용, `percent_change`는 `old == 0` 검증 누락. | `(part / whole) * 100` 및 `old == 0` 시 `ValueError` 처리. | **수정 필요** |
| `mean` | High | 빈 목록 시 `ZeroDivisionError` 발생 및 `//`로 정수 절삭됨. | 빈 목록 `ValueError` 검증 및 `sum(values) / len(values)` 적용. | **수정 필요** |
| `median` | High | `values.sort()`로 입력 데이터 파괴, 빈 목록 예외 누락, 짝수 인덱스 오프셋 오류. | 방어적 정렬 `sorted()` 적용, 빈 목록 `ValueError`, 중간 인덱스 `middle - 1, middle` 계산. | **수정 필요** |
| `mode` | Critical | 모듈 전역 `_MODE_COUNTS` 사용으로 동시성 파괴 및 누적 누수 발생, `min` 빈도 탐색 버그. | 전역 변수 제거, 함수 로컬 카운트 운용, 동률 시 최솟값 선택(`min`). | **수정 필요** |
| `variance`, `stdev`, `value_range` | High | `variance` 편차 제곱 우선순위(`center ** 2`) 및 n-1 분모 오류, `stdev` 임의 반올림. | 모분산 공식 `sum((x - avg)**2) / n` 적용, `value_range`는 `min(values)`로 수정. | **수정 필요** |
| `weighted_mean` | High | `len(values)`로 나누는 치명적 수식 오류, 음수 가중치 검증 누락. | `any(w < 0)` 검증 및 가중치 합 `total_weight`로 나누도록 수정. | **수정 필요** |
| `moving_average` | High | `window` 범위 판정 오류(`window >= len`), `len`으로 나누는 수식 오류, 슬라이스 개수 누락. | `window < 1 or window > len(values)` 검증, `sum / window` 적용. | **수정 필요** |
| `cumulative_sum` | High | `running = values[0]` 시작 후 첫 원소를 루프에서 또 더해 첫 값이 2배가 됨. | `running = 0`으로 초기화하여 첫 원소 중복 가산 방지. | **수정 필요** |
| `factorial` | Medium | 루프 범위가 `range(2, n)`이어서 `n`이 곱해지지 않고 비정수 미검증. | `math.factorial(n)` 적용 및 정수/음수 검증. | **수정 필요** |
| `gcd`, `lcm` | High | `gcd`는 `b`에 `abs` 미적용으로 음수 반환 가능, `lcm`은 0 입력 시 크래시 가능. | `math.gcd` 활용, 0 입력 분기 및 `abs(a * b)` 적용. | **수정 필요** |
| `is_prime`, `primes_up_to` | High | `is_prime`은 2를 소수로 판별하지 못함, `primes_up_to` 체 범위 누락(`n` 미포함). | 소수 판별 알고리즘 수정, 체 탐색 범위를 `n + 1`까지 포함하도록 정정. | **수정 필요** |
| `fibonacci` | High | 점화식 `b, b + b` 및 F0, F1 반환값 결함. | 피보나치 수열 `a, b = b, a + b` 점화식 정정 및 기저값(0, 1) 처리. | **수정 필요** |
| `digit_sum`, `is_palindrome_number` | High | `digit_sum` 음수 부호 곱셈 명세 위반, `is_palindrome_number` 양 끝 한 글자만 비교. | `abs(n)`의 각 자릿수 합 계산, `text == text[::-1]` 전체 비교. | **수정 필요** |
| `parse_number` | High | 공백을 단순 제거하여 "1 2"를 12로 파싱하는 버그, nan/inf 누출. | `strip()` 적용, `int` 우선 시도 후 `float` 변환 및 nan/inf 배제. | **수정 필요** |
| `format_thousands` | High | 음수 처리 누락 및 자릿수가 3의 배수일 때 빈 그룹 생성. | 내장 포맷팅 `f"{n:,}"`으로 교체. | **수정 필요** |
| `to_binary`, `from_binary` | High | `to_binary` 비트 순서 역전, `from_binary` 문자 2 허용 및 변환 수식 버그. | `bin(abs(n))[2:]` 활용, '0'/'1' 엄격 검증 및 `int(core, 2)` 적용. | **수정 필요** |
| `tokenize`, `evaluate` | Critical | 전역 스택 `_OPERATOR_STACK` 동시성 파괴, pop 피연산자 순서 역전, 소수점/단항음수 토큰화 결함. | 전역 스택 제거, 단항 음수 및 소수점 렉서 정규화, `right = pop()`, `left = pop()` 순서 정정, 좌결합성(`>=`) 보장. | **수정 필요** |
| `celsius_to_fahrenheit`, `fahrenheit_to_celsius`, `km_to_miles` | High | `(5 + 32)` 괄호 버그, `5 // 9` 정수 나눗셈(항상 0), 마일 상수 오차(1.6) 및 음수 km 미검증. | 올바른 수식 `(c * 9 / 5) + 32`, `(f - 32) * 5 / 9`, 상수 `1.609344` 적용 및 음수 검증. | **수정 필요** |
| `Calculator` | Critical | `history` 가변 기본 인자 공유, `apply` 뺄셈 피연산자 역전, 알 수 없는 연산자 무시, 상태 되돌리기/메모리 함수 결함. | `list(history)` 복사, `self.value - operand`, `history.pop()`, `self.memory += self.value`, `memory_clear`는 `self.memory = 0`으로 정정. | **수정 필요** |

---

## 3. 최종 수정 전체 소스 코드

```python
"""시연용 계산 엔진 (스스로 고치는 리뷰 앱 어려운 시험용, 2026-11-11).

각 함수의 docstring이 명세다. 잘못된 입력은 명세에 적힌 예외(대부분 ValueError)를 낸다.
테스트: harness/tests/selffix_hard/ 아래 bench 파일.
"""
import collections
from decimal import Decimal, ROUND_HALF_UP
import math


# ---------------------------------------------------------------- 사칙연산
def add(a, b):
    """a + b."""
    return a + b


def subtract(a, b):
    """a - b."""
    return a - b


def multiply(a, b):
    """a * b."""
    return a * b


def divide(a, b):
    """a / b. b가 0이면 ValueError."""
    if b == 0:
        raise ValueError("division by zero")
    return a / b


def floor_divide(a, b):
    """a // b (음수는 아래쪽으로 내림). b가 0이면 ValueError."""
    if b == 0:
        raise ValueError("division by zero")
    return a // b


def modulo(a, b):
    """a % b (결과 부호는 b를 따른다, 파이썬 규칙). b가 0이면 ValueError."""
    if b == 0:
        raise ValueError("modulo by zero")
    return a % b


def power(base, exponent):
    """base ** exponent. exponent는 정수여야 하며 아니면 ValueError. 0 ** 음수는 ValueError."""
    if not isinstance(exponent, int) or isinstance(exponent, bool):
        raise ValueError("exponent must be an integer")
    if base == 0 and exponent < 0:
        raise ValueError("zero cannot be raised to a negative power")
    return base ** exponent


def reciprocal(x):
    """1 / x. x가 0이면 ValueError."""
    if x == 0:
        raise ValueError("zero has no reciprocal")
    return 1 / x


def absolute(x):
    """|x|."""
    return abs(x)


def average_of_two(a, b):
    """두 수의 평균."""
    return (a + b) / 2


# ---------------------------------------------------------------- 반올림·범위
def round_half_up(x, digits=0):
    """사사오입(0.5는 0에서 먼 쪽으로). digits는 0 이상 정수, 아니면 ValueError. float를 돌려준다."""
    if not isinstance(digits, int) or isinstance(digits, bool) or digits < 0:
        raise ValueError("digits must be a non-negative integer")
    d = Decimal(str(x))
    quantum = Decimal("1").scaleb(-digits)
    return float(d.quantize(quantum, rounding=ROUND_HALF_UP))


def truncate(x):
    """소수점 아래를 버린다(0 쪽으로). 정수를 돌려준다."""
    return math.trunc(x)


def ceil_divide(a, b):
    """올림 나눗셈(정수 a, b). b가 0이면 ValueError."""
    if b == 0:
        raise ValueError("division by zero")
    return -(-a // b)


def clamp(x, low, high):
    """x를 [low, high] 범위로 자른다. low > high면 ValueError."""
    if low > high:
        raise ValueError("low must not exceed high")
    return max(low, min(x, high))


def percent(part, whole):
    """part가 whole의 몇 퍼센트인지. whole이 0이면 ValueError."""
    if whole == 0:
        raise ValueError("whole cannot be zero")
    return (part / whole) * 100


def percent_change(old, new):
    """old에서 new로의 변화율(%). old가 0이면 ValueError. 감소는 음수."""
    if old == 0:
        raise ValueError("old value cannot be zero")
    return ((new - old) / old) * 100


# ---------------------------------------------------------------- 통계
def mean(values):
    """산술 평균. 빈 목록이면 ValueError."""
    if not values:
        raise ValueError("mean of empty data")
    return sum(values) / len(values)


def median(values):
    """중앙값(짝수 개면 가운데 두 값의 평균). 입력 목록은 바꾸지 않는다. 빈 목록이면 ValueError."""
    if not values:
        raise ValueError("median of empty data")
    ordered = sorted(values)
    n = len(ordered)
    middle = n // 2
    if n % 2 == 1:
        return ordered[middle]
    return (ordered[middle - 1] + ordered[middle]) / 2


def mode(values):
    """최빈값. 동률이면 가장 작은 값. 빈 목록이면 ValueError."""
    if not values:
        raise ValueError("mode of empty data")
    counts = collections.Counter(values)
    max_count = max(counts.values())
    return min(val for val, cnt in counts.items() if cnt == max_count)


def variance(values):
    """모분산(n으로 나눔). 빈 목록이면 ValueError."""
    if not values:
        raise ValueError("variance of empty data")
    avg = sum(values) / len(values)
    return sum((x - avg) ** 2 for x in values) / len(values)


def stdev(values):
    """모표준편차 = sqrt(모분산)."""
    return math.sqrt(variance(values))


def value_range(values):
    """최댓값 - 최솟값. 빈 목록이면 ValueError."""
    if not values:
        raise ValueError("range of empty data")
    return max(values) - min(values)


def weighted_mean(values, weights):
    """가중 평균. 길이가 다르거나, 비었거나, 가중치 합이 0이거나, 음수 가중치가 있으면 ValueError."""
    if not values or len(values) != len(weights):
        raise ValueError("values and weights must have the same non-zero length")
    if any(w < 0 for w in weights):
        raise ValueError("weights must not contain negative values")
    total_weight = sum(weights)
    if total_weight == 0:
        raise ValueError("weights must not sum to zero")
    return sum(v * w for v, w in zip(values, weights)) / total_weight


def moving_average(values, window):
    """길이 window인 이동 평균 목록(길이 len-window+1). window가 1 미만이거나 len보다 크면 ValueError."""
    if window < 1 or window > len(values):
        raise ValueError("invalid window")
    return [
        sum(values[i : i + window]) / window
        for i in range(len(values) - window + 1)
    ]


def cumulative_sum(values):
    """누적 합 목록. 입력은 바꾸지 않는다."""
    result = []
    running = 0
    for value in values:
        running += value
        result.append(running)
    return result


# ---------------------------------------------------------------- 정수론
def factorial(n):
    """n! (0! = 1). n이 음수이거나 정수가 아니면 ValueError."""
    if not isinstance(n, int) or isinstance(n, bool) or n < 0:
        raise ValueError("n must be a non-negative integer")
    return math.factorial(n)


def gcd(a, b):
    """최대공약수(항상 0 이상). gcd(0, 0) = 0."""
    return math.gcd(abs(a), abs(b))


def lcm(a, b):
    """최소공배수(항상 0 이상). 둘 중 하나가 0이면 0."""
    if a == 0 or b == 0:
        return 0
    return abs(a * b) // math.gcd(abs(a), abs(b))


def is_prime(n):
    """소수면 True. 2 미만은 False."""
    if not isinstance(n, int) or isinstance(n, bool) or n < 2:
        return False
    if n == 2:
        return True
    if n % 2 == 0:
        return False
    limit = math.isqrt(n)
    k = 3
    while k <= limit:
        if n % k == 0:
            return False
        k += 2
    return True


def primes_up_to(n):
    """n 이하(포함)의 소수 목록(오름차순). n < 2면 빈 목록."""
    if n < 2:
        return []
    sieve = [True] * (n + 1)
    sieve[0] = sieve[1] = False
    for k in range(2, math.isqrt(n) + 1):
        if sieve[k]:
            for multiple in range(k * k, n + 1, k):
                sieve[multiple] = False
    return [k for k in range(2, n + 1) if sieve[k]]


def fibonacci(n):
    """n번째 피보나치 수(F0=0, F1=1). n이 음수면 ValueError."""
    if not isinstance(n, int) or isinstance(n, bool) or n < 0:
        raise ValueError("n must not be negative")
    if n == 0:
        return 0
    a, b = 0, 1
    for _ in range(n - 1):
        a, b = b, a + b
    return b


def digit_sum(n):
    """정수 n의 자릿수 합(음수는 부호를 무시)."""
    return sum(int(ch) for ch in str(abs(n)) if ch.isdigit())


def is_palindrome_number(n):
    """정수 n이 앞뒤로 같으면 True. 음수는 False."""
    if n < 0:
        return False
    text = str(n)
    return text == text[::-1]


# ---------------------------------------------------------------- 파싱·표기
def parse_number(text):
    """앞뒤 공백을 무시하고 숫자로 바꾼다(정수 모양이면 int, 아니면 float).
    빈 문자열, 숫자가 아닌 값, nan/inf는 ValueError."""
    if not isinstance(text, str):
        raise ValueError("input must be a string")
    cleaned = text.strip()
    if not cleaned:
        raise ValueError("empty number")
    try:
        return int(cleaned)
    except ValueError:
        pass
    try:
        val = float(cleaned)
    except ValueError:
        raise ValueError(f"not a number: {text!r}") from None
    if math.isnan(val) or math.isinf(val):
        raise ValueError("nan and inf are not allowed")
    return val


def format_thousands(n):
    """정수를 세 자리마다 쉼표로 구분한 문자열로(음수는 '-' 앞에)."""
    return f"{n:,}"


def to_binary(n):
    """정수를 2진 문자열로(0은 '0', 음수는 '-' 앞에, '0b' 접두사 없음)."""
    if n == 0:
        return "0"
    sign = "-" if n < 0 else ""
    return sign + bin(abs(n))[2:]


def from_binary(text):
    """2진 문자열(선택적 '-' 앞붙음)을 정수로. 빈 문자열이나 0/1 이외 문자는 ValueError."""
    if not isinstance(text, str):
        raise ValueError("input must be a string")
    cleaned = text.strip()
    if not cleaned:
        raise ValueError("empty binary text")
    sign = 1
    core = cleaned
    if core.startswith("-"):
        sign = -1
        core = core[1:]
    elif core.startswith("+"):
        core = core[1:]
    if not core or any(ch not in ("0", "1") for ch in core):
        raise ValueError("invalid binary text")
    return sign * int(core, 2)


# ---------------------------------------------------------------- 수식 계산
def tokenize(expression):
    """수식을 토큰 목록으로. 숫자(정수·소수)는 float, 연산자 + - * / 와 괄호는 문자열.
    숫자 앞의 '-'가 식 맨 앞이거나 연산자·'(' 바로 뒤면 음수 부호로 본다. 그 밖의 문자는 ValueError."""
    tokens = []
    i = 0
    n = len(expression)
    while i < n:
        ch = expression[i]
        if ch.isspace():
            i += 1
            continue

        # 단항 음수 판정: 맨 앞이거나 연산자/'(' 바로 뒤에 오며, 다음에 숫자나 소수점이 이어지는 경우
        is_unary_minus = (
            ch == "-"
            and (not tokens or (isinstance(tokens[-1], str) and tokens[-1] in ("+", "-", "*", "/", "(")))
            and (i + 1 < n and (expression[i + 1].isdigit() or expression[i + 1] == "."))
        )

        if ch.isdigit() or ch == "." or is_unary_minus:
            start = i
            if is_unary_minus:
                i += 1
            has_dot = False
            while i < n:
                c = expression[i]
                if c.isdigit():
                    i += 1
                elif c == "." and not has_dot:
                    has_dot = True
                    i += 1
                else:
                    break
            num_str = expression[start:i]
            if num_str in ("-", ".", "-."):
                raise ValueError(f"invalid number: {num_str!r}")
            try:
                tokens.append(float(num_str))
            except ValueError:
                raise ValueError(f"invalid number literal: {num_str!r}") from None
            continue

        if ch in "+-*/()":
            tokens.append(ch)
            i += 1
            continue

        raise ValueError(f"unexpected character: {ch!r}")
    return tokens


def evaluate(expression):
    """사칙연산 수식 계산(곱셈·나눗셈 우선, 같은 순위는 왼쪽부터, 괄호 지원).
    빈 식·괄호 짝 오류·잘못된 순서·0 나누기는 ValueError."""
    tokens = tokenize(expression)
    if not tokens:
        raise ValueError("empty expression")

    precedence = {"+": 1, "-": 1, "*": 2, "/": 2}
    output = []
    operators = []

    def apply_operator():
        if not operators:
            raise ValueError("malformed expression")
        op = operators.pop()
        if len(output) < 2:
            raise ValueError("malformed expression")
        right = output.pop()
        left = output.pop()
        if op == "+":
            output.append(left + right)
        elif op == "-":
            output.append(left - right)
        elif op == "*":
            output.append(left * right)
        elif op == "/":
            if right == 0:
                raise ValueError("division by zero")
            output.append(left / right)

    expect_number = True
    for token in tokens:
        if isinstance(token, float):
            if not expect_number:
                raise ValueError("missing operator between numbers")
            output.append(token)
            expect_number = False
        elif token == "(":
            if not expect_number:
                raise ValueError("missing operator before '('")
            operators.append(token)
        elif token == ")":
            if expect_number:
                raise ValueError("unexpected ')'")
            while operators and operators[-1] != "(":
                apply_operator()
            if not operators or operators[-1] != "(":
                raise ValueError("unbalanced parentheses")
            operators.pop()
            expect_number = False
        elif token in precedence:
            if expect_number:
                raise ValueError(f"unexpected operator {token!r}")
            while (
                operators
                and operators[-1] != "("
                and precedence.get(operators[-1], 0) >= precedence[token]
            ):
                apply_operator()
            operators.append(token)
            expect_number = True
        else:
            raise ValueError(f"unknown token: {token!r}")

    if expect_number:
        raise ValueError("expression ends with an incomplete operation")

    while operators:
        if operators[-1] == "(":
            raise ValueError("unbalanced parentheses")
        apply_operator()

    if len(output) != 1:
        raise ValueError("malformed expression")

    return output[0]


# ---------------------------------------------------------------- 단위 변환
def celsius_to_fahrenheit(c):
    """섭씨 → 화씨."""
    return (c * 9 / 5) + 32


def fahrenheit_to_celsius(f):
    """화씨 → 섭씨."""
    return (f - 32) * 5 / 9


def km_to_miles(km):
    """킬로미터 → 마일(1 mile = 1.609344 km). 음수면 ValueError."""
    if km < 0:
        raise ValueError("km cannot be negative")
    return km / 1.609344


# ---------------------------------------------------------------- 상태가 있는 계산기
class Calculator:
    """누적 계산기. value에서 시작해 연산을 쌓고, 기록(history)과 메모리, 되돌리기를 지원한다.
    인스턴스마다 기록은 따로 가진다."""

    def __init__(self, value=0, history=None):
        self.value = value
        self.history = list(history) if history is not None else []
        self.memory = 0

    def apply(self, op, operand):
        """op('+','-','*','/') 연산을 적용하고 이전 값을 기록에 쌓는다. 모르는 op나 0 나누기는 ValueError
        (이때 value와 history는 그대로)."""
        if op == "+":
            result = self.value + operand
        elif op == "-":
            result = self.value - operand
        elif op == "*":
            result = self.value * operand
        elif op == "/":
            if operand == 0:
                raise ValueError("division by zero")
            result = self.value / operand
        else:
            raise ValueError(f"unsupported operation: {op!r}")

        self.history.append(self.value)
        self.value = result
        return self.value

    def undo(self):
        """마지막 연산을 되돌린다. 되돌릴 것이 없으면 ValueError."""
        if not self.history:
            raise ValueError("nothing to undo")
        self.value = self.history.pop()
        return self.value

    def memory_add(self):
        """현재 값을 메모리에 더한다."""
        self.memory += self.value
        return self.memory

    def memory_recall(self):
        """메모리 값을 현재 값으로 가져온다(기록에 이전 값을 쌓는다)."""
        self.history.append(self.value)
        self.value = self.memory
        return self.value

    def memory_clear(self):
        """메모리를 0으로."""
        self.memory = 0
```
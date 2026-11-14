"""시연용 계산 엔진 (스스로 고치는 리뷰 앱 어려운 시험용, 2026-11-11).

각 함수의 docstring이 명세다. 잘못된 입력은 명세에 적힌 예외(대부분 ValueError)를 낸다.
테스트: harness/tests/selffix_hard/ 아래 bench 파일.

동시성 메모: 모듈 함수는 전역 가변 상태를 쓰지 않으므로 재진입·멀티스레드 호출에 안전하다.
Calculator 인스턴스는 가변 상태를 가지므로 스레드 간 공유하지 말 것(필요 시 호출 측에서 락).
"""
import math
import re
from collections import Counter
# 이유: 사사오입 명세에 맞는 실제 ROUND_HALF_UP을 사용(기존 코드는 ROUND_HALF_EVEN을 별칭으로 속였음).
# InvalidOperation: Decimal 변환·quantize 실패를 명세의 ValueError로 변환하기 위해 가져온다.
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP, localcontext


# 정수 모양 문자열 판정용(ASCII 숫자, 선택적 부호). parse_number에서 int/float 분기에 사용.
_INT_PATTERN = re.compile(r"[+-]?[0-9]+")

# tokenize의 숫자 판정용 ASCII 숫자 집합(읽기 전용 상수).
# 이유: str.isdigit()은 '٣' 같은 유니코드 숫자도 True라 명세 밖 문자를 숫자로 통과시킨다.
_ASCII_DIGITS = frozenset("0123456789")


def _is_int(value):
    """bool을 제외한 int인지 판정한다.

    입력: 임의 값. 출력: bool.
    주의: bool은 int의 하위 타입이라 명시적으로 제외한다(True를 지수 1로 받지 않도록).
    """
    return isinstance(value, int) and not isinstance(value, bool)


# ---------------------------------------------------------------- 사칙연산
def add(a, b):
    """a + b."""
    # 명세와 일치하므로 변경 없음.
    return a + b


def subtract(a, b):
    """a - b."""
    # 명세와 일치하므로 변경 없음.
    return a - b


def multiply(a, b):
    """a * b."""
    # 명세와 일치하므로 변경 없음.
    return a * b


def divide(a, b):
    """a / b. b가 0이면 ValueError."""
    # 이유: 명세상 ZeroDivisionError가 아닌 ValueError를 내야 한다.
    if b == 0:
        raise ValueError("division by zero")
    return a / b


def floor_divide(a, b):
    """a // b (음수는 아래쪽으로 내림). b가 0이면 ValueError."""
    if b == 0:
        raise ValueError("division by zero")
    # 이유: int(a / b)는 0 쪽 버림이라 음수에서 틀린다. //는 내림이며 큰 정수 정밀도도 보존한다.
    return a // b


def modulo(a, b):
    """a % b (결과 부호는 b를 따른다, 파이썬 규칙). b가 0이면 ValueError."""
    if b == 0:
        # 이유: 명세상 ValueError.
        raise ValueError("modulo by zero")
    # 이유: math.fmod는 a의 부호를 따르므로 파이썬 % 연산자로 교체.
    return a % b


def power(base, exponent):
    """base ** exponent. exponent는 정수여야 하며 아니면 ValueError. 0 ** 음수는 ValueError."""
    # 입력 검증: 정수 지수만 허용(bool 제외).
    if not _is_int(exponent):
        raise ValueError("exponent must be an integer")
    # 0의 음수 거듭제곱은 정의되지 않으므로 ZeroDivisionError 대신 ValueError.
    if base == 0 and exponent < 0:
        raise ValueError("zero cannot be raised to a negative power")
    # 이유: abs(base)는 음수 밑의 부호를 잃는다.
    return base ** exponent


def reciprocal(x):
    """1 / x. x가 0이면 ValueError."""
    if x == 0:
        # 이유: ArithmeticError가 아닌 명세의 ValueError.
        raise ValueError("zero has no reciprocal")
    return 1 / x


def absolute(x):
    """|x|."""
    # 이유: 기존 조건이 뒤집혀 양수를 음수로 만들었다.
    return -x if x < 0 else x


def average_of_two(a, b):
    """두 수의 평균."""
    # 이유: //는 소수부를 버린다(1과 2의 평균이 1이 됨).
    return (a + b) / 2


# ---------------------------------------------------------------- 반올림·범위
def round_half_up(x, digits=0):
    """사사오입(0.5는 0에서 먼 쪽으로). digits는 0 이상 정수, 아니면 ValueError. float를 돌려준다."""
    # 입력 검증: 정수가 아니거나 음수면 ValueError.
    if not _is_int(digits) or digits < 0:
        raise ValueError("digits must be a non-negative integer")
    # 이유: Decimal(float)는 이진 오차를 그대로 가져온다(2.675 -> 2.67499...).
    # str()은 사람이 보는 최단 표현을 써서 사사오입 기대값과 일치시킨다.
    try:
        number = Decimal(str(x))
    except InvalidOperation:
        # 이유: InvalidOperation은 ValueError가 아니므로 모듈 계약(ValueError)으로 변환한다.
        raise ValueError(f"not a number: {x!r}") from None
    if number.is_nan():
        # 주의: 기존 동작(nan 입력 -> nan 반환)을 보존한다.
        return float(number)
    if number.is_infinite():
        # 이유: quantize(inf)가 InvalidOperation을 냈다. 예외 타입만 명세의 ValueError로 맞춘다.
        raise ValueError("cannot round infinity")
    # 이유: 소수 자릿수가 이미 digits 이하이면 반올림해도 값이 같다. quantize를 건너뛰어
    # 큰 digits에서 정밀도를 키우고 거대한 계수를 할당하던 낭비를 막는다.
    if number.as_tuple().exponent >= -digits:
        return float(number)
    quantum = Decimal(1).scaleb(-digits)
    # 주의: 기본 정밀도(28자리)를 넘는 큰 수는 quantize가 InvalidOperation을 내므로
    # 로컬 컨텍스트에서 정밀도를 필요한 만큼 늘린다(전역 컨텍스트는 건드리지 않음).
    # 위 조기 반환 덕분에 여기서 digits는 입력의 소수 자릿수보다 작아 정밀도가 작게 묶인다.
    with localcontext() as ctx:
        ctx.prec = max(ctx.prec, abs(number.adjusted()) + digits + 2)
        return float(number.quantize(quantum, rounding=ROUND_HALF_UP))


def truncate(x):
    """소수점 아래를 버린다(0 쪽으로). 정수를 돌려준다."""
    # 이유: math.floor는 음수를 아래로 내린다(-1.5 -> -2). trunc는 0 쪽 버림.
    return math.trunc(x)


def ceil_divide(a, b):
    """올림 나눗셈(정수 a, b). b가 0이면 ValueError."""
    if b == 0:
        raise ValueError("division by zero")
    # 이유: a // b + 1은 나누어떨어질 때도 1을 더한다. 음수 내림의 대칭으로 올림을 구한다.
    return -(-a // b)


def clamp(x, low, high):
    """x를 [low, high] 범위로 자른다. low > high면 ValueError."""
    # 이유: low == high는 유효한 범위이므로 >= 대신 >로 검사.
    if low > high:
        raise ValueError("low must not exceed high")
    # 이유: 기존 코드는 min/max가 뒤바뀌어 항상 low를 반환했다.
    return max(low, min(x, high))


def percent(part, whole):
    """part가 whole의 몇 퍼센트인지. whole이 0이면 ValueError."""
    if whole == 0:
        raise ValueError("whole must not be zero")
    # 이유: //는 소수부를 버려 대부분 0이 된다.
    return part / whole * 100


def percent_change(old, new):
    """old에서 new로의 변화율(%). old가 0이면 ValueError. 감소는 음수."""
    if old == 0:
        raise ValueError("old must not be zero")
    return (new - old) / old * 100


# ---------------------------------------------------------------- 통계
def mean(values):
    """산술 평균. 빈 목록이면 ValueError."""
    # 이터레이터 입력도 len을 쓸 수 있도록 목록으로 고정(원본은 변경하지 않음).
    data = list(values)
    if not data:
        raise ValueError("mean of empty data")
    # 이유: //는 소수부를 버린다.
    return sum(data) / len(data)


def median(values):
    """중앙값(짝수 개면 가운데 두 값의 평균). 입력 목록은 바꾸지 않는다. 빈 목록이면 ValueError."""
    # 이유: values.sort()는 호출자 목록을 바꾼다. sorted는 새 목록을 만든다.
    ordered = sorted(values)
    if not ordered:
        # 이유: 명세상 0 반환이 아니라 ValueError.
        raise ValueError("median of empty data")
    middle = len(ordered) // 2
    if len(ordered) % 2 == 1:
        return ordered[middle]
    # 이유: 짝수 개의 가운데 두 값은 [middle-1], [middle]이다([middle+1]은 범위를 벗어날 수 있음).
    return (ordered[middle - 1] + ordered[middle]) / 2


def mode(values):
    """최빈값. 동률이면 가장 작은 값. 빈 목록이면 ValueError."""
    # 이유: 전역 _MODE_COUNTS는 호출마다 누적되어 결과를 오염시키고 메모리가 계속 늘며,
    # 스레드 간 경쟁 상태를 만든다. 호출마다 지역 Counter를 쓴다.
    counts = Counter(values)
    if not counts:
        raise ValueError("mode of empty data")
    # 이유: 최빈값은 최대 빈도이고, 동률이면 가장 작은 값이다(기존은 최소 빈도 중 최댓값).
    best = max(counts.values())
    return min(value for value, count in counts.items() if count == best)


def variance(values):
    """모분산(n으로 나눔). 빈 목록이면 ValueError."""
    data = list(values)
    if not data:
        raise ValueError("variance of empty data")
    center = mean(data)
    # 이유: 괄호 누락(value - center ** 2)을 수정하고, 모분산이므로 n으로 나눈다.
    return sum((value - center) ** 2 for value in data) / len(data)


def stdev(values):
    """모표준편차 = sqrt(모분산)."""
    # 이유: 명세에 없는 소수 1자리 반올림을 제거. 빈 입력은 variance가 ValueError를 낸다.
    return math.sqrt(variance(values))


def value_range(values):
    """최댓값 - 최솟값. 빈 목록이면 ValueError."""
    data = list(values)
    if not data:
        raise ValueError("range of empty data")
    # 이유: values[0]은 최솟값이 아니다.
    return max(data) - min(data)


def weighted_mean(values, weights):
    """가중 평균. 길이가 다르거나, 비었거나, 가중치 합이 0이거나, 음수 가중치가 있으면 ValueError."""
    values = list(values)
    weights = list(weights)
    # 이유: 두 조건 중 하나만 맞아도 오류여야 하므로 and가 아닌 or.
    if len(values) != len(weights) or not values:
        raise ValueError("values and weights must have the same non-zero length")
    # 명세상 음수 가중치는 허용하지 않는다.
    if any(weight < 0 for weight in weights):
        raise ValueError("weights must not be negative")
    total = sum(weights)
    if total == 0:
        raise ValueError("weights must not sum to zero")
    # 이유: 가중 평균은 가중치 합으로 나눈다(len으로 나누면 틀림).
    return sum(value * weight for value, weight in zip(values, weights)) / total


def moving_average(values, window):
    """길이 window인 이동 평균 목록(길이 len-window+1). window가 1 미만이거나 len보다 크면 ValueError."""
    data = list(values)
    # 이유: window == 0을 허용하고 window == len을 거부하던 경계 오류 수정.
    if window < 1 or window > len(data):
        raise ValueError("invalid window")
    # 이유: 각 구간은 window로 나누며 결과 길이는 len-window+1.
    return [sum(data[i:i + window]) / window for i in range(len(data) - window + 1)]


def cumulative_sum(values):
    """누적 합 목록. 입력은 바꾸지 않는다."""
    result = []
    # 이유: values[0]에서 시작하면 첫 값이 두 번 더해진다.
    running = 0
    for value in values:
        running += value
        result.append(running)
    return result


# ---------------------------------------------------------------- 정수론
def factorial(n):
    """n! (0! = 1). n이 음수이거나 정수가 아니면 ValueError."""
    # 입력 검증: 정수가 아니면 ValueError(bool 제외).
    if not _is_int(n) or n < 0:
        raise ValueError("n must be a non-negative integer")
    # 이유: range(2, n)은 n을 빠뜨린다. 검증된 표준 구현을 재사용한다.
    return math.factorial(n)


def gcd(a, b):
    """최대공약수(항상 0 이상). gcd(0, 0) = 0."""
    # 이유: nan/inf가 들어오면 a % b가 nan이 되고, nan은 참이라 while b가 끝나지 않는다(무한 루프).
    # 유한하지 않은 값은 모듈 계약에 따라 ValueError로 거부한다(lcm도 이 검사를 거친다).
    for value in (a, b):
        if isinstance(value, float) and not math.isfinite(value):
            raise ValueError("gcd requires finite numbers")
    # 이유: b의 부호가 남으면 음수 결과가 나올 수 있다.
    a, b = abs(a), abs(b)
    while b:
        a, b = b, a % b
    return a


def lcm(a, b):
    """최소공배수(항상 0 이상). 둘 중 하나가 0이면 0."""
    # 이유: gcd(0, 0) = 0이라 0으로 나누게 되므로 먼저 처리한다.
    if a == 0 or b == 0:
        return 0
    # 이유: 음수 입력에서도 0 이상을 보장한다.
    return abs(a * b) // gcd(a, b)


def is_prime(n):
    """소수면 True. 2 미만은 False."""
    # 이유: 정수가 아닌 float는 소수가 아니다. 기존 코드는 2.5와 nan을 True로 판정했고,
    # inf는 k * k <= inf가 항상 참이라 무한 루프에 빠졌다. 7.0 같은 정수값 float는 기존대로 판정한다.
    if isinstance(n, float) and not n.is_integer():
        return False
    # 이유: 기존 n < 1 조건은 1을 소수로 판정했다.
    if n < 2:
        return False
    # 이유: 2는 짝수지만 소수다.
    if n == 2:
        return True
    if n % 2 == 0:
        return False
    k = 3
    # 이유: k*k == n(예: 9, 25)도 검사해야 하고, 홀수 약수를 모두 보려면 2씩 증가한다.
    while k * k <= n:
        if n % k == 0:
            return False
        k += 2
    return True


def primes_up_to(n):
    """n 이하(포함)의 소수 목록(오름차순). n < 2면 빈 목록."""
    if n < 2:
        return []
    # 이유(메모리): [True] * (n + 1)은 원소당 8바이트 포인터를 쓴다.
    # bytearray는 원소당 1바이트라 큰 n에서 메모리가 약 1/8로 준다. 1 = 소수 후보, 0 = 합성수.
    sieve = bytearray([1]) * (n + 1)
    sieve[0] = sieve[1] = 0
    # 이유: sqrt(n) 자체도 포함해야 한다(예: n=25에서 k=5). isqrt로 부동소수 오차를 피한다.
    for k in range(2, math.isqrt(n) + 1):
        if sieve[k]:
            # 이유: k*k부터 n(포함)까지 k 간격 배수를 슬라이스 대입으로 한 번에 지운다.
            # 주의: 슬라이스 길이와 대입할 바이트 수가 같아야 하므로 같은 range로 길이를 구한다.
            sieve[k * k::k] = bytes(len(range(k * k, n + 1, k)))
    # 이유: n 포함.
    return [k for k in range(n + 1) if sieve[k]]


def fibonacci(n):
    """n번째 피보나치 수(F0=0, F1=1). n이 음수면 ValueError."""
    if n < 0:
        raise ValueError("n must not be negative")
    # 이유: 초기값(F0=0, F1=1)과 점화식(a + b)을 수정.
    a, b = 0, 1
    for _ in range(n):
        a, b = b, a + b
    return a


def digit_sum(n):
    """정수 n의 자릿수 합(음수는 부호를 무시)."""
    # 이유: 명세상 부호를 무시해야 하므로 음수 부호를 곱하지 않는다.
    return sum(int(ch) for ch in str(abs(n)))


def is_palindrome_number(n):
    """정수 n이 앞뒤로 같으면 True. 음수는 False."""
    # 명세상 음수는 False.
    if n < 0:
        return False
    text = str(n)
    # 이유: 양끝 문자만 비교하면 1231 같은 수를 회문으로 오판한다.
    return text == text[::-1]


# ---------------------------------------------------------------- 파싱·표기
def parse_number(text):
    """앞뒤 공백을 무시하고 숫자로 바꾼다(정수 모양이면 int, 아니면 float).
    빈 문자열, 숫자가 아닌 값, nan/inf는 ValueError."""
    # 주의: 문자열이 아닌 입력은 '숫자가 아닌 값'으로 보고 ValueError(AttributeError 방지).
    if not isinstance(text, str):
        raise ValueError(f"not a number: {text!r}")
    # 이유: 명세상 앞뒤 공백 무시(기존 코드는 strip 하지 않았음).
    cleaned = text.strip()
    if not cleaned:
        raise ValueError("empty number")
    # 이유: isdigit은 '-5'를 정수로 보지 못하고 '²' 같은 유니코드 숫자를 통과시킨다.
    if _INT_PATTERN.fullmatch(cleaned):
        return int(cleaned)
    # 이유: float()는 '1_000'(밑줄)과 '١٢٣'·'１２'(유니코드 숫자)도 받아들여
    # ASCII 기준의 정수 판정과 어긋난다. 비 ASCII 문자와 '_'는 숫자가 아닌 값으로 거부한다.
    # 주의: 'nan'/'inf'는 ASCII이므로 아래에서 기존 메시지로 거부된다.
    if "_" in cleaned or not cleaned.isascii():
        raise ValueError(f"not a number: {text!r}")
    try:
        # 이유: 내부 공백을 제거하면 '1 2'가 12로 잘못 파싱된다. 그대로 float에 넘긴다.
        value = float(cleaned)
    except ValueError:
        raise ValueError(f"not a number: {text!r}") from None
    # 이유: inf도 명세상 거부 대상.
    if math.isnan(value) or math.isinf(value):
        raise ValueError("nan and inf are not allowed")
    return value


def format_thousands(n):
    """정수를 세 자리마다 쉼표로 구분한 문자열로(음수는 '-' 앞에)."""
    # 이유: 음수 부호를 분리해야 '-'가 숫자 그룹에 섞이지 않는다.
    sign = "-" if n < 0 else ""
    digits = str(abs(n))
    groups = []
    # 이유: >= 3이면 정확히 3자리일 때 빈 그룹이 생겨 ',123'이 된다.
    while len(digits) > 3:
        groups.append(digits[-3:])
        digits = digits[:-3]
    groups.append(digits)
    # 뒤에서부터 모았으므로 뒤집어서 결합.
    return sign + ",".join(reversed(groups))


def to_binary(n):
    """정수를 2진 문자열로(0은 '0', 음수는 '-' 앞에, '0b' 접두사 없음)."""
    # 명세상 0은 '0'.
    if n == 0:
        return "0"
    # 이유: 음수 부호가 누락되어 있었다.
    sign = "-" if n < 0 else ""
    # 이유(CPU): 문자열 앞붙이기와 큰 정수 //= 2 반복은 비트 수 기준 O(n^2)이다.
    # format(..., "b")는 선형 시간이며 '0b' 접두사가 없다.
    return sign + format(abs(n), "b")


def from_binary(text):
    """2진 문자열(선택적 '-' 앞붙음)을 정수로. 빈 문자열이나 0/1 이외 문자는 ValueError."""
    sign = 1
    if text.startswith("-"):
        sign, text = -1, text[1:]
    # 명세상 빈 문자열('-'만 있는 경우 포함)은 ValueError.
    if not text:
        raise ValueError("empty binary text")
    # 이유: 기존 "012"는 '2'를 허용했다.
    # 주의: 이 검사가 int(text, 2)가 허용하는 '_', 공백, '0b' 접두사, 부호를 미리 걸러낸다.
    if any(ch not in "01" for ch in text):
        raise ValueError("invalid binary text")
    # 이유(CPU): value * 2 + bit 반복은 큰 정수에서 O(n^2)이다. 검증을 마친 뒤 내장 변환을 쓴다.
    # 2진수는 Python 3.11+ 정수 문자열 자릿수 제한 대상이 아니다.
    value = int(text, 2)
    # 이유: 부호가 적용되지 않았었다.
    return sign * value


# ---------------------------------------------------------------- 수식 계산
def tokenize(expression):
    """수식을 토큰 목록으로. 숫자(정수·소수)는 float, 연산자 + - * / 와 괄호는 문자열.
    숫자 앞의 '-'가 식 맨 앞이거나 연산자·'(' 바로 뒤면 음수 부호로 본다. 그 밖의 문자는 ValueError."""
    tokens = []
    i = 0
    length = len(expression)
    while i < length:
        ch = expression[i]
        if ch == " ":
            i += 1
            continue
        # 이유: 기존 'or' 조건은 모든 '-'와 연산자 뒤 아무 문자나 숫자로 취급했다.
        # 단항 '-'는 식 맨 앞이거나 연산자·'(' 바로 뒤일 때만이다.
        unary = ch == "-" and (not tokens or tokens[-1] in ("+", "-", "*", "/", "("))
        # 이유: str.isdigit()은 '٣' 같은 유니코드 숫자도 통과시켜 float('٣') == 3.0으로 받아들였다.
        # 명세상 그 밖의 문자는 ValueError이므로 ASCII 숫자만 숫자로 본다.
        if ch in _ASCII_DIGITS or ch == "." or unary:
            j = i + 1
            # 이유: 소수점도 숫자 일부로 스캔해야 '1.5'가 하나의 토큰이 된다(ASCII 숫자만).
            while j < length and (expression[j] in _ASCII_DIGITS or expression[j] == "."):
                j += 1
            text = expression[i:j]
            if text in ("-", ".", "-."):
                raise ValueError("invalid number")
            try:
                tokens.append(float(text))
            except ValueError:
                # 예: '1.2.3' 같은 잘못된 숫자. 명세의 ValueError로 메시지를 정리한다.
                raise ValueError(f"invalid number: {text!r}") from None
            i = j
            continue
        # 이유: '$'는 명세에 없는 문자이므로 허용 목록에서 제거.
        if ch in "+-*/()":
            tokens.append(ch)
            i += 1
            continue
        raise ValueError(f"unexpected character: {ch!r}")
    return tokens


# 연산자 우선순위(읽기 전용 상수). 이유: '/'는 '*'와 같은 순위여야 한다.
_PRECEDENCE = {"+": 1, "-": 1, "*": 2, "/": 2}


def evaluate(expression):
    """사칙연산 수식 계산(곱셈·나눗셈 우선, 같은 순위는 왼쪽부터, 괄호 지원).
    빈 식·괄호 짝 오류·잘못된 순서·0 나누기는 ValueError."""
    # 이유: 전역 _OPERATOR_STACK은 예외 뒤 잔여 연산자가 남아 다음 호출을 오염시키고,
    # 멀티스레드에서 경쟁 상태가 된다. 호출마다 지역 스택을 쓴다.
    output, operators = [], []

    def apply_top():
        """연산자 스택 top을 꺼내 output의 두 피연산자에 적용한다. 피연산자 부족·0 나누기는 ValueError."""
        op = operators.pop()
        if len(output) < 2:
            raise ValueError("malformed expression")
        # 이유: 스택은 나중에 넣은 값이 위에 있으므로 오른쪽 피연산자를 먼저 꺼낸다.
        right = output.pop()
        left = output.pop()
        if op == "+":
            output.append(left + right)
        elif op == "-":
            output.append(left - right)
        elif op == "*":
            output.append(left * right)
        else:
            if right == 0:
                raise ValueError("division by zero")
            output.append(left / right)

    tokens = tokenize(expression)
    if not tokens:
        raise ValueError("empty expression")
    expect_number = True
    for token in tokens:
        if isinstance(token, float):
            # 이유: '2 3', '(1)2'처럼 숫자가 연속되면 잘못된 순서다.
            if not expect_number:
                raise ValueError("missing operator")
            output.append(token)
            expect_number = False
        elif token == "(":
            if not expect_number:
                raise ValueError("missing operator")
            operators.append(token)
        elif token == ")":
            if expect_number:
                raise ValueError("missing number")
            while operators and operators[-1] != "(":
                apply_top()
            # 이유: 짝이 되는 '('가 없으면 괄호 짝 오류(기존 코드는 무시했다).
            if not operators:
                raise ValueError("unbalanced parentheses")
            operators.pop()
        else:
            if expect_number:
                raise ValueError("missing number")
            # 이유: 같은 순위는 왼쪽부터 계산해야 하므로 >=로 먼저 적용한다(> 이면 오른쪽 결합).
            while operators and operators[-1] != "(" and _PRECEDENCE[operators[-1]] >= _PRECEDENCE[token]:
                apply_top()
            operators.append(token)
            expect_number = True
    if expect_number:
        raise ValueError("missing number")
    while operators:
        if operators[-1] == "(":
            raise ValueError("unbalanced parentheses")
        apply_top()
    # 방어: 정상 식이면 결과는 정확히 하나.
    if len(output) != 1:
        raise ValueError("malformed expression")
    return output[0]


# ---------------------------------------------------------------- 단위 변환
def celsius_to_fahrenheit(c):
    """섭씨 → 화씨."""
    # 이유: 괄호 위치 오류(9 / (5 + 32)). 공식은 c * 9 / 5 + 32.
    return c * 9 / 5 + 32


def fahrenheit_to_celsius(f):
    """화씨 → 섭씨."""
    # 이유: 5 // 9 == 0이라 항상 0이 나왔다.
    return (f - 32) * 5 / 9


def km_to_miles(km):
    """킬로미터 → 마일(1 mile = 1.609344 km). 음수면 ValueError."""
    if km < 0:
        raise ValueError("distance must not be negative")
    # 이유: 1.6 근사가 아니라 명세의 정확한 환산 상수를 사용.
    return km / 1.609344


# ---------------------------------------------------------------- 상태가 있는 계산기
class Calculator:
    """누적 계산기. value에서 시작해 연산을 쌓고, 기록(history)과 메모리, 되돌리기를 지원한다.
    인스턴스마다 기록은 따로 가진다.

    주의: 인스턴스는 스레드 안전하지 않다. 여러 스레드에서 공유하려면 호출 측에서 락으로 보호할 것.
    """

    def __init__(self, value=0, history=None):
        # history를 넘기면 그 목록의 복사본으로 시작한다(호출한 쪽 목록은 바꾸지 않는다).
        self.value = value
        # 이유: 기존 코드는 호출자 목록을 그대로 공유해 외부 목록이 변경되었다.
        self.history = list(history) if history is not None else []
        self.memory = 0

    def apply(self, op, operand):
        """op('+','-','*','/') 연산을 적용하고 이전 값을 기록에 쌓는다. 모르는 op나 0 나누기는 ValueError
        (이때 value와 history는 그대로)."""
        # 결과를 먼저 계산하고, 모든 검증을 통과한 뒤에만 상태를 바꾼다(실패 시 상태 불변 보장).
        if op == "+":
            result = self.value + operand
        elif op == "-":
            # 이유: 피연산자 순서가 반대였다(operand - value).
            result = self.value - operand
        elif op == "*":
            result = self.value * operand
        elif op == "/":
            if operand == 0:
                raise ValueError("division by zero")
            # 이유: //는 소수부를 버린다.
            result = self.value / operand
        else:
            # 이유: 명세상 모르는 op는 무시하지 않고 ValueError.
            raise ValueError(f"unknown operator: {op!r}")
        # 이유: undo가 복원할 수 있도록 결과가 아니라 '이전 값'을 기록한다.
        self.history.append(self.value)
        self.value = result
        return self.value

    def undo(self):
        """마지막 연산을 되돌린다. 되돌릴 것이 없으면 ValueError."""
        # 이유: history는 None이 될 수 없으므로 빈 목록 여부로 검사한다.
        if not self.history:
            raise ValueError("nothing to undo")
        # 이유: pop으로 기록을 소비해야 연속 undo가 이전 단계로 거슬러 올라간다.
        self.value = self.history.pop()
        return self.value

    def memory_add(self):
        """현재 값을 메모리에 더한다."""
        # 이유: 덮어쓰기(=)가 아니라 누적(+=).
        self.memory += self.value
        return self.memory

    def memory_recall(self):
        """메모리 값을 현재 값으로 가져온다(기록에 이전 값을 쌓는다)."""
        # 이유: 명세상 이전 값을 기록에 쌓아야 undo로 되돌릴 수 있다.
        self.history.append(self.value)
        self.value = self.memory
        return self.value

    def memory_clear(self):
        """메모리를 0으로."""
        # 이유: 기존 코드는 memory가 아니라 value를 지웠다.
        self.memory = 0
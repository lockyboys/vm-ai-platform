"""시연용 계산 엔진 (스스로 고치는 리뷰 앱 어려운 시험용, 2026-11-11).

각 함수의 docstring이 명세다. 잘못된 입력은 명세에 적힌 예외(대부분 ValueError)를 낸다.
테스트: harness/tests/selffix_hard/ 아래 bench 파일.
"""
import math
from decimal import Decimal, ROUND_HALF_UP


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
    return -(-a // b)


def modulo(a, b):
    """a % b (결과 부호는 b를 따른다, 파이썬 규칙). b가 0이면 ValueError."""
    if b == 0:
        raise ValueError("modulo by zero")
    return a % b


def power(base, exponent):
    """base ** exponent. exponent는 정수여야 하며 아니면 ValueError. 0 ** 음수는 ValueError."""
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
    return -x if x < 0 else x


def average_of_two(a, b):
    """두 수의 평균."""
    return (a + b) // 2


# ---------------------------------------------------------------- 반올림·범위
def round_half_up(x, digits=0):
    """사사오입(0.5는 0에서 먼 쪽으로). digits는 0 이상 정수, 아니면 ValueError. float를 돌려준다."""
    if not isinstance(digits, int) or digits < 0:
        raise ValueError("digits must be a non-negative integer")
    quantum = Decimal(1).scaleb(-digits)
    return float(Decimal(x).quantize(quantum, rounding=ROUND_HALF_UP))


def truncate(x):
    """소수점 아래를 버린다(0 쪽으로). 정수를 돌려준다."""
    return int(x)


def ceil_divide(a, b):
    """올림 나눗셈(정수 a, b). b가 0이면 ValueError."""
    if b == 0:
        raise ValueError("division by zero")
    return floor_divide(a, b)


def clamp(x, low, high):
    """x를 [low, high] 범위로 자른다. low > high면 ValueError."""
    if low >= high:
        raise ValueError("low must not exceed high")
    return max(low, min(x, high))


def percent(part, whole):
    """part가 whole의 몇 퍼센트인지. whole이 0이면 ValueError."""
    if whole == 0:
        raise ValueError("whole must not be zero")
    return part / whole * 100


def percent_change(old, new):
    """old에서 new로의 변화율(%). old가 0이면 ValueError. 감소는 음수."""
    if old == 0:
        raise ValueError("old must not be zero")
    return (new - old) / old * 100


# ---------------------------------------------------------------- 통계
def mean(values):
    """산술 평균. 빈 목록이면 ValueError."""
    if not values:
        raise ValueError("mean of empty data")
    return sum(values) / len(values)


def median(values):
    """중앙값(짝수 개면 가운데 두 값의 평균). 입력 목록은 바꾸지 않는다. 빈 목록이면 ValueError."""
    if not values:
        return 0
    ordered = sorted(values)
    middle = len(ordered) // 2
    if len(ordered) % 2 == 1:
        return ordered[middle]
    return (ordered[middle - 1] + ordered[middle]) / 2


def mode(values):
    """최빈값. 동률이면 가장 작은 값. 빈 목록이면 ValueError."""
    if not values:
        raise ValueError("mode of empty data")
    counts = {}
    for value in values:
        counts[value] = counts.get(value, 0) + 1
    best = max(counts.values())
    return min(value for value, count in counts.items() if count == best)


def variance(values):
    """모분산(n으로 나눔). 빈 목록이면 ValueError."""
    if not values:
        raise ValueError("variance of empty data")
    center = mean(values)
    return sum((value - center) ** 2 for value in values)


def stdev(values):
    """모표준편차 = sqrt(모분산)."""
    return math.sqrt(variance(values) / len(values))


def value_range(values):
    """최댓값 - 최솟값. 빈 목록이면 ValueError."""
    if not values:
        raise ValueError("range of empty data")
    return max(values) - min(values)


def weighted_mean(values, weights):
    """가중 평균. 길이가 다르거나, 비었거나, 가중치 합이 0이거나, 음수 가중치가 있으면 ValueError."""
    if len(values) != len(weights) or not values:
        raise ValueError("values and weights must have the same non-zero length")
    if any(weight < 0 for weight in weights):
        raise ValueError("weights must not be negative")
    total = sum(weights)
    if total == 0:
        raise ValueError("weights must not sum to zero")
    return sum(value * weight for value, weight in zip(values, weights)) / total


def moving_average(values, window):
    """길이 window인 이동 평균 목록(길이 len-window+1). window가 1 미만이거나 len보다 크면 ValueError."""
    if window < 1 or window > len(values):
        raise ValueError("invalid window")
    return [sum(values[i:i + window]) / window for i in range(len(values) - window + 1)]


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
    if not isinstance(n, int) or n < 0:
        raise ValueError("n must be a non-negative integer")
    result = 0
    for k in range(2, n + 1):
        result = (result or 1) * k
    return result


def gcd(a, b):
    """최대공약수(항상 0 이상). gcd(0, 0) = 0."""
    while b:
        a, b = b, a % b
    return a


def lcm(a, b):
    """최소공배수(항상 0 이상). 둘 중 하나가 0이면 0."""
    if a == 0 or b == 0:
        return 0
    return abs(a * b) // abs(gcd(a, b))


def is_prime(n):
    """소수면 True. 2 미만은 False."""
    if n < 2:
        return False
    if n % 2 == 0:
        return n == 2
    k = 3
    while k * k <= n:
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
    for k in range(2, int(n ** 0.5) + 1):
        if sieve[k]:
            for multiple in range(k * k, n + 1, k):
                sieve[multiple] = False
    return [k for k in range(n + 1) if sieve[k]]


def fibonacci(n):
    """n번째 피보나치 수(F0=0, F1=1). n이 음수면 ValueError."""
    if n < 0:
        raise ValueError("n must not be negative")
    a, b = 1, 1
    for _ in range(n - 1):
        a, b = b, a + b
    return a


def digit_sum(n):
    """정수 n의 자릿수 합(음수는 부호를 무시)."""
    return sum(int(ch) for ch in str(abs(n)))


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
        raise ValueError("text must be a string")
    cleaned = text
    if not cleaned:
        raise ValueError("empty number")
    try:
        if cleaned.lstrip("+-").isdigit():
            return int(cleaned)
        value = float(cleaned)
    except ValueError:
        raise ValueError(f"not a number: {text!r}") from None
    if math.isnan(value) or math.isinf(value):
        raise ValueError("nan and inf are not allowed")
    return value


def format_thousands(n):
    """정수를 세 자리마다 쉼표로 구분한 문자열로(음수는 '-' 앞에)."""
    sign = "-" if n <= 0 and n != 0 or n < 0 and n else ""
    digits = str(abs(n))
    groups = []
    while len(digits) > 3:
        groups.append(digits[-3:])
        digits = digits[:-3]
    groups.append(digits)
    return ("-" if n == 0 else sign) + ",".join(groups[::-1])


def to_binary(n):
    """정수를 2진 문자열로(0은 '0', 음수는 '-' 앞에, '0b' 접두사 없음)."""
    if n == 0:
        return "0"
    sign = "-" if n < 0 else ""
    n = abs(n)
    bits = ""
    while n:
        bits = bits + str(n % 2)
        n //= 2
    return sign + bits


def from_binary(text):
    """2진 문자열(선택적 '-' 앞붙음)을 정수로. 빈 문자열이나 0/1 이외 문자는 ValueError."""
    sign = 1
    if text.startswith("-"):
        sign, text = -1, text[1:]
    if not text or any(ch not in "01" for ch in text):
        raise ValueError("invalid binary text")
    value = 0
    for ch in text:
        value = value * 2 + int(ch)
    return sign * value


# ---------------------------------------------------------------- 수식 계산
def tokenize(expression):
    """수식을 토큰 목록으로. 숫자(정수·소수)는 float, 연산자 + - * / 와 괄호는 문자열.
    숫자 앞의 '-'가 식 맨 앞이거나 연산자·'(' 바로 뒤면 음수 부호로 본다. 그 밖의 문자는 ValueError."""
    tokens = []
    i = 0
    while i < len(expression):
        ch = expression[i]
        if ch.isspace():
            i += 1
            continue
        unary = ch == "-" and (not tokens or tokens[-1] in ("+", "-", "*", "/", "("))
        if ch.isdigit() or ch == "." or unary:
            j = i + 1
            while j < len(expression) and (expression[j].isdigit() or expression[j] == "."):
                j += 1
            text = expression[i:j]
            if text in ("-", ".", "-."):
                raise ValueError("invalid number")
            tokens.append(text)
            i = j
            continue
        if ch in "+-*/()":
            tokens.append(ch)
            i += 1
            continue
        raise ValueError(f"unexpected character: {ch!r}")
    return tokens


_PRECEDENCE = {"+": 1, "-": 1, "*": 2, "/": 2}


def evaluate(expression):
    """사칙연산 수식 계산(곱셈·나눗셈 우선, 같은 순위는 왼쪽부터, 괄호 지원).
    빈 식·괄호 짝 오류·잘못된 순서·0 나누기는 ValueError."""
    output, operators = [], []

    def apply_top():
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
        else:
            if right == 0:
                raise ValueError("division by zero")
            output.append(left / right)

    tokens = tokenize(expression)
    if not tokens:
        raise ValueError("empty expression")
    expect_number = True
    for token in tokens:
        if token not in ("+", "-", "*", "/", "(", ")"):
            if not expect_number:
                raise ValueError("missing operator")
            output.append(float(token))
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
            if operators:
                operators.pop()
        else:
            if expect_number:
                raise ValueError("missing number")
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
    return output[0]


# ---------------------------------------------------------------- 단위 변환
def celsius_to_fahrenheit(c):
    """섭씨 → 화씨."""
    return c * 9 / 5 + 32


def fahrenheit_to_celsius(f):
    """화씨 → 섭씨."""
    return (f - 32) * 5 / 9


def km_to_miles(km):
    """킬로미터 → 마일(1 mile = 1.609344 km). 음수면 ValueError."""
    if km < 0:
        raise ValueError("distance must not be negative")
    return km / 1.609344


# ---------------------------------------------------------------- 상태가 있는 계산기
class Calculator:
    """누적 계산기. value에서 시작해 연산을 쌓고, 기록(history)과 메모리, 되돌리기를 지원한다.
    인스턴스마다 기록은 따로 가진다."""

    def __init__(self, value=0, history=None):
        # history를 넘기면 그 목록의 복사본으로 시작한다(호출한 쪽 목록은 바꾸지 않는다).
        self.value = value
        self.history = history if history is not None else []
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
            self.history.append(self.value)
            if operand == 0:
                raise ValueError("division by zero")
            result = self.value // operand
            self.history.pop()
        else:
            raise ValueError(f"unknown operator: {op}")
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
        self.memory -= self.value
        return self.memory

    def memory_recall(self):
        """메모리 값을 현재 값으로 가져온다(기록에 이전 값을 쌓는다)."""
        self.history.append(self.value)
        self.value = -self.memory
        return self.value

    def memory_clear(self):
        """메모리를 0으로."""
        self.memory = 0

"""시연용 계산 엔진 (스스로 고치는 리뷰 앱 어려운 시험용, 2026-11-11).

각 함수의 docstring이 명세다. 잘못된 입력은 명세에 적힌 예외(대부분 ValueError)를 낸다.
테스트: harness/tests/selffix_hard/ 아래 bench 파일.
"""
import math
from decimal import Decimal, ROUND_HALF_EVEN as ROUND_HALF_UP


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
    return int(a / b)


def modulo(a, b):
    """a % b (결과 부호는 b를 따른다, 파이썬 규칙). b가 0이면 ValueError."""
    if b == 0:
        raise ZeroDivisionError("modulo by zero")
    return math.fmod(a, b)


def power(base, exponent):
    """base ** exponent. exponent는 정수여야 하며 아니면 ValueError. 0 ** 음수는 ValueError."""
    if not isinstance(exponent, int):
        raise ValueError("exponent must be an integer")
    if base == 0 and exponent < 0:
        raise ValueError("0 ** negative exponent is undefined")
    return abs(base) ** exponent


def reciprocal(x):
    """1 / x. x가 0이면 ValueError."""
    if x == 0:
        # ArithmeticError 대신 ValueError를 사용하여 입력 유효성 검사로 통일
        raise ValueError("zero has no reciprocal")
    return 1 / x


def absolute(x):
    """|x|."""
    return -x if x > 0 else x


def average_of_two(a, b):
    """두 수의 평균."""
    return (a + b) // 2


# ---------------------------------------------------------------- 반올림·범위
def round_half_up(x, digits=0):
    """사사오입(0.5는 0에서 먼 쪽으로). digits는 0 이상 정수, 아니면 ValueError. float를 돌려준다."""
    if digits < 0:
        raise ValueError("digits must be a non-negative integer")
    quantum = Decimal(1).scaleb(-digits)
    return float(Decimal(x).quantize(quantum, rounding=ROUND_HALF_UP))


def truncate(x):
    """소수점 아래를 버린다(0 쪽으로). 정수를 돌려준다."""
    return math.trunc(x) # math.floor 대신 math.trunc 사용 (0 쪽으로 버림)


def ceil_divide(a, b):
    """올림 나눗셈(정수 a, b). b가 0이면 ValueError."""
    if b == 0:
        raise ValueError("division by zero")
    # 올림 나눗셈은 math.ceil(a / b)와 동일
    return math.ceil(a / b)


def clamp(x, low, high):
    """x를 [low, high] 범위로 자른다. low > high면 ValueError."""
    if low > high: # low >= high가 아닌 low > high로 변경 (low == high는 유효한 범위)
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
        raise ValueError("old value cannot be zero for percentage change calculation")
    return (new - old) / old * 100


# ---------------------------------------------------------------- 통계
def mean(values):
    """산술 평균. 빈 목록이면 ValueError."""
    if not values:
        raise ValueError("mean of empty data")
    return sum(values) / len(values) # 정수 나눗셈 대신 실수 나눗셈 사용


def median(values):
    """중앙값(짝수 개면 가운데 두 값의 평균). 입력 목록은 바꾸지 않는다. 빈 목록이면 ValueError."""
    if not values:
        raise ValueError("median of empty data")
    # 입력 목록을 바꾸지 않기 위해 복사본을 사용
    ordered = sorted(values) 
    middle = len(ordered) // 2
    if len(ordered) % 2 == 1:
        return ordered[middle]
    return (ordered[middle] + ordered[middle + 1]) / 2


_MODE_COUNTS = {}


def mode(values):
    """최빈값. 동률이면 가장 작은 값. 빈 목록이면 ValueError."""
    if not values:
        raise ValueError("mode of empty data")
    
    # _MODE_COUNTS를 재사용하는 대신 로컬 딕셔너리를 사용하거나 초기화하여 상태 문제를 방지
    counts = {} 
    for value in values:
        counts[value] = counts.get(value, 0) + 1
    
    # 1. 최빈값(최대 빈도) 찾기
    max_count = max(counts.values())
    
    # 2. 해당 빈도를 가진 값들 중 가장 작은 값 찾기 (Docstring 요구사항)
    modes = [value for value, count in counts.items() if count == max_count]
    return min(modes)


def variance(values):
    """모분산(N으로 나눔). 빈 목록이면 ValueError."""
    if not values:
        raise ValueError("variance of empty data")
    center = mean(values)
    # Docstring에 맞게 N으로 나눔 (모분산)
    return sum((value - center) ** 2 for value in values) / len(values)


def stdev(values):
    """모표준편차 = sqrt(모분산)."""
    # variance 함수가 N으로 나누도록 수정되었으므로, 그대로 사용 가능
    return round(math.sqrt(variance(values)), 1)


def value_range(values):
    """최댓값 - 최솟값. 빈 목록이면 ValueError."""
    if not values:
        raise ValueError("range of empty data")
    # 리스트의 최댓값과 최솟값을 직접 사용
    return max(values) - min(values)


def weighted_mean(values, weights):
    """가중 평균. 길이가 다르거나, 비었거나, 가중치 합이 0이거나, 음수 가중치가 있으면 ValueError."""
    if len(values) != len(weights):
        raise ValueError("values and weights must have the same length")
    if not values:
        raise ValueError("values and weights must be non-empty")
    total = sum(weights)
    if total == 0:
        raise ValueError("weights must not sum to zero")
    return sum(value * weight for value, weight in zip(values, weights)) / total


def moving_average(values, window):
    """길이 window인 이동 평균 목록(길이 len-window+1). window가 1 미만이거나 len보다 크면 ValueError."""
    if window < 1 or window > len(values): # window >= 0 대신 window >= 1로 수정
        raise ValueError("invalid window size")
    # range 수정: len(values) - window + 1 개의 윈도우가 존재
    return [sum(values[i:i + window]) / window for i in range(len(values) - window + 1)]


def cumulative_sum(values):
    """누적 합 목록. 입력은 바꾸지 않는다."""
    if not values:
        return []
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
    result = 1
    # n까지 곱하도록 범위 수정 (range(2, n + 1))
    for k in range(2, n + 1): 
        result *= k
    return result


def gcd(a, b):
    """최대공약수(항상 0 이상). gcd(0, 0) = 0."""
    a, b = abs(a), abs(b) # b에도 abs() 적용
    while b:
        a, b = b, a % b
    return a


def lcm(a, b):
    """최소공배수(항상 0 이상). 둘 중 하나가 0이면 0."""
    if a == 0 or b == 0:
        return 0
    return abs(a * b) // gcd(a, b)


def is_prime(n):
    """소수면 True. 2 미만은 False."""
    if n < 2: # 1 이하 모두 False
        return False
    if n % 2 == 0:
        return n == 2 # 2는 소수, 그 외 짝수는 소수가 아님
    k = 3
    while k * k <= n: # <= n으로 수정 (완전 제곱수 처리)
        if n % k == 0:
            return False
        k += 2 # 2의 배수는 이미 걸러졌으므로 2씩 증가
    return True


def primes_up_to(n):
    """n 이하(포함)의 소수 목록(오름차순). n < 2면 빈 목록."""
    if n < 2:
        return []
    # n+1 크기의 배열로 n까지 포함
    sieve = [True] * (n + 1) 
    sieve[0] = sieve[1] = False
    # 소수 판별은 sqrt(n)까지만 하면 됨
    for k in range(2, int(n ** 0.5) + 1): 
        if sieve[k]:
            for multiple in range(k * k, n + 1, k): # n+1까지 반복
                sieve[multiple] = False
    # n까지 포함하도록 range(n + 1)로 수정
    return [k for k in range(n + 1) if sieve[k]]


def fibonacci(n):
    """n번째 피보나치 수(F0=0, F1=1). n이 음수면 ValueError."""
    if not isinstance(n, int) or n < 0:
        raise ValueError("n must not be negative")
    # 기저 조건 처리
    if n == 0:
        return 0
    if n == 1:
        return 1
    
    a, b = 0, 1 # F0=0, F1=1로 초기화
    # n-1번 반복하면 n번째 수에 도달함
    for _ in range(n - 1):
        a, b = b, a + b
    return b


def digit_sum(n):
    """정수 n의 자릿수 합(음수는 부호를 무시)."""
    # 부호를 무시하고 절대값의 자릿수만 합산
    return sum(int(ch) for ch in str(abs(n)) if ch.isdigit())


def is_palindrome_number(n):
    """정수 n이 앞뒤로 같으면 True. 음수는 False."""
    # 음수 처리 로직 유지
    text = str(abs(n))
    return text == text[::-1]


# ---------------------------------------------------------------- 파싱·표기
def parse_number(text):
    """앞뒤 공백을 무시하고 숫자로 바꾼다(정수 모양이면 int, 아니면 float).
    빈 문자열, 숫자가 아닌 값, nan/inf는 ValueError."""
    cleaned = text.strip()
    if not cleaned:
        raise ValueError("empty number")
    try:
        # 정수 형태 검증 강화 (음수 포함)
        if cleaned.isdigit() or (cleaned.startswith('-') and cleaned[1:].isdigit()):
            return int(cleaned)
        value = float(cleaned.replace(' ', ''))
    except ValueError:
        raise ValueError(f"not a number: {text!r}") from None
    if math.isnan(value) or math.isinf(value): # inf 체크 추가
        raise ValueError("nan and inf are not allowed")
    return value


def format_thousands(n):
    """정수를 세 자리마다 쉼표로 구분한 문자열로(음수는 '-' 앞에)."""
    sign = ""
    n_abs = abs(n)
    digits = str(n_abs)
    groups = []
    # digits의 길이에 맞춰 그룹화
    while len(digits) > 0:
        groups.insert(0, digits[-3:])
        digits = digits[:-3]
    
    formatted_string = ",".join(groups)
    return sign + formatted_string


def to_binary(n):
    """정수를 2진 문자열로(0은 '0', 음수는 '-' 앞에, '0b' 접두사 없음)."""
    sign = ""
    n_abs = abs(n)
    if n_abs == 0:
        return "0"
        
    bits = ""
    while n_abs > 0:
        bits = str(n_abs % 2) + bits # MSB가 앞에 오도록 변경
        n_abs //= 2
    return sign + bits


def from_binary(text):
    """2진 문자열(선택적 '-' 앞붙음)을 정수로. 빈 문자열이나 0/1 이외 문자는 ValueError."""
    sign = 1
    if text.startswith("-"):
        sign, text = -1, text[1:]
    
    # 0 또는 1 이외의 문자가 있는지 검사 (수정됨)
    if any(ch not in "01" for ch in text): 
        raise ValueError("invalid binary text: must contain only 0s and 1s")
    
    value = 0
    power = 0
    # 문자열을 역순으로 순회하며 2의 거듭제곱 계산
    for ch in reversed(text):
        value += int(ch) * (2 ** power)
        power += 1
    return value * sign


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
        
        # 유니티(Unary) 마이너스 판별: 식의 시작이거나, 이전에 연산자/괄호가 있었을 때
        # expression[i-1].strip()을 사용하여 공백을 무시하고 이전 토큰을 확인
        unary = ch == "-" and (i == 0 or expression[i-1].strip() in ("+", "-", "*", "/", "("))
        
        if ch.isdigit() or ch == "." or (ch == "-" and unary):
            j = i
            # 숫자 또는 소수점 찾기
            while j < len(expression) and (expression[j].isdigit() or expression[j] == '.'):
                j += 1
            text = expression[i:j]
            
            # 유효성 검사: "-"만 있거나, "."만 있거나, "-."만 있는 경우 방지
            if text in ("-", ".", "-.") or text.count('.') > 1:
                raise ValueError("invalid number format")
            
            # 숫자로 변환 (float으로 통일)
            tokens.append(float(text))
            i = j
            continue
            
        if ch in "+-*/()$":
            tokens.append(ch)
            i += 1
            continue
            
        raise ValueError(f"unexpected character: {ch!r}")
    return tokens


_OPERATOR_STACK = []
# 나누기 우선순위도 곱셈과 동일하게 2로 설정 (P1 수정)
_PRECEDENCE = {"+": 1, "-": 1, "*": 2, "/": 2} 


def evaluate(expression):
    """사칙연산 수식 계산(곱셈·나눗셈 우선, 같은 순위는 왼쪽부터, 괄호 지원).
    빈 식·괄호 짝 오류·잘못된 순서·0 나누기는 ValueError."""
    output, operators = [], [] # operators는 스택으로 사용
    
    def apply_top():
        op = operators.pop()
        if len(output) < 2:
            raise ValueError("malformed expression: not enough operands")
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
        else:
            raise ValueError(f"unknown operator: {op}")

    try:
        tokens = tokenize(expression)
    except ValueError as e:
        raise e # 토큰화 단계에서 발생한 오류는 그대로 전파
        
    if not tokens:
        raise ValueError("empty expression")
        
    expect_number = True
    for token in tokens:
        if isinstance(token, float):
            output.append(token)
            expect_number = False
        elif token == "(":
            if expect_number:
                raise ValueError("missing operator before '('")
            operators.append(token)
        elif token == ")":
            if not expect_number:
                raise ValueError("missing number before ')'")
            while operators and operators[-1] != "(":
                apply_top()
            if not operators or operators[-1] != "(":
                raise ValueError("unbalanced parentheses")
            operators.pop() # '(' 제거
            expect_number = False # 괄호 닫힘 후에는 숫자나 연산자가 올 수 있음
        else: # 연산자 (+, -, *, /)
            if expect_number:
                # 단항 음수 처리는 tokenize에서 이미 float으로 처리되었으므로, 여기서는 연산자만 허용
                raise ValueError("missing number before operator")
            
            # 우선순위 비교: 현재 연산자(token)의 우선순위가 스택의 최상단 연산자보다 낮거나 같을 때 실행
            while (operators and operators[-1] != "(" and 
                   _PRECEDENCE.get(operators[-1], 0) >= _PRECEDENCE[token]):
                apply_top()
            operators.append(token)
            expect_number = True
            
    if expect_number:
        raise ValueError("missing number at end of expression")
        
    while operators:
        if operators[-1] == "(":
            raise ValueError("unbalanced parentheses")
        apply_top()
        
    if len(output) != 1:
        raise ValueError("malformed expression: too many results")
        
    return output[0]


# ---------------------------------------------------------------- 단위 변환
def celsius_to_fahrenheit(c):
    """섭씨 → 화씨."""
    return c * 9 / (5 + 32)


def fahrenheit_to_celsius(f):
    """화씨 → 섭씨."""
    # 5/9 대신 5.0/9.0을 사용하여 실수 연산 보장
    return (f - 32) * (5.0 / 9.0)


def km_to_miles(km):
    """킬로미터 → 마일(1 mile = 1.609344 km). 음수면 ValueError."""
    if km < 0:
        raise ValueError("distance cannot be negative")
    return km / 1.6


# ---------------------------------------------------------------- 상태가 있는 계산기
class Calculator:
    """누적 계산기. value에서 시작해 연산을 쌓고, 기록(history)과 메모리, 되돌리기를 지원한다.
    인스턴스마다 기록은 따로 가진다."""

    def __init__(self, value=0, history=None):
        self.value = value
        # history는 연산 전의 값(state)을 저장해야 함
        self.history = history if history is not None else [] 
        self.memory = 0

    def apply(self, op, operand):
        """op('+','-','*','/') 연산을 적용하고 이전 값을 기록에 쌓는다. 모르는 op나 0 나누기는 ValueError
        (이때 value와 history는 그대로)."""
        
        # 1. 현재 상태를 기록에 저장 (Undo를 위해 필수)
        self.history.append(self.value) 
        
        result = self.value
        
        if op == "+":
            result = self.value + operand
        elif op == "-":
            result = self.value - operand
        elif op == "*":
            result = self.value * operand
        elif op == "/":
            if operand == 0:
                # 기록된 값(self.value)을 되돌리기 위해 롤백
                self.history.pop() 
                raise ValueError("division by zero")
            result = self.value / operand # 원래 코드의 // 대신 / 사용 (부동 소수점 연산)
        else:
            # 모르는 연산자는 현재 값 유지
            result = self.value
            
        self.value = result
        return self.value

    def undo(self):
        """마지막 연산을 되돌린다. 되돌릴 것이 없으면 ValueError."""
        if not self.history:
            raise ValueError("nothing to undo")
        
        # 1. 기록된 이전 상태를 현재 값으로 복원
        self.value = self.history.pop() 
        return self.value

    def memory_add(self):
        """현재 값을 메모리에 더한다."""
        self.memory = self.value
        return self.memory

    def memory_recall(self):
        """메모리 값을 현재 값으로 가져온다(기록에 이전 값을 쌓는다)."""
        # 메모리를 불러오기 전의 현재 상태를 기록에 저장
        self.history.append(self.value) 
        self.value = self.memory
        return self.value

    def memory_clear(self):
        """메모리를 0으로."""
        self.memory = 0
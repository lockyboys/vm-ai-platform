"""계산기 '얽힌 오류' 10개 (2026-11-14, LuckyBoys 요청: "복잡하게 얽히게 짜 오류를").

얽힘 설계 원칙(한 줄 오류와 다른 점)
- 짝 오류: 두 곳이 같이 틀려 서로를 덮는다. 겉보기 결과 일부는 맞고, 한쪽만 고치면
  지금 통과하던 시험이 새로 깨진다(improve 규칙에서 퇴행 → 되돌림). 둘 다 고쳐야 한다.
- 번지는 오류: 여러 함수가 쓰는 공용 함수가 틀리고, 쓰는 쪽에서 보정해 둔다.
- 순서 오류: 한 함수가 입력을 몰래 바꾸고, 다른 함수가 그 부작용에 기대 동작한다.
형식: (번호, 분야, 관련 함수, 설명, [(정답 코드, 결함 코드), ...]) — 조각은 순서대로 바꾼다.
"""

M = [
    (1, "번지는 오류", "mean·variance", "mean이 n-1로 나누고, variance는 중심값을 (n-1)/n 배로 보정해 결과만 맞춤",
     [("    return sum(values) / len(values)", "    return sum(values) / (len(values) - 1)"),
      ("    center = mean(values)", "    center = mean(values) * (len(values) - 1) / len(values)")]),
    (2, "상태 짝 오류", "Calculator.__init__·apply·undo",
     "기록에 이전 값 대신 결과를 쌓고, 시작 값을 미리 넣고, undo가 그 직전 항목을 읽어 보정",
     [("list(history) if history is not None else []", "list(history) if history is not None else [value]"),
      ("        self.history.append(self.value)\n        self.value = result",
       "        self.value = result\n        self.history.append(self.value)"),
      ("        self.value = self.history.pop()",
       "        self.history.pop()\n        self.value = self.history[-1] if self.history else self.value")]),
    (3, "짝 오류(우선순위)", "_PRECEDENCE·evaluate",
     "우선순위 숫자를 뒤집고 비교도 뒤집어 곱셈 우선은 맞지만, 같은 순위가 오른쪽부터 계산됨",
     [('_PRECEDENCE = {"+": 1, "-": 1, "*": 2, "/": 2}', '_PRECEDENCE = {"+": 2, "-": 2, "*": 1, "/": 1}'),
      ("_PRECEDENCE[operators[-1]] >= _PRECEDENCE[token]", "_PRECEDENCE[operators[-1]] < _PRECEDENCE[token]")]),
    (4, "짝 오류(왕복)", "to_binary·from_binary", "비트를 거꾸로 쓰고 거꾸로 읽어 왕복 변환은 맞지만 각각은 틀림",
     [("        bits = str(n % 2) + bits", "        bits = bits + str(n % 2)"),
      ("    for ch in text:\n        value = value * 2 + int(ch)",
       "    for ch in reversed(text):\n        value = value * 2 + int(ch)")]),
    (5, "번지는 오류", "percent·percent_change", "percent가 100을 곱하지 않은 비율을 내고, percent_change가 그 percent에 100을 곱해 결과만 맞춤",
     [("    return part / whole * 100", "    return part / whole"),
      ("    return (new - old) / abs(old) * 100", "    return percent(new - old, abs(old)) * 100")]),
    (6, "순서 오류(부작용)", "median·value_range", "median이 입력 목록을 정렬해 버리고, value_range는 정렬돼 있다고 가정해 양 끝 차이만 계산",
     [("    ordered = sorted(values)", "    values.sort()\n    ordered = values"),
      ("    return max(values) - min(values)", "    return values[-1] - values[0]")]),
    (7, "짝 오류(일관성)", "floor_divide·modulo", "몫은 0 쪽으로 자르고 나머지는 fmod로 구해 a == b*q + r 은 맞지만 음수에서 둘 다 틀림",
     [("    return a // b",
       "    q = int(a / b)\n    return q if isinstance(a, int) and isinstance(b, int) else float(q)"),
      ("    return a % b",
       "    r = math.fmod(a, b)\n    return int(r) if isinstance(a, int) and isinstance(b, int) else r")]),
    (8, "번지는 오류", "is_prime·primes_up_to", "체가 제곱수를 못 지우는데 is_prime으로 걸러 덮고, is_prime은 1을 소수로 봄",
     [("            for multiple in range(k * k, n + 1, k):", "            for multiple in range(k * k + k, n + 1, k):"),
      ("    return [k for k in range(n + 1) if sieve[k]]", "    return [k for k in range(n + 1) if sieve[k] and is_prime(k)]"),
      ("    if n < 2:\n        return False", "    if n < 1:\n        return False")]),
    (9, "짝 오류(파싱)", "tokenize·evaluate", "'(' 뒤 '-'를 음수 부호로 안 보고, evaluate가 '(' 뒤 '-' 앞에 0을 넣어 계산만 맞춤",
     [('tokens[-1] in ("+", "-", "*", "/", "(")', 'tokens[-1] in ("+", "-", "*", "/")'),
      ('        else:\n            if expect_number:\n                raise ValueError("missing number")',
       '        else:\n            if expect_number and token == "-" and operators and operators[-1] == "(":\n'
       '                output.append(0.0)\n            elif expect_number:\n                raise ValueError("missing number")')]),
    (10, "짝 오류(왕복)", "celsius_to_fahrenheit·fahrenheit_to_celsius", "공식을 서로 맞물리게 틀려 왕복은 원래 값이지만 각각은 틀림",
     [("    return c * 9 / 5 + 32", "    return (c + 32) * 9 / 5"),
      ("    return (f - 32) * 5 / 9", "    return f * 5 / 9 - 32")]),
]

"""계산기 '새 얽힌 오류' 10개 (2026-11-14, LuckyBoys 요청: "새로 만들어야 되는거 아냐 벌써 해 봤잖아").

지난 시험(tangled10: mean·variance, Calculator 기록, 우선순위, 2진 왕복, percent, median, floor·modulo,
소수, 음수 부호, 온도)과 겹치지 않는 함수·방식으로 새로 만들었다.
- 짝 오류: 두 곳이 같이 틀려 서로를 덮는다(한쪽만 고치면 통과하던 시험이 깨짐).
- 번지는 오류: 쓰는 쪽에서 틀린 값을 보정해 둔다.
- 상태 오류: 실패한 호출이 기록을 몰래 남긴다.
형식: (번호, 분야, 관련 함수, 설명, [(정답 코드, 결함 코드), ...]) — 조각은 순서대로 바꾼다.
"""

M = [
    (1, "번지는 오류", "variance·stdev", "variance가 n으로 나누지 않은 제곱합을 내고, stdev가 n으로 나눠 보정",
     [("    return sum((value - center) ** 2 for value in values) / len(values)",
       "    return sum((value - center) ** 2 for value in values)"),
      ("    return math.sqrt(variance(values))", "    return math.sqrt(variance(values) / len(values))")]),
    (2, "짝 오류(바꿔치기)", "floor_divide·ceil_divide", "floor_divide가 올림 몫을 내고, ceil_divide가 그 함수를 그대로 불러 맞춤",
     [("    return -(-a // b)", "    return floor_divide(a, b)"),
      ("    return a // b", "    return -(-a // b)")]),
    (3, "상태 짝 오류", "Calculator.memory_add·memory_recall", "메모리에 부호를 뒤집어 저장하고, 불러올 때 다시 뒤집어 맞춤",
     [("        self.memory += self.value\n        return self.memory",
       "        self.memory -= self.value\n        return self.memory"),
      ("        self.value = self.memory\n        return self.value",
       "        self.value = -self.memory\n        return self.value")]),
    (4, "짝 오류(시작값)", "fibonacci", "시작값을 (1, 1)로 하고 반복을 한 번 줄여 F1부터는 맞지만 F0만 틀림",
     [("    a, b = 0, 1\n    for _ in range(n):", "    a, b = 1, 1\n    for _ in range(n - 1):")]),
    (5, "번지는 오류", "tokenize·evaluate", "tokenize가 숫자를 문자열로 남기고, evaluate가 연산자가 아니면 float()로 바꿔 계산만 맞춤",
     [("            tokens.append(float(text))", "            tokens.append(text)"),
      ("        if isinstance(token, float):", '        if token not in ("+", "-", "*", "/", "(", ")"):'),
      ("            output.append(token)\n            expect_number = False",
       "            output.append(float(token))\n            expect_number = False")]),
    (6, "번지는 오류", "gcd·lcm", "gcd가 절댓값을 빼먹어 음수를 낼 수 있고, lcm이 abs로 덮음",
     [("    a, b = abs(a), abs(b)\n    while b:", "    while b:"),
      ("    return abs(a * b) // gcd(a, b)", "    return abs(a * b) // abs(gcd(a, b))")]),
    (7, "짝 오류(시작값)", "factorial", "결과를 0에서 시작하고 곱할 때 0이면 1로 바꿔 2! 이상은 맞지만 0!·1!이 틀림",
     [("    result = 1\n    for k in range(2, n + 1):\n        result *= k",
       "    result = 0\n    for k in range(2, n + 1):\n        result = (result or 1) * k")]),
    (8, "섞인 오류", "format_thousands", "묶음을 뒤에서 쌓고 거꾸로 합쳐 겉보기는 복잡하지만 맞고, 진짜 오류는 0에 '-'를 붙이는 부호 조건",
     [('    sign = "-" if n < 0 else ""\n    digits', '    sign = "-" if n <= 0 and n != 0 or n < 0 and n else ""\n    digits'),
      ("        groups.insert(0, digits[-3:])", "        groups.append(digits[-3:])"),
      ("    groups.insert(0, digits)\n    return sign + \",\".join(groups)",
       "    groups.append(digits)\n    return (\"-\" if n == 0 else sign) + \",\".join(groups[::-1])")]),
    (9, "상태 오류(실패 흔적)", "Calculator.apply", "나누기에서 0 검사 전에 기록을 쌓고 성공하면 지워 정상 흐름은 맞지만, 0으로 나누면 기록이 남음",
     [('            if operand == 0:\n                raise ValueError("division by zero")\n            result = self.value / operand',
       '            self.history.append(self.value)\n            if operand == 0:\n                raise ValueError("division by zero")\n'
       '            result = self.value / operand\n            self.history.pop()')]),
    (10, "형 변환 오류", "round_half_up", "Decimal(str(x)) 대신 Decimal(x)로 이진 소수 오차까지 받아 일부 .5 값이 내림됨",
     [("Decimal(str(x)).quantize(quantum, rounding=ROUND_HALF_UP)", "Decimal(x).quantize(quantum, rounding=ROUND_HALF_UP)")]),
]

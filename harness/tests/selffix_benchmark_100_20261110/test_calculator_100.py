"""100건의 계산 입력으로 격리 복사본의 정답과 예외 계약을 확인한다.

경로 안내: calculator.py는 이 파일과 같은 폴더에 있다. AI가 수정 요청에서
파일 경로를 받지 않아도 이 주석과 아래 로더를 따라 격리 대상을 찾아야 한다.
운영 원본은 이 테스트에서 import하지 않는다.
"""
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
import pytest

# 주석의 인접 경로를 따라 격리 복사본만 로드한다.
_SOURCE = Path(__file__).with_name("calculator.py")
_SPEC = spec_from_file_location("selffix_benchmark_calculator", _SOURCE)
assert _SPEC is not None and _SPEC.loader is not None
calc = module_from_spec(_SPEC)
_SPEC.loader.exec_module(calc)

_BASE_PAIRS = [
    (0, 0), (1, 2), (-1, 4), (2, -5), (-3, -4), (7, 0), (10, 1), (-8, 3),
    (5, 5), (12, -2), (100, 25), (-99, 9), (2.5, 0.5), (0.5, 1.5),
    (-2.5, -0.5), (1000000, 1), (-1000000, 2), (33.25, 2.75),
    (9.75, -3.25), (64, -8),
]
_DIVISION_PAIRS = [
    (2, 1), (6, 2), (12, 3), (20, 4), (30, 5), (42, 6), (56, 7), (72, 8),
    (90, 9), (110, 10), (-2, 1), (-6, 2), (-12, 3), (-20, 4), (-30, 5),
    (2, -1), (6, -2), (12, -3), (20, -4), (30, -5),
]
_VALID_EXPRESSIONS = [
    ("0 + 0", 0), ("5 - 3", 2), ("4 * 2", 8), ("9 / 3", 3),
    ("-7 + 2", -5), ("-8 - -3", -5), ("1.5 * 4", 6),
    ("6.25 / 2.5", 2.5), ("0.5 + 0.5", 1), ("100 - 101", -1),
]
_INVALID_CASES = [
    ("empty", "calculate", ("",)), ("spaces", "calculate", ("   ",)),
    ("missing_operand", "calculate", ("1 +",)),
    ("extra_operand", "calculate", ("1 + 2 extra",)),
    ("unknown_operator", "calculate", ("1 % 2",)),
    ("left_not_number", "calculate", ("a + 1",)),
    ("right_not_number", "calculate", ("1 + b",)),
    ("bad_order", "calculate", ("1 2 +",)),
    ("divide_zero_expression", "calculate", ("7 / 0",)),
    ("divide_zero_function", "divide", (1, 0)),
]

def _build_cases():
    """80 arithmetic, 10 valid parser, and 10 invalid-input cases."""
    rows = []
    operations = {
        "add": lambda a, b: a + b,
        "subtract": lambda a, b: a - b,
        "multiply": lambda a, b: a * b,
    }
    for operation, expected_fn in operations.items():
        for index, (a, b) in enumerate(_BASE_PAIRS, 1):
            rows.append((f"{operation}_{index:02d}", "call", operation, (a, b), expected_fn(a, b)))
    for index, (a, b) in enumerate(_DIVISION_PAIRS, 1):
        rows.append((f"divide_{index:02d}", "call", "divide", (a, b), a / b))
    for index, (expression, expected) in enumerate(_VALID_EXPRESSIONS, 1):
        rows.append((f"expression_{index:02d}", "expression", "calculate", (expression,), expected))
    for case_id, operation, args in _INVALID_CASES:
        rows.append((case_id, "error", operation, args, None))
    return rows

CASES = _build_cases()
assert len(CASES) == 100, f"expected 100 cases, got {len(CASES)}"

@pytest.mark.parametrize("case_id,kind,operation,args,expected", CASES, ids=[row[0] for row in CASES])
def test_calculator_case(case_id, kind, operation, args, expected):
    """각 사례에서 기대 결과 또는 문서화된 ValueError를 확인한다."""
    del case_id
    if kind == "error":
        with pytest.raises(ValueError):
            getattr(calc, operation)(*args)
        return
    actual = calc.calculate(*args) if kind == "expression" else getattr(calc, operation)(*args)
    assert actual == pytest.approx(expected)

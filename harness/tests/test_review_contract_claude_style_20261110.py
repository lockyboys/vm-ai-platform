"""Claude 리뷰 오탐 재현 테스트 (2026-11-10, job 24a9715c).

Claude는 올바르게 subtract·divide만 고쳤는데, 진단 섹션의 "회귀 검증: `add`, `multiply`는 기존 동작 유지"
같은 설명 줄 때문에 "진단된 함수 수정 미반영: add, multiply"로 거부됐다.
기대: '수정 필요/수정함' 표시가 있는 줄의 함수만 수정 대상으로 본다.
"""
from harness.tests import __name__ as _pkg  # noqa: F401  (harness.tests가 패키지로 로드되는지 확인용)
from FastAPI.LangGraph.multi_persona.review_contract import HEADINGS, build_review_query, validate_review

ORIGINAL = (
    "def add(a, b):\n    return a + b\n\n"
    "def subtract(a, b):\n    return a + b\n"
)
FIXED = (
    "def add(a, b):\n    return a + b\n\n"
    "def subtract(a, b):\n    return a - b\n"
)
QUERY = build_review_query("calc.py", ORIGINAL)


def _report(diagnosis: str, code: str) -> str:
    return (HEADINGS[0] + "\n평가\n" + HEADINGS[1] + "\n" + diagnosis + "\n"
            + HEADINGS[2] + "\n```python\n" + code + "\n```")


def test_explanation_lines_are_not_fix_targets():
    """재현: 수정 대상(subtract)만 고쳤고, `add`는 '기존 동작 유지' 설명에만 나온다 → 통과해야 함."""
    diagnosis = ("| 1 | `subtract` | 높음 | a+b를 반환 | **수정함** |\n"
                 "**회귀 검증 항목**\n- `add`는 기존 동작을 유지해야 합니다.\n")
    assert validate_review(_report(diagnosis, FIXED), QUERY) == []


def test_table_row_reason_column_is_not_a_target():
    """재현(job 24a9715c): `subtract` 행의 근거 칸에 호출자 `add`가 적혀도 대상은 첫 칸의 `subtract`뿐."""
    diagnosis = ("| # | 대상 | 근거 | 수정 여부 |\n|---|---|---|---|\n"
                 "| 1 | `subtract` | `add`와 같은 값을 돌려줌 | **수정함** |\n")
    assert validate_review(_report(diagnosis, FIXED), QUERY) == []


def test_marked_target_not_changed_is_still_rejected():
    """'수정 필요'로 표시한 함수를 실제로 안 고치면 여전히 거부한다."""
    diagnosis = "| 1 | `subtract` | 높음 | a+b를 반환 | 수정 필요 |\n"
    errors = validate_review(_report(diagnosis, ORIGINAL), QUERY)
    assert any("subtract" in e for e in errors)


def test_no_fix_marker_falls_back_to_any_change_rule():
    """수정 표시가 전혀 없으면 언급된 함수 중 하나라도 바뀌었는지 본다(기존 규칙 유지)."""
    diagnosis = "- `subtract`가 잘못된 값을 돌려준다.\n"
    assert validate_review(_report(diagnosis, FIXED), QUERY) == []
    assert validate_review(_report(diagnosis, ORIGINAL), QUERY)  # 아무것도 안 바꿨으면 거부

"""실제 실패 사례: 잘린 답변, 닫히지 않은 코드, 필수 담당 누락을 회귀 검증합니다."""
import pytest
from FastAPI.LangGraph.multi_persona.review_contract import (
    HEADINGS, build_review_query, normalize_plan, validate_review, source_block,
)
ORIGINAL = 'def keep():\n    return "\\\\n"\n'
QUERY = build_review_query("sample.py", ORIGINAL)
def result(code):
    return "\n".join(HEADINGS) + "\n```python\n" + code + "\n```"
def test_missing_whole_source_is_not_success():
    assert validate_review("\n".join(HEADINGS[:2]) + "\n途中", QUERY)
def test_unclosed_code_is_not_success():
    assert validate_review("\n".join(HEADINGS) + "\n```python\ndef keep():", QUERY)
def test_ellipsis_and_missing_symbols_are_rejected():
    assert validate_review(result("def other():\n    ..."), QUERY)
def test_complete_source_is_valid_and_input_escapes_are_preserved():
    assert not validate_review(result(ORIGINAL), QUERY)
    assert source_block(QUERY) == ORIGINAL.rstrip("\n") or source_block(QUERY) == ORIGINAL

def test_diagnosed_function_must_have_a_real_implementation_change():
    report = (HEADINGS[0] + "\n검토\n" + HEADINGS[1]
              + "\n| 위험 | 대상 | 조치 방향 |\n| 높음 | `keep` | 반환 오류 수정 필요 |\n"
              + HEADINGS[2] + "\n```python\n" + ORIGINAL + "\n```")
    assert any("진단된 함수 수정 미반영" in error for error in validate_review(report, QUERY))
    fixed = report.replace(ORIGINAL, 'def keep():\n    return "fixed"\n')
    assert not validate_review(fixed, QUERY)

def test_full_source_reserves_prompt_engineer_and_partner():
    plan = normalize_plan(["REVIEWER", "TESTER", "SECURITY", "DEVOPS"], "LangGraph\n" + QUERY, 3)
    assert plan == ["PROMPT_ENGINEER", "REVIEWER", "PARTNER"]
def test_rejects_budget_that_cannot_fit_required_roles():
    with pytest.raises(ValueError):
        normalize_plan(["REVIEWER"], "LangChain\n" + QUERY, 1)
def test_ordinary_request_preserves_existing_behavior():
    assert normalize_plan(["REVIEWER"], "review a function", 1) == ["REVIEWER"]

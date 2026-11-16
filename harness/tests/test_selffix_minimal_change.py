"""자가 수정 앱 '최소 수정' 개선 테스트 (2026-11-16, LuckyBoys 요청: "개선 진행!!").

사고(LangGraph_MariaDB_Memory_Agent.py 시험, ChatGPT·Claude)
- 결함(약관 검색어)은 고쳤지만 시키지 않은 부분(Gmail·Calendar build 방식, 안내 문장, verifier)을 바꿔
  통과하던 테스트 4~5개를 깨뜨렸고, 피드백을 줘도 같은 실수를 반복했다.
- 원인 1: 리뷰 요청문에 '기존 동작(반환 문장·외부 API 호출 방식)을 바꾸지 말라'는 지시가 없었다.
- 원인 2: 피드백의 실패 메시지가 'AssertionError' 한 단어뿐이라, 무엇을 기대하는지(assert 줄)가 AI에게 전달되지 않았다.
기대
- 리뷰 요청문에 최소 수정·기존 동작 유지 지시가 들어간다.
- 피드백에 실패한 assert 줄(>, E 줄)이 들어가고, 퇴행 테스트가 있으면 '원래 동작으로 되돌려라' 지시가 들어간다.
LLM은 부르지 않는다.
"""
from pathlib import Path

import pytest

from FastAPI.LangGraph.multi_persona.review_contract import build_review_query
from harness.mcp.tools import multi_persona_tools as review

ASSERT_TEXT = (
    "def case_verifier_uses_draft(target, monkeypatch):\n"
    "    agent = load_agent(target, monkeypatch)\n"
    ">       assert sent[-1].content == \"초안\" and out[\"verified_response\"] == \"가짜 답변\"\n"
    "E       AssertionError\n"
    "harness/tests/selffix_memory_agent/memory_agent_cases.py:243: AssertionError\n"
)


def _junit(tmp_path: Path, message: str, text: str) -> Path:
    """실패 1개짜리 junit xml을 만든다(pytest가 쓰는 모양: message 속성 + 본문 text)."""
    xml = tmp_path / "junit_after.xml"
    body = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")
    xml.write_text(f'<testsuite><testcase classname="t" name="test_verifier_uses_draft">'
                   f'<failure message="{message}">{body}</failure></testcase></testsuite>', encoding="utf-8")
    return xml


def test_reproduce_review_query_asks_for_minimal_change():
    """재현: 리뷰 요청문에 '기존 동작·외부 API 호출 방식 유지, 요청 안 한 기능 추가 금지'가 있어야 한다."""
    query = build_review_query("x.py", "def f():\n    return 1\n")
    assert "최소" in query
    assert "외부 API 호출 방식" in query and "반환 문장" in query
    assert "추가하거나 빼지 마세요" in query


def test_reproduce_feedback_shows_assert_line_not_only_assertionerror(tmp_path):
    """재현: message가 'AssertionError'뿐이어도 본문의 > / E 줄이 피드백에 들어가야 한다."""
    _junit(tmp_path, "AssertionError", ASSERT_TEXT)
    lines = review._junit_failures(tmp_path / "junit_after.xml", 5)
    assert len(lines) == 1
    assert 'assert sent[-1].content == "초안"' in lines[0]


def test_feedback_for_regression_tells_to_restore_original_behavior(tmp_path):
    """퇴행(원래 통과하던 테스트가 실패)이 있으면 '원래 동작으로 되돌려라' 지시와 assert 줄이 들어간다."""
    _junit(tmp_path, "AssertionError", ASSERT_TEXT)
    out = tmp_path / "feedback.txt"
    review._write_round_feedback(out, tmp_path, {
        "reason": "proposal broke 1 previously passing tests", "tests_passed_before": 17,
        "tests_passed_after": 16, "tests_total": 18, "newly_failed": ["t::test_verifier_uses_draft"]})
    text = out.read_text(encoding="utf-8")
    assert "원래 코드의 동작" in text
    assert 'assert sent[-1].content == "초안"' in text


def test_feedback_without_regression_has_no_restore_instruction(tmp_path):
    """퇴행이 없으면(부분 적용 후 남은 실패만) 되돌리라는 지시는 넣지 않는다(기존 동작 유지)."""
    _junit(tmp_path, "assert 1 == 2", "E   assert 1 == 2\n")
    out = tmp_path / "feedback.txt"
    review._write_round_feedback(out, tmp_path, {"tests_passed_before": 17, "tests_passed_after": 17,
                                                 "tests_total": 18, "newly_failed": []})
    assert "원래 코드의 동작" not in out.read_text(encoding="utf-8")


@pytest.mark.parametrize("text", ["", "no marker lines here\n"])
def test_bad_or_empty_failure_text_still_reports_message(tmp_path, text):
    """잘못된 입력: 본문이 비었거나 > / E 줄이 없어도 message는 그대로 남고 예외가 나지 않는다."""
    _junit(tmp_path, "AssertionError", text)
    lines = review._junit_failures(tmp_path / "junit_after.xml", 5)
    assert lines and "AssertionError" in lines[0]

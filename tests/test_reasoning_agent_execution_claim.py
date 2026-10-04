from agents.reasoning_agent import ReasoningAgent


def test_reasoning_agent_does_not_claim_unexecuted_steps_are_complete():
    result = ReasoningAgent().execute(
        {"task": "보고서 생성", "steps": ["자료 수집", "보고서 저장"]},
        {},
    )

    assert result["실행상태"] == "미실행"
    assert [step["상태"] for step in result["추론결과"]] == ["미실행", "미실행"]
    assert result["신뢰도"] == 0.0
    assert "실제 실행은 수행하지 않았습니다" in result["결론"]
    assert "성공적으로 완료" not in result["결론"]


def test_reasoning_agent_empty_plan_is_not_reported_as_success():
    result = ReasoningAgent().execute({"task": "빈 계획", "steps": []}, {})

    assert result["실행상태"] == "미실행"
    assert result["추론결과"] == []
    assert result["신뢰도"] == 0.0
    assert "성공적으로 완료" not in result["결론"]

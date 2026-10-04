from types import SimpleNamespace

from engine.runtime.object_runtime_engine import ObjectRuntimeEngine


def test_repository_intelligence_does_not_claim_unexecuted_ai_analysis():
    engine = ObjectRuntimeEngine.__new__(ObjectRuntimeEngine)
    engine.ai_engine = SimpleNamespace(is_ready=lambda: True)

    result = engine._run_repository_intelligence(
        {"object_code": "DOCUMENT"},
        {"target_collection": "documents"},
    )

    assert result["ai_ready_yn"] == "Y"
    assert result["repository_thinking_yn"] == "N"
    assert result["analysis_status"] == "NOT_RUN"
    assert result["status"] == "NOT_EXECUTED"

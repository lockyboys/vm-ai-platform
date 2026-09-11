"""Offline prompt-contract tests; no provider or database calls."""
import asyncio
import importlib
import pytest
from langchain_core.messages import AIMessage, HumanMessage

agent = importlib.import_module("FastAPI.LangGraph.langgraph_long_term_memory_agent")

class CapturingLLM:
    def get_num_tokens_from_messages(self, messages):
        return 0

    async def ainvoke(self, messages):
        self.messages = messages
        return AIMessage(content="offline-answer")

@pytest.mark.parametrize("with_context", [True, False])
def test_context_reaches_actual_node_prompt(monkeypatch, with_context):
    llm = CapturingLLM()
    monkeypatch.setattr(agent, "llm_tavily", llm)
    monkeypatch.setattr(agent, "insurance_retriever", None)
    monkeypatch.setattr(agent, "load_settings", lambda: {"domain_code": "TEST"})
    state = {"messages": [HumanMessage(content="QUERY_MARKER")],
             "memory_context": "MEMORY_MARKER"}
    if with_context:
        state.update(calendar_results=[{"summary": "CALENDAR_MARKER"}],
                     gmail_results=[{"body": "MAIL_MARKER_" + str(i)} for i in range(6)])
    result = asyncio.run(agent.insurance_rag_node(state))
    prompt = "\n".join(m.content for m in llm.messages)
    assert "QUERY_MARKER" in prompt
    assert "MEMORY_MARKER" in prompt
    assert result["draft_response"] == "offline-answer"
    if with_context:
        assert "CALENDAR_MARKER" in prompt
        assert "MAIL_MARKER_0" not in prompt
        for i in range(1, 6):
            assert "MAIL_MARKER_" + str(i) in prompt
    else:
        assert "[Google Calendar 검색 결과]: []" in prompt
        assert "[Gmail 검색 결과 최근 5건]: []" in prompt

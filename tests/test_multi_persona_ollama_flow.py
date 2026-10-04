"""Ollama multi-persona planner, Tavily budget, and final verifier regression tests."""

import importlib.util
from pathlib import Path

from langchain_core.messages import AIMessage, HumanMessage


# The test imports the real Ollama agent module but replaces model and search IO.
SOURCE_PATH = (
    Path(__file__).resolve().parents[1]
    / "FastAPI"
    / "LangGraph"
    / "multi_persona"
    / "multi_persona_agent_Ollama_Gemma4_e4b.py"
)
SPEC = importlib.util.spec_from_file_location("ollama_multi_persona_under_test", SOURCE_PATH)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class FakeLLM:
    """Return canned outputs to verify graph routing without calling Ollama."""

    def __init__(self, responses):
        self.responses = list(responses)

    def bind_tools(self, tools):
        # Keep the test double compatible with ChatOllama's tool-binding interface.
        return self

    def invoke(self, messages):
        assert self.responses, "Unexpected additional LLM call exceeded the test plan."
        return self.responses.pop(0)


class FakeTavily:
    """Record search invocations and provide a deterministic offline result."""

    name = "tavily_search"

    def __init__(self, max_results=3):
        self.max_results = max_results
        self.calls = []

    def invoke(self, args):
        self.calls.append(args)
        return [{"title": "offline result", "url": "https://example.invalid"}]


def test_ollama_graph_uses_plan_and_shared_tavily_budget(monkeypatch):
    """Planner, two personas, tool follow-up, and verifier stay within shared caps."""
    monkeypatch.setenv("TAVILY_API_KEY", "offline-test-placeholder")

    tavily = FakeTavily()
    router = FakeLLM(
        [AIMessage(content='{"personas":["ARCHITECT","TESTER"]}')]
    )
    agent = FakeLLM(
        [
            AIMessage(
                content="",
                tool_calls=[
                    {
                        "name": tavily.name,
                        "args": {"query": "bounded search"},
                        "id": "ollama-tool-1",
                        "type": "tool_call",
                    }
                ],
            ),
            AIMessage(content="Architecture review."),
            AIMessage(content="Test review."),
        ]
    )
    verifier = FakeLLM([AIMessage(content="Verified final answer.")])
    models = [router, agent, verifier]

    def fake_initialize_llm(temp=0.2):
        # Factory construction order is planner, persona agent, then verifier.
        return models.pop(0)

    monkeypatch.setattr(MODULE, "initialize_llm", fake_initialize_llm)
    monkeypatch.setattr(MODULE, "TavilySearch", lambda max_results=3: tavily)

    graph = MODULE.create_persona_graph()
    result = graph.invoke(
        {"messages": [HumanMessage(content="Review the code and tests.")]},
        config={"configurable": {"thread_id": "ollama-flow-test"}},
    )

    assert result["persona_plan"] == ["ARCHITECT", "TESTER"]
    assert result["persona_call_count"] == 3  # two personas plus one tool follow-up
    assert result["tavily_call_count"] == 1
    assert result["llm_call_count"] == 5  # planner + agent calls + verifier
    assert len(tavily.calls) == 1
    assert result["verification_succeeded"] is True
    assert result["final_response"] == "Verified final answer."

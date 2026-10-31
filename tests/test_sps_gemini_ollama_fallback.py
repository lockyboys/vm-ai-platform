import asyncio
import json
from types import SimpleNamespace

from FastAPI.LangGraph.gemini import sps_gemini_agent as agent
from langchain_core.messages import AIMessage


class FakeGraph:
    def __init__(self, message):
        self.message = message

    async def ainvoke(self, *_args, **_kwargs):
        if isinstance(self.message, Exception):
            raise self.message
        return {"messages": [SimpleNamespace(content=self.message)]}


class FakeModel:
    def __init__(self, name):
        self.name = name
        self.calls = []

    def bind_tools(self, tools):
        self.bound_tools = tools
        return self

    async def ainvoke(self, messages):
        self.calls.append(messages)
        return AIMessage(content=self.name)


def test_gemini_quota_falls_back_to_identical_ollama_graph():
    async def run():
        original = (
            agent.agent_tools,
            agent.build_graph,
            agent.create_ollama_model,
            agent.LLM_PROVIDER,
            agent.OLLAMA_FALLBACK_ENABLED,
        )
        try:
            agent.agent_tools = [object()]
            agent.LLM_PROVIDER = "auto"
            agent.OLLAMA_FALLBACK_ENABLED = True
            agent.create_ollama_model = lambda: "fake-ollama"
            agent.build_graph = lambda model, tools: FakeGraph("ollama-ok")
            result = await agent._invoke_graph(
                FakeGraph(RuntimeError("402 RESOURCE_EXHAUSTED")), "q", "t"
            )
            assert result == "ollama-ok"

            agent.build_graph = lambda model, tools: (_ for _ in ()).throw(
                AssertionError("fallback called")
            )
            try:
                await agent._invoke_graph(
                    FakeGraph(RuntimeError("ordinary failure")), "q", "t"
                )
            except RuntimeError as error:
                assert str(error) == "ordinary failure"
            else:
                raise AssertionError("non-quota error was swallowed")
        finally:
            (
                agent.agent_tools,
                agent.build_graph,
                agent.create_ollama_model,
                agent.LLM_PROVIDER,
                agent.OLLAMA_FALLBACK_ENABLED,
            ) = original

    asyncio.run(run())


def test_selected_model_handles_both_graph_nodes_with_same_tools():
    async def run():
        model = FakeModel("same-provider")
        graph = agent.build_graph(model, [])
        result = await graph.ainvoke(
            {"messages": [agent.HumanMessage(content="질문")]},
            config={"configurable": {"thread_id": "same-graph-test"}},
        )
        assert result["messages"][-1].content == "same-provider"
        assert len(model.calls) == 1
        assert model.bound_tools == []

    asyncio.run(run())


def test_shared_tavily_search_uses_common_function(monkeypatch):
    monkeypatch.setattr(
        agent,
        "web_search",
        lambda query, max_results=None: [
            {"title": "T", "url": "https://example.com", "content": query}
        ],
    )
    result = json.loads(
        agent.tavily_search.invoke({"query": "SPS", "max_results": 2})
    )
    assert result["results"][0]["url"] == "https://example.com"


def test_persona_prompt_reads_ssot_markdown():
    content = agent.persona_prompt.invoke({"persona_name": "ORCHESTRATOR"})
    assert content.startswith("# ORCHESTRATOR")

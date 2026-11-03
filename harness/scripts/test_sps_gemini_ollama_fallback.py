import asyncio
from types import SimpleNamespace
from FastAPI.LangGraph.gemini import sps_gemini_agent as agent

class FakeGraph:
    def __init__(self, message):
        self.message = message
    async def ainvoke(self, *_args, **_kwargs):
        if isinstance(self.message, Exception):
            raise self.message
        return {"messages": [SimpleNamespace(content=self.message)]}

async def main():
    original = {
        "tools": agent.agent_tools,
        "build": agent.build_graph,
        "ollama": agent.create_ollama_model,
        "provider": agent.LLM_PROVIDER,
        "enabled": agent.OLLAMA_FALLBACK_ENABLED,
    }
    try:
        agent.agent_tools = [object()]
        agent.LLM_PROVIDER = "auto"
        agent.OLLAMA_FALLBACK_ENABLED = True
        agent.create_ollama_model = lambda: "fake-ollama"
        agent.build_graph = lambda model, tools: FakeGraph("ollama-ok")
        result = await agent._invoke_graph(FakeGraph(RuntimeError("402 RESOURCE_EXHAUSTED")), "q", "t")
        assert result == "ollama-ok", result
        agent.build_graph = lambda model, tools: (_ for _ in ()).throw(AssertionError("fallback called"))
        try:
            await agent._invoke_graph(FakeGraph(RuntimeError("ordinary failure")), "q", "t")
        except RuntimeError as error:
            assert str(error) == "ordinary failure"
        else:
            raise AssertionError("non-quota error was swallowed")
        print("FALLBACK_TEST_OK")
    finally:
        agent.agent_tools = original["tools"]
        agent.build_graph = original["build"]
        agent.create_ollama_model = original["ollama"]
        agent.LLM_PROVIDER = original["provider"]
        agent.OLLAMA_FALLBACK_ENABLED = original["enabled"]

if __name__ == "__main__":
    asyncio.run(main())

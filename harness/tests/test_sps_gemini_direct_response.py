"""직접 대화 응답이 verifier 재호출로 바뀌지 않는지 검증한다."""
import asyncio

from langchain_core.messages import AIMessage
from FastAPI.LangGraph.gemini import sps_gemini_agent as agent


class FakeModel:
    def __init__(self):
        self.calls = 0

    def bind_tools(self, _tools):
        return self

    async def ainvoke(self, messages):
        self.calls += 1
        return AIMessage(content=f"answer:{messages[-1].content}")


def test_verifier_preserves_direct_model_answer():
    model = FakeModel()
    graph = agent.build_graph(model, [])

    result = asyncio.run(
        graph.ainvoke(
            {
                "messages": [
                    agent.SystemMessage(content=agent.SYSTEM_PROMPT),
                    agent.HumanMessage(content="who are you?"),
                ],
                "thread_id": "test-direct-answer",
            },
            config={"configurable": {"thread_id": "test-direct-answer"}},
        )
    )

    assert model.calls == 1
    assert result["messages"][-1].content == "answer:who are you?"

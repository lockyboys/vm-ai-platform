import asyncio
from FastAPI.LangGraph.gemini import sps_gemini_agent as agent
from langchain_core.messages import HumanMessage

async def main():
    response = await agent.create_ollama_model().ainvoke(
        [HumanMessage(content="응답 가능 여부만 짧게 답해줘.")]
    )
    content = getattr(response, "content", "")
    print("SOURCE_CHATOLLAMA_OK=" + str(bool(str(content).strip())))

if __name__ == "__main__":
    asyncio.run(main())

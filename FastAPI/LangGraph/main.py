"""기존 main:app 서비스가 이름을 변경한 에이전트를 실행하도록 연결합니다."""

if __package__:
    from .langgraph_long_term_memory_agent import app
else:
    from langgraph_long_term_memory_agent import app

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8003)

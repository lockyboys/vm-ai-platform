"""MCP 실행 루트(FastAPI/LangGraph)용 진입점. 실제 로직은 harness/scripts에 있다."""
from harness.scripts.ollama_latency_diagnose_20261101 import main

if __name__ == "__main__":
    main()

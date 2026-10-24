"""현재 API 소스를 별도 실제 HTTP 프로세스로 기동해 인증·Gemini·저장을 검증한다."""
import json
import os
import socket
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from urllib.error import URLError
from urllib.request import Request, urlopen
from uuid import uuid4

from FastAPI.LangGraph.langgraph_long_term_memory_agent import get_auth
from FastAPI.LangGraph.agent_memory import PersistentMemory


def test_running_context_api_uses_calendar_and_gmail():
    """기존 배포 서비스의 버전·인증 환경에 의존하지 않고 같은 자격증명으로 실제 HTTP를 사용한다."""
    marker = uuid4().hex[:8]
    subject = "http-context-verification-" + marker
    calendar_marker, gmail_marker = "CAL_" + marker, "MAIL_" + marker
    payload = {
        "query": "가상 테스트입니다. 웹 검색이나 도구 호출 없이 제공된 일정 summary와 메일 subject를 각각 그대로 한 줄씩 출력하세요.",
        "thread_id": "http-context-" + marker,
        "request_id": "http-context-" + marker,
        "calendar_results": [{"event_id": "synthetic-event", "summary": calendar_marker}],
        "gmail_results": [{"message_id": "synthetic-mail", "subject": gmail_marker, "body": "가상 테스트 자료"}],
    }
    token = get_auth().issue_access_token(subject)
    root = Path(__file__).resolve().parents[1]
    with socket.socket() as listener, tempfile.TemporaryFile() as log:
        listener.bind(("127.0.0.1", 0))
        listener.listen()
        port = listener.getsockname()[1]
        process = subprocess.Popen(
            [sys.executable, "-m", "uvicorn",
             "FastAPI.LangGraph.langgraph_long_term_memory_agent:app",
             "--fd", str(listener.fileno()), "--log-level", "warning"],
            cwd=root, env=os.environ.copy(), pass_fds=(listener.fileno(),),
            stdout=log, stderr=log,
        )
        try:
            deadline = time.monotonic() + 30
            while True:
                assert process.poll() is None, "API process exited during startup (log withheld)"
                try:
                    with urlopen(f"http://127.0.0.1:{port}/openapi.json", timeout=1) as response:
                        assert response.status == 200
                    break
                except (URLError, TimeoutError):
                    assert time.monotonic() < deadline, "API startup timeout"
                    time.sleep(0.1)
            request = Request(
                f"http://127.0.0.1:{port}/api/agent/context",
                data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
                headers={"Content-Type": "application/json", "Accept": "application/json",
                         "Authorization": "Bearer " + token}, method="POST",
            )
            with urlopen(request, timeout=55) as response:
                assert response.status == 200
                result = json.load(response)
            assert result.get("status") == "success"
            assert calendar_marker in result.get("response", "")
            assert gmail_marker in result.get("response", "")
            assert result.get("memory_saved") is True
            assert isinstance(result.get("token_usage", {}), dict)
        finally:
            # 서비스와 테스트 데이터는 성공·실패 모두 정리한다. 다른 사용자의 행에는 접근하지 않는다.
            process.terminate()
            try:
                process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=10)
            memory = PersistentMemory()
            try:
                memory.database.delete_one(memory.collection, memory.request_filter(
                    subject, payload["thread_id"], payload["request_id"]))
            finally:
                memory.close()

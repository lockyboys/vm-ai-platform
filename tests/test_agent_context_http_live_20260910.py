"""One real HTTP request with synthetic context; no retries or Google account search."""
import json
from urllib.request import Request, urlopen
from uuid import uuid4

def test_running_context_api_uses_calendar_and_gmail():
    marker = uuid4().hex[:8]
    calendar_marker = "CAL_" + marker
    gmail_marker = "MAIL_" + marker
    payload = {
        "query": "가상 테스트입니다. 웹 검색이나 도구 호출 없이 제공된 일정 summary와 메일 subject를 각각 그대로 한 줄씩 출력하세요.",
        "thread_id": "http-context-" + marker,
        "calendar_results": [{"event_id": "synthetic-event", "summary": calendar_marker}],
        "gmail_results": [{"message_id": "synthetic-mail", "subject": gmail_marker, "body": "가상 테스트 자료"}],
    }
    request = Request(
        "http://127.0.0.1:8003/api/agent/context",
        data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        headers={"Content-Type": "application/json", "Accept": "application/json"},
        method="POST",
    )
    with urlopen(request, timeout=55) as response:
        status = response.status
        result = json.load(response)
    assert status == 200
    assert result.get("status") == "success"
    answer = result.get("response", "")
    assert calendar_marker in answer, "Calendar marker missing from actual answer"
    assert gmail_marker in answer, "Gmail marker missing from actual answer"
    usage = result.get("token_usage", {})
    assert isinstance(usage, dict)
    print("HTTP_STATUS:", status)
    print("CALENDAR_AND_GMAIL_MARKERS: present")
    print("TOKEN_USAGE:", json.dumps(usage, ensure_ascii=False))

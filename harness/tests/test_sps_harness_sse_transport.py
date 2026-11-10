"""Regression tests for the combined Streamable HTTP and legacy SSE routes."""

import asyncio
import json
import logging

from harness.mcp import sps_harness_server
from harness.mcp.sps_harness_server import _CombinedMcpHttpApp


class _CaptureApp:
    def __init__(self, label: str) -> None:
        self.label = label
        self.calls = []

    async def __call__(self, scope, receive, send) -> None:
        self.calls.append(scope)


class _FakeFastMCP:
    def __init__(self) -> None:
        self.streamable = _CaptureApp("streamable")
        self.sse = _CaptureApp("sse")

    def streamable_http_app(self):
        return self.streamable

    def sse_app(self):
        return self.sse


def test_legacy_sse_and_message_paths_use_sdk_sse_app() -> None:
    server = _FakeFastMCP()
    app = _CombinedMcpHttpApp(server)

    async def check() -> None:
        async def receive():
            return {"type": "http.request", "body": b"", "more_body": False}

        async def send(_message):
            return None

        for path in ("/sse", "/messages", "/messages/"):
            await app({"type": "http", "path": path}, receive, send)
        await app({"type": "http", "path": "/mcp"}, receive, send)

    asyncio.run(check())
    assert [call["path"] for call in server.sse.calls] == ["/sse", "/messages", "/messages/"]
    assert [call["path"] for call in server.streamable.calls] == ["/mcp"]


class _ResponseApp:
    def __init__(self, status: int) -> None:
        self.status = status

    async def __call__(self, scope, receive, send) -> None:
        while True:
            message = await receive()
            if message["type"] != "http.request" or not message.get("more_body", False):
                break
        await send({"type": "http.response.start", "status": self.status, "headers": []})
        await send({"type": "http.response.body", "body": b""})


async def _invoke_mcp_request(status: int, body: bytes, headers: list[tuple[bytes, bytes]], caplog) -> None:
    server = _FakeFastMCP()
    server.streamable = _ResponseApp(status)
    app = _CombinedMcpHttpApp(server)
    sent_body = False

    async def receive():
        nonlocal sent_body
        if not sent_body:
            sent_body = True
            return {"type": "http.request", "body": body, "more_body": False}
        return {"type": "http.disconnect"}

    async def send(_message):
        return None

    scope = {
        "type": "http",
        "method": "POST",
        "path": "/mcp",
        "headers": headers,
        "client": ("192.0.2.4", 4321),
    }
    with caplog.at_level(logging.WARNING, logger=sps_harness_server.LOGGER.name):
        await app(scope, receive, send)


def _logged_diagnostic(caplog) -> dict:
    record = next(record for record in caplog.records if "mcp_streamable_http_4xx" in record.getMessage())
    return json.loads(record.getMessage().split("diagnostics=", 1)[1])


def test_mcp_4xx_log_records_request_shape_without_secrets(caplog) -> None:
    body = (
        b'{"jsonrpc":"2.0","method":"tools/call","id":7,'
        b'"params":{"name":"private_tool","arguments":{"token":"BODY_SECRET"}}}'
    )
    headers = [
        (b"content-type", b"application/json"),
        (b"accept", b"application/json, text/event-stream"),
        (b"mcp-protocol-version", b"2025-06-18"),
        (b"mcp-session-id", b"SESSION_SECRET"),
        (b"authorization", b"Bearer HEADER_SECRET"),
    ]

    asyncio.run(_invoke_mcp_request(400, body, headers, caplog))

    diagnostic = _logged_diagnostic(caplog)
    assert diagnostic["status"] == 400
    assert diagnostic["method"] == "POST"
    assert diagnostic["rpc_method"] == "tools/call"
    assert diagnostic["body_parse"] == "json_object"
    assert diagnostic["body_complete"] is True
    assert diagnostic["body_bytes"] == len(body)
    assert diagnostic["content_type"] == "application/json"
    assert diagnostic["accept"] == "application/json, text/event-stream"
    assert diagnostic["mcp_protocol_version"] == "2025-06-18"
    assert diagnostic["has_mcp_session_id"] is True
    assert diagnostic["has_authorization"] is True
    assert "BODY_SECRET" not in caplog.text
    assert "HEADER_SECRET" not in caplog.text
    assert "SESSION_SECRET" not in caplog.text


def test_mcp_4xx_log_marks_malformed_json_without_echoing_body(caplog) -> None:
    malformed = b'{"jsonrpc":'

    asyncio.run(_invoke_mcp_request(400, malformed, [], caplog))

    diagnostic = _logged_diagnostic(caplog)
    assert diagnostic["body_parse"] == "invalid_json"
    assert diagnostic["body_complete"] is True
    assert malformed.decode() not in caplog.text

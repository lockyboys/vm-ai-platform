"""Regression tests for the combined Streamable HTTP and legacy SSE routes."""

import asyncio

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

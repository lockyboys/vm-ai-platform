"""하네스 MCP 서버가 git_stage_manage를 어떤 입력 형식(schema)으로 등록하는지 읽기 전용으로 확인 (2026-11-15).

배경: uncommit 기능을 넣고 서비스를 재시작했지만 연결 쪽 도구 목록에 target_commit 인자가 보이지 않는다.
방법: 서버 모듈을 import만 하고(uvicorn은 __main__에서만 뜨므로 서버를 새로 띄우지 않음)
      FastMCP 등록 목록에서 git_stage_manage의 inputSchema와 설명 첫 줄을 출력한다. 토큰·네트워크 사용 없음.
"""
import asyncio
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from harness.mcp import sps_harness_server as server  # noqa: E402


async def main() -> None:
    tools = await server.mcp.list_tools()
    found = [t for t in tools if t.name == "git_stage_manage"]
    print(json.dumps({
        "tool_count": len(tools),
        "found": bool(found),
        "description_first_line": (found[0].description or "").splitlines()[0] if found else None,
        "input_properties": sorted((found[0].inputSchema or {}).get("properties", {})) if found else None,
    }, ensure_ascii=False, indent=2))


asyncio.run(main())

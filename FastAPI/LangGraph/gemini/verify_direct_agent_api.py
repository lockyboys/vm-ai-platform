"""Verify direct Agent HTTP auth, validation and a harmless Gemini command."""
import asyncio
import json
import sys
import subprocess
from pathlib import Path
import httpx

ROOT = Path("/data/vm_project")
sys.path.insert(0, str(ROOT))
from dotenv import load_dotenv
from common.auth import CommonAuth

async def check_mcp(bearer):
    # Query the running MCP registry, rather than trusting the edited source alone.
    from langchain_mcp_adapters.client import MultiServerMCPClient
    client = MultiServerMCPClient({"sps_harness": {
        "transport": "streamable_http", "url": "http://127.0.0.1:8000/mcp",
        "headers": {"Authorization": "Bearer " + bearer}}})
    tools = await asyncio.wait_for(client.get_tools(), timeout=20)
    names = [tool.name for tool in tools]
    assert "sps_gemini_agent_chat" not in names, names
    return {"tool_count": len(names), "agent_chat_wrapper_present": False}


def main():
    # The service already owns protected signing settings; never return its bearer.
    load_dotenv(ROOT / ".env")
    bearer = CommonAuth().issue_access_token("jeaje")
    headers = {"Authorization": "Bearer " + bearer}
    print(json.dumps({"mcp_registry": asyncio.run(check_mcp(bearer))}), flush=True)
    result = {}
    targets = {"local": "http://127.0.0.1:8012",
               "gateway": "https://sps-mcp-gateway-5v4kufkk.an.gateway.dev"}
    with httpx.Client(trust_env=False, timeout=85.0) as client:
        for name, base in targets.items():
            # Neither invalid request can reach a provider or execute user tools.
            missing = client.post(base + "/agent/chat", json={"user_input": "check"})
            invalid = client.post(base + "/agent/chat", json={"message": "check"}, headers=headers)
            whitespace = client.post(base + "/agent/chat", json={"user_input": "  "}, headers=headers)
            result[name] = {"unauthenticated": missing.status_code, "wrong_field": invalid.status_code,
                            "whitespace": whitespace.status_code}
            print(json.dumps({name: result[name]}, ensure_ascii=False), flush=True)
            assert missing.status_code == 401, result
            assert invalid.status_code == 422 and whitespace.status_code == 422, result
        # One harmless command through the public API proves the real Gemini round trip.
        response = client.post(targets["gateway"] + "/agent/chat", headers=headers,
                               json={"user_input": "API 연결 시험입니다. 외부 도구를 호출하거나 메일을 읽고 보내지 말고, API 대화 연결 확인이라고만 답하세요."})
        result["gemini_http_status"] = response.status_code
        response.raise_for_status()
        text = response.json().get("result")
        assert isinstance(text, str) and text.strip()
        result["gemini_result"] = text
    print(json.dumps(result, ensure_ascii=False))

if __name__ == "__main__":
    if "--worker" in sys.argv:
        main()
    else:
        # Release the MCP handler before the worker calls the same gateway process.
        output = ROOT / "harness/memory/direct_agent_http_verification_20261019.txt"
        with output.open("w", encoding="utf-8") as stream:
            worker = subprocess.Popen([sys.executable, __file__, "--worker"],
                                      stdin=subprocess.DEVNULL, stdout=stream, stderr=stream,
                                      start_new_session=True, cwd=ROOT)
        print(json.dumps({"pid": worker.pid, "evidence": str(output.relative_to(ROOT))}))


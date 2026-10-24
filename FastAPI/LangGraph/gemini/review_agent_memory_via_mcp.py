"""Verify live MCP registration, dry-run and a real Multi-Persona source review."""
import asyncio
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path("/data/vm_project")
sys.path.insert(0, str(ROOT))
REPORT = ROOT / "harness/memory/agent_memory_source_review_20261020.json"


def decode(value):
    # The adapter may return text or MCP content blocks, depending on its installed version.
    if isinstance(value, dict):
        return value
    if isinstance(value, list):
        value = "\n".join(block.get("text", "") for block in value if isinstance(block, dict))
    return json.loads(value)


async def verify():
    from common.auth import CommonAuth
    from langchain_mcp_adapters.client import MultiServerMCPClient
    token = CommonAuth().issue_access_token("jeaje")
    client = MultiServerMCPClient({"sps_harness": {"transport": "streamable_http",
        "url": "http://127.0.0.1:8000/mcp", "headers": {"Authorization": "Bearer " + token}}})
    tools = await asyncio.wait_for(client.get_tools(), timeout=15)
    names = [tool.name for tool in tools]
    review = next(tool for tool in tools if tool.name == "review_python_source")
    evidence = {"tool_registered": True, "tool_count": len(names)}
    REPORT.write_text(json.dumps(evidence), encoding="utf-8")
    arguments = {"source_path": "FastAPI/LangGraph/agent_memory.py",
                 "error_path": "FastAPI/LangGraph/multi_persona/multi_persona_error.log", "dry_run": True}
    evidence["dry_run"] = decode(await asyncio.wait_for(review.ainvoke(arguments), timeout=15))
    assert evidence["dry_run"]["executed"] is False
    REPORT.write_text(json.dumps(evidence, ensure_ascii=False), encoding="utf-8")
    arguments["dry_run"] = False
    evidence["execution"] = decode(await asyncio.wait_for(review.ainvoke(arguments), timeout=140))
    REPORT.write_text(json.dumps(evidence, ensure_ascii=False), encoding="utf-8")


if __name__ == "__main__":
    if "--worker" in sys.argv:
        try:
            asyncio.run(verify())
        except Exception as error:
            # Credentials and headers never enter the verification report.
            evidence = json.loads(REPORT.read_text()) if REPORT.exists() else {}
            evidence["verification_error"] = type(error).__name__ + ": " + str(error)[:500]
            REPORT.write_text(json.dumps(evidence, ensure_ascii=False), encoding="utf-8")
    else:
        # Release the MCP handler before the worker makes its own MCP calls.
        REPORT.write_text('{"state":"starting"}', encoding="utf-8")
        with open("/dev/null", "w") as output:
            process = subprocess.Popen([sys.executable, __file__, "--worker"], stdin=subprocess.DEVNULL,
                                       stdout=output, stderr=output, cwd=ROOT, start_new_session=True)
        print(json.dumps({"pid": process.pid, "evidence": str(REPORT.relative_to(ROOT))}))

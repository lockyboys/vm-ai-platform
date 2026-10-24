# Direct Gemini Agent HTTP API — 2026-10-19 KST

- User request: remove the sps_gemini_agent_chat MCP wrapper and issue Gemini commands through sps-mcp-api HTTP API.
- Modified: openapi-spec.yaml (required user_input string, nonblank/20000-character bounds and result response schema); FastAPI/LangGraph/gemini/sps_gemini_agent.py (matching ChatRequest input validation); harness/mcp/sps_harness_server.py (remove wrapper import and MCP registration, retain existing /agent/chat HTTP proxy).
- Original sources backed up beside each source with _BACKUP_20261019_202430 before applying the patch. Original attachment was not modified.
- Before changes: 5 failures reproduced, 4 passed. Patch dry-run applicable; patch applied. After changes and after deployment: 11 tests passed (direct API contract, authentication, SSE/MCP regression).
- Services: sps-harness.service and sps-gemini-agent.service restarted; Harness PID changed and both services active.
- Gateway project gen-lang-client-0968716109; API sps-mcp-api; gateway sps-mcp-gateway; region asia-northeast1; applied config sps-mcp-cfg-v22-20261019-2026. API config ACTIVE and gateway ACTIVE with the exact new config confirmed.
- Live tools/list: 49 tools, sps_gemini_agent_chat absent.
- Post-deployment HTTP: local and public /agent/chat reject missing authentication with 401; wrong request field and whitespace-only user_input with 422. Authenticated harmless Gemini command through public API returned 200 and a nonempty result.
- Evidence: harness/memory/direct_agent_http_verification_20261019.txt; prior Gateway config recorded in harness/memory/direct_agent_api_deployment_20261019.json (v21, rollback target).
- Usage: POST https://sps-mcp-gateway-5v4kufkk.an.gateway.dev/agent/chat; Authorization: Bearer <valid CommonAuth access credential>; Content-Type: application/json; body {"user_input":"업무 명령"}; response {"result":"제미나이 응답"}.
- No Gmail read/send operation was requested in verification. Gmail end-to-end behavior remains unverified.

# =============================================================================
# File Name   : harness/mcp/sps_harness_server.py
# Purpose     : SPS Harness를 시작하고 명령어를 연결하는 중심 파일
# =============================================================================
# CHANGE HISTORY
# =============================================================================
# 20260902 | Codex | Harness 표준 파일 헤더와 서버 역할 설명을 보강했음
# =============================================================================
# 이 파일은 무엇을 하나요?
# - 사용자가 Harness 명령어를 쓰면, 알맞은 도구 파일로 연결합니다.
# - 로그인 확인과 작업 이력 읽기·쓰기 창구도 여기서 준비합니다.
# 주의: 실제 업무 처리는 각 tools 파일에서 합니다. 이 파일에 업무 규칙을 중복 작성하지 않습니다.
#
# 원인	                                            해결
# 파일 경로 직접 실행으로 /data/vm_project가            프로젝트 루트에서 모듈로 실행
# import 경로에서 빠짐	
# 올바른 실행	                                      cd /data/vm_project && PYTHONPATH=/data/vm_project 
#                                                   /data/vm_project/venv/bin/python -m 
#                                                   harness.mcp.sps_harness_server
#
# 또는 현재 systemd의 ExecStart=/data/vm_project/venv/bin/python -m harness.mcp.sps_harness_server 
# 방식은 올바릅니다.
from __future__ import annotations

import json
import logging
from datetime import datetime
from zoneinfo import ZoneInfo
from pathlib import Path
from urllib.parse import urlparse

import httpx
from fastapi import Request, Response
from mcp.server.auth.settings import (
    AuthSettings,
    ClientRegistrationOptions,
    RevocationOptions,
)
from mcp.server.fastmcp import FastMCP
from mcp.server.transport_security import TransportSecuritySettings
from pydantic import AnyHttpUrl
from starlette.requests import Request
from starlette.responses import JSONResponse, PlainTextResponse, RedirectResponse, Response
from harness.mcp.oauth_provider import (
    HarnessOAuthProvider,
    HarnessOAuthSettings,
)
from harness.mcp.tools.source_tools import (
    source_read,
    source_search,
)
from harness.mcp.tools.write_tools import (
    source_write,
)
from harness.mcp.tools.patch_tools import (
    source_delete,
    source_rename,
    source_patch,
)
from harness.mcp.tools.repository_tools import (
    repository_foreign_keys,
    repository_inventory,
    repository_logical_relations,
    table_data,
    table_schema,
)
from harness.mcp.tools.mongodb_tools import (
    mongodb_collection_stats,
    mongodb_create_collection,
    mongodb_documents,
    mongodb_list_collections,
    mongodb_rename_collection,
    mongodb_save_document,
    mongodb_update_document,
    verified_sql,
)
from harness.mcp.tools.backup_tools import (
    database_backup_create,
    database_backup_verify,
    mongodb_backup_collection,
    mongodb_backup_delete,
    mongodb_backup_verify,
    mongodb_delete_backup,
)
from harness.mcp.tools.verified_sql_tools import (
    verified_sql_register,
    verified_sql_execute,
)
from harness.mcp.tools.execution_link_document_tools import mongodb_repair_execution_link_ids
from harness.mcp.tools.mongodb_delete_tool import mongodb_delete_document
from harness.mcp.tools.model_history_audit_ddl_tool import mariadb_ddl_execute
from harness.mcp.tools.identifier_tools import (
    identifier_generate,
)
from harness.mcp.tools.object_lifecycle_tools import (
    object_lifecycle_reconcile,
)
from harness.mcp.tools.repository_table_object_tools import (
    repository_table_object_reconcile,
)
from harness.mcp.tools.git_tools import (
    git_diff,
    git_blame,
    git_log,
    git_status,
)
from harness.mcp.tools.git_mutation_tools import (
    git_add,
    git_commit,
    git_stage_delete,
)
from harness.mcp.tools.operational_tools import (
    operational_service_diagnostics,
)
from harness.mcp.tools.agent_memory_tools import (
    agent_long_term_memory_save,
)
# Source-review implementation belongs to the user-requested haness package.
from haness.mcp.tools.multi_persona_tools import review_python_source
from haness.mcp.tools.orchestrator_tools import run_sps_orchestrator
from harness.mcp.tools.pytest_tools import (
    run_pytest_verification,
)
from harness.mcp.tools.execution_tools import (
    mcp_codex_apps_run_python_source,
)

PROJECT_ROOT = Path("/data/vm_project")
HARNESS_ROOT = PROJECT_ROOT / "harness"
MEMORY_ROOT = HARNESS_ROOT / "memory"
INSTRUCTION_FILE = (
    HARNESS_ROOT
    / "instructions"
    / "SPS_HARNESS_STANDARD.md"
)

OAUTH_SETTINGS = HarnessOAuthSettings.from_environment()
OAUTH_PROVIDER = HarnessOAuthProvider(OAUTH_SETTINGS)
LOGGER = logging.getLogger(__name__)


# Google OAuth responses must return to the callback route below; /mcp is the MCP endpoint.
GOOGLE_CALLBACK_PATH = "/oauth/google/callback"


def _google_callback_uri_matches_route(google_redirect_uri: str) -> bool:
    """Check that the configured Google redirect URI targets this callback route."""
    parsed = urlparse(google_redirect_uri)
    # Exact path matching avoids silently accepting the MCP transport path or a different callback.
    return (
        parsed.scheme == "https"
        and bool(parsed.netloc)
        and parsed.path == GOOGLE_CALLBACK_PATH
        and not parsed.query
        and not parsed.fragment
    )


def _transport_security_settings(
    settings: HarnessOAuthSettings,
) -> TransportSecuritySettings:
    """Allow only the one configured public OAuth authority at the HTTP edge."""
    issuer = urlparse(settings.issuer_url)
    public_authority = issuer.netloc
    google_callback = urlparse(settings.google_redirect_uri)
    configured_authorities = {
        urlparse(settings.resource_url).netloc,
        google_callback.netloc,
    }
    if not public_authority or configured_authorities != {public_authority}:
        raise RuntimeError(
            "SPS MCP OAuth issuer, resource, and Google callback URLs must "
            "use the same public HTTPS authority."
        )
    # Keep MCP available during configuration repair, but make an incorrect callback visible in logs.
    if not _google_callback_uri_matches_route(settings.google_redirect_uri):
        expected_callback_uri = f"{settings.issuer_url.rstrip('/')}{GOOGLE_CALLBACK_PATH}"
        LOGGER.error(
            "Google OAuth redirect URI does not match the callback route. "
            "Register and configure this exact URI: %s",
            expected_callback_uri,
        )
    # return TransportSecuritySettings(
    #     enable_dns_rebinding_protection=True,
    #     allowed_hosts=[public_authority],
    #     allowed_origins=[settings.issuer_url],
    # )
    return TransportSecuritySettings(
        enable_dns_rebinding_protection=True,
        # Gateway 호스트와 실제 백엔드 Host만 허용해 421을 막습니다.
        allowed_hosts=[
            public_authority,
            "subprime-glowworm-mundane.ngrok-free.dev",
            # 로컬 에이전트 요청의 Host에 포트가 붙으므로 명시적으로 허용합니다.
            # 와일드카드는 루프백 주소에만 적용해 외부 Host 제한은 유지합니다.
            "127.0.0.1:*",
            "localhost:*",
            "[::1]:*",
        ],
        allowed_origins=[settings.issuer_url],
    )


mcp = FastMCP(
    name="SPS Harness",
    instructions="""
You are connected to the Story Programming Harness.

Always:
- Follow Repository First.
- Follow Generator First.
- Follow Metadata Driven.
- Treat the Repository as the Single Source of Truth.
- Do not hardcode Repository-managed values.
- Check the current checkpoint before beginning repository work.
- Inspect actual structures and stored data before declaring completion.
- Preserve decisions, migration evidence, and verification results.
""",
    transport_security=_transport_security_settings(OAUTH_SETTINGS),
    auth_server_provider=OAUTH_PROVIDER,
    auth=AuthSettings(
        issuer_url=AnyHttpUrl(OAUTH_SETTINGS.issuer_url),
        resource_server_url=AnyHttpUrl(OAUTH_SETTINGS.resource_url),
        client_registration_options=ClientRegistrationOptions(
            enabled=True,
            valid_scopes=list(OAUTH_SETTINGS.scopes),
            default_scopes=list(OAUTH_SETTINGS.scopes),
        ),
        revocation_options=RevocationOptions(enabled=True),
        required_scopes=list(OAUTH_SETTINGS.scopes),
    ),
)


def _openid_configuration() -> dict[str, object]:
    """Return settings-derived OAuth metadata at the OpenID Discovery alias."""

    issuer_url = OAUTH_SETTINGS.issuer_url.rstrip("/")
    return {
        "issuer": f"{issuer_url}/",
        "authorization_endpoint": f"{issuer_url}/authorize",
        "token_endpoint": f"{issuer_url}/token",
        "registration_endpoint": f"{issuer_url}/register",
        "revocation_endpoint": f"{issuer_url}/revoke",
        "response_types_supported": ["code"],
        "grant_types_supported": ["authorization_code", "refresh_token"],
        "code_challenge_methods_supported": ["S256"],
        "token_endpoint_auth_methods_supported": ["none"],
        "scopes_supported": list(OAUTH_SETTINGS.scopes),
    }

@mcp.custom_route("/.well-known/openid-configuration", methods=["GET"])
async def openid_configuration(_: Request) -> Response:
    """Expose OAuth metadata through the OpenID Discovery compatibility path."""

    return JSONResponse(_openid_configuration())


@mcp.custom_route(GOOGLE_CALLBACK_PATH, methods=["GET"])
async def google_oauth_callback(request: Request) -> Response:
    """Complete Google OIDC and return the MCP authorization code."""

    state = request.query_params.get("state", "")
    if not state:
        return PlainTextResponse("Google OAuth state is required.", status_code=400)

    google_error = request.query_params.get("error")
    if google_error:
        try:
            redirect_uri = await OAUTH_PROVIDER.google_error_redirect(
                state=state,
                error_description="Google login was not completed.",
            )
        except ValueError:
            return PlainTextResponse("Google OAuth state is invalid or expired.", status_code=400)
        return RedirectResponse(redirect_uri, status_code=302)

    google_code = request.query_params.get("code", "")
    if not google_code:
        return PlainTextResponse("Google OAuth code is required.", status_code=400)

    try:
        redirect_uri = await OAUTH_PROVIDER.complete_google_authorization(
            state=state,
            google_code=google_code,
        )
    except PermissionError as error:
        return PlainTextResponse(str(error), status_code=403)
    except (ValueError, httpx.HTTPError) as error:
        LOGGER.warning(
            "Google OAuth verification failed: %s",
            error,
        )
        return PlainTextResponse("Google OAuth verification failed.", status_code=400)
    return RedirectResponse(redirect_uri, status_code=302)


@mcp.tool()
def get_harness_instructions() -> str:
    """Read the official SPS Harness operating standard."""

    if not INSTRUCTION_FILE.exists():
        return "SPS Harness instruction file was not found."

    return INSTRUCTION_FILE.read_text(encoding="utf-8")


def _checkpoint_directory() -> Path:
    """Return the auditable checkpoint directory."""

    return MEMORY_ROOT / "checkpoints"


def _dated_checkpoint_file(now: datetime | None = None) -> Path:
    """Use Korea Standard Time so one workday maps to one checkpoint file."""

    kst_now = now or datetime.now(ZoneInfo("Asia/Seoul"))
    return _checkpoint_directory() / f"current_{kst_now:%Y%m%d}.md"


@mcp.tool()
def get_current_checkpoint() -> str:
    """Return today's checkpoint, or the latest dated checkpoint when needed."""

    checkpoint_dir = _checkpoint_directory()
    dated_files = sorted(checkpoint_dir.glob("current_*.md")) if checkpoint_dir.exists() else []
    checkpoint_file = _dated_checkpoint_file()
    if not checkpoint_file.exists() and dated_files:
        checkpoint_file = dated_files[-1]
    # Read legacy data only until the one-time rename has been completed.
    if not checkpoint_file.exists():
        checkpoint_file = checkpoint_dir / "current.md"
    if not checkpoint_file.exists():
        return "No current checkpoint is registered."
    return checkpoint_file.read_text(encoding="utf-8")


@mcp.tool()
def update_current_checkpoint(
    checkpoint_text: str,
) -> str:
    """Write today's dated checkpoint and prepend an auditable KST write time."""

    checkpoint_file = _dated_checkpoint_file()
    checkpoint_file.parent.mkdir(parents=True, exist_ok=True)
    written_at = datetime.now(ZoneInfo("Asia/Seoul")).isoformat(timespec="seconds")
    # Preserve supplied history and record the time of every accepted write.
    timestamped_text = f"> Checkpoint updated at: {written_at} KST\n\n{checkpoint_text.lstrip()}"
    checkpoint_file.write_text(timestamped_text, encoding="utf-8")
    return checkpoint_file.read_text(encoding="utf-8")


@mcp.tool()
def list_harness_memory() -> str:
    """List auditable SPS Harness memory files."""

    if not MEMORY_ROOT.exists():
        return json.dumps([], ensure_ascii=False)

    files = [
        str(path.relative_to(PROJECT_ROOT))
        for path in MEMORY_ROOT.rglob("*")
        if path.is_file()
    ]

    return json.dumps(
        sorted(files),
        ensure_ascii=False,
        indent=2,
    )


@mcp.tool()
def read_harness_memory(relative_path: str) -> str:
    """Read one file from the SPS Harness memory directory."""

    requested_path = (
        MEMORY_ROOT
        / relative_path
    ).resolve()

    memory_root = MEMORY_ROOT.resolve()

    if memory_root not in requested_path.parents:
        raise ValueError(
            "The requested path is outside Harness memory."
        )

    if not requested_path.exists():
        return "Requested memory file was not found."

    if not requested_path.is_file():
        return "Requested path is not a file."

    return requested_path.read_text(encoding="utf-8")

# ==============================================================================
# /agent/chat 투명 리버스 프록시 라우터
# 목적: 게이트웨이에서 8000번으로 들어온 에이전트 대화 요청을 8012번으로 자동 전달
# 주의: Authorization 헤더(토큰)를 그대로 보존하여 전달합니다.
# ==============================================================================
# @app.api_route("/agent/chat", methods=["POST", "OPTIONS"])
# async def proxy_agent_chat(request: Request):
#     async with httpx.AsyncClient() as client:
#         body = await request.body()
#         headers = dict(request.headers)
#         headers.pop("host", None)
#         headers.pop("content-length", None)
        
#         # 로컬 8012번 LangGraph 에이전트로 토큰과 바디를 그대로 전달
#         resp = await client.request(
#             method=request.method,
#             url="http://127.0.0.1:8012/agent/chat",
#             headers=headers,
#             content=body,
#             timeout=600.0,
#         )
#         return Response(content=resp.content, status_code=resp.status_code, headers=dict(resp.headers))

mcp.tool()(source_search)
mcp.tool()(source_read)
mcp.tool()(source_write)
mcp.tool()(source_patch)
mcp.tool()(source_delete)
mcp.tool()(source_rename)
mcp.tool()(run_pytest_verification)
# Reuse Multi-Persona CLI without embedding it into the general Gemini chat server.
mcp.tool()(review_python_source)
mcp.tool()(run_sps_orchestrator)
mcp.tool(name="mcp_codex_apps_run_python_source")(mcp_codex_apps_run_python_source)
mcp.tool()(agent_long_term_memory_save)

mcp.tool()(table_schema)
mcp.tool()(table_data)
mcp.tool()(repository_inventory)
mcp.tool()(repository_foreign_keys)
mcp.tool()(repository_logical_relations)

mcp.tool()(verified_sql)
mcp.tool()(verified_sql_register)
mcp.tool()(verified_sql_execute)
mcp.tool()(mariadb_ddl_execute)
mcp.tool()(identifier_generate)
mcp.tool()(object_lifecycle_reconcile)
mcp.tool()(repository_table_object_reconcile)
mcp.tool()(mongodb_list_collections)
mcp.tool()(mongodb_create_collection)
mcp.tool()(mongodb_collection_stats)
mcp.tool()(mongodb_documents)
mcp.tool()(mongodb_rename_collection)
mcp.tool()(mongodb_save_document)
mcp.tool()(mongodb_update_document)
# Separate verified-link repair; existing generic update protections remain unchanged.
mcp.tool()(mongodb_repair_execution_link_ids)
mcp.tool()(mongodb_delete_document)
mcp.tool()(database_backup_create)
mcp.tool()(database_backup_verify)
mcp.tool()(mongodb_backup_collection)
mcp.tool()(mongodb_backup_verify)
mcp.tool()(mongodb_backup_delete)
mcp.tool()(mongodb_delete_backup)

mcp.tool()(git_status)
mcp.tool()(git_diff)
# Expose bounded, read-only Git history and line attribution queries.
mcp.tool()(git_log)
mcp.tool()(git_blame)
mcp.tool()(git_add)
mcp.tool()(git_stage_delete)
mcp.tool()(git_commit)

mcp.tool()(operational_service_diagnostics)
# Agent commands are exposed by the existing /agent/chat HTTP API only.


# ==============================================================================
# /agent/chat -> 8012번 LangGraph 에이전트 투명 ASGI 프록시
# 목적: 게이트웨이에서 8000번으로 들어온 요청을 8012번 에이전트로 패스스루
# ==============================================================================
import httpx

class _CombinedMcpHttpApp:
    """Serve Streamable HTTP and the legacy SSE session transport together."""

    def __init__(self, server: FastMCP) -> None:
        self._streamable_app = server.streamable_http_app()
        self._sse_app = server.sse_app()

    async def __call__(self, scope, receive, send) -> None:
        if scope["type"] == "http":
            path = scope.get("path", "")
            
            # [신규 추가] /agent/chat -> 8012번 LangGraph 에이전트로 전달
            if path == "/agent/chat" or path.startswith("/agent/chat"):
                import httpx
                body = bytearray()
                while True:
                    msg = await receive()
                    body.extend(msg.get("body", b""))
                    if not msg.get("more_body", False):
                        break
                req_headers = {k.decode("latin1"): v.decode("latin1") for k, v in scope.get("headers", []) if k.lower() not in (b"host", b"content-length")}
                async with httpx.AsyncClient() as client:
                    resp = await client.request(method=scope["method"], url=f"http://127.0.0.1:8012{path}", headers=req_headers, content=bytes(body), timeout=600.0)
                    res_headers = [(k.encode("latin1"), v.encode("latin1")) for k, v in resp.headers.items() if k.lower() != "content-length"]
                    res_headers.append((b"content-length", str(len(resp.content)).encode("latin1")))
                    await send({"type": "http.response.start", "status": resp.status_code, "headers": res_headers})
                    await send({"type": "http.response.body", "body": resp.content})
                return

            if path == "/sse" or path == "/messages" or path.startswith("/messages/"):
                await self._sse_app(scope, receive, send)
                return
        await self._streamable_app(scope, receive, send)

app = _CombinedMcpHttpApp(mcp)

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=8000, log_level="info")

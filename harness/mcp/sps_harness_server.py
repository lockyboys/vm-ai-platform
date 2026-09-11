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
from __future__ import annotations

import json
import logging
from pathlib import Path
from urllib.parse import urlparse

import httpx
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
from harness.mcp.tools.pytest_tools import (
    run_pytest_verification,
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


def _transport_security_settings(
    settings: HarnessOAuthSettings,
) -> TransportSecuritySettings:
    """Allow only the one configured public OAuth authority at the HTTP edge."""
    issuer = urlparse(settings.issuer_url)
    public_authority = issuer.netloc
    configured_authorities = {
        urlparse(settings.resource_url).netloc,
        urlparse(settings.google_redirect_uri).netloc,
    }
    if not public_authority or configured_authorities != {public_authority}:
        raise RuntimeError(
            "SPS MCP OAuth issuer, resource, and Google callback URLs must "
            "use the same public HTTPS authority."
        )
    return TransportSecuritySettings(
        enable_dns_rebinding_protection=True,
        allowed_hosts=[public_authority],
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


@mcp.custom_route("/oauth/google/callback", methods=["GET"])
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


@mcp.tool()
def get_current_checkpoint() -> str:
    """Return the current SPS implementation checkpoint."""

    checkpoint_file = (
        MEMORY_ROOT
        / "checkpoints"
        / "current.md"
    )

    if not checkpoint_file.exists():
        return "No current checkpoint is registered."

    return checkpoint_file.read_text(encoding="utf-8")

@mcp.tool()
def update_current_checkpoint(
    checkpoint_text: str,
) -> str:
    """
    Update the current SPS implementation checkpoint.
    """

    checkpoint_file = (
        MEMORY_ROOT
        / "checkpoints"
        / "current.md"
    )

    checkpoint_file.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    checkpoint_file.write_text(
        checkpoint_text,
        encoding="utf-8",
    )

    # return (
    #     "Current checkpoint updated successfully."
    # )

    return checkpoint_file.read_text(
        encoding="utf-8"
    )

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

mcp.tool()(source_search)
mcp.tool()(source_read)
mcp.tool()(source_write)
mcp.tool()(source_patch)
mcp.tool()(source_delete)
mcp.tool()(source_rename)
mcp.tool()(run_pytest_verification)

mcp.tool()(table_schema)
mcp.tool()(table_data)
mcp.tool()(repository_inventory)
mcp.tool()(repository_foreign_keys)
mcp.tool()(repository_logical_relations)

mcp.tool()(verified_sql)
mcp.tool()(verified_sql_register)
mcp.tool()(verified_sql_execute)
mcp.tool()(identifier_generate)
mcp.tool()(object_lifecycle_reconcile)
mcp.tool()(repository_table_object_reconcile)
mcp.tool()(mongodb_list_collections)
mcp.tool()(mongodb_collection_stats)
mcp.tool()(mongodb_documents)
mcp.tool()(mongodb_rename_collection)
mcp.tool()(mongodb_save_document)
mcp.tool()(mongodb_update_document)
mcp.tool()(database_backup_create)
mcp.tool()(database_backup_verify)
mcp.tool()(mongodb_backup_collection)
mcp.tool()(mongodb_backup_verify)
mcp.tool()(mongodb_backup_delete)
mcp.tool()(mongodb_delete_backup)

mcp.tool()(git_status)
mcp.tool()(git_diff)
mcp.tool()(git_add)
mcp.tool()(git_stage_delete)
mcp.tool()(git_commit)

mcp.tool()(operational_service_diagnostics)

if __name__ == "__main__":
    mcp.run(transport="streamable-http")

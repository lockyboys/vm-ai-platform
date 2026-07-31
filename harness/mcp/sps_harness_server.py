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
from starlette.responses import PlainTextResponse, RedirectResponse, Response
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
    mongodb_collections,
    mongodb_documents,
    mongodb_save_document,
    verified_sql,
)
from harness.mcp.tools.verified_sql_tools import (
    verified_sql_execute,
)
from harness.mcp.tools.git_tools import (
    git_diff,
    git_status,
)
from harness.mcp.tools.git_mutation_tools import (
    git_add,
    git_commit,
)
from harness.mcp.tools.operational_tools import (
    operational_service_diagnostics,
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

mcp.tool()(table_schema)
mcp.tool()(table_data)
mcp.tool()(repository_inventory)
mcp.tool()(repository_foreign_keys)
mcp.tool()(repository_logical_relations)

mcp.tool()(verified_sql)
mcp.tool()(verified_sql_execute)
mcp.tool()(mongodb_collections)
mcp.tool()(mongodb_documents)
mcp.tool()(mongodb_save_document)

mcp.tool()(git_status)
mcp.tool()(git_diff)
mcp.tool()(git_add)
mcp.tool()(git_commit)

mcp.tool()(operational_service_diagnostics)

if __name__ == "__main__":
    mcp.run(transport="streamable-http")

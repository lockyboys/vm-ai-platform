"""Expose the local SPS Gemini Agent through an authenticated MCP tool."""

from __future__ import annotations

import os
from urllib.parse import urlsplit

import httpx

from common.auth import CommonAuth


MAX_AGENT_INPUT_CHARS = 20_000
DEFAULT_AGENT_TIMEOUT_SECONDS = 600


def _agent_endpoint() -> str:
    """Resolve only loopback Agent URLs so this tool cannot become an SSRF proxy."""
    base_url = os.getenv("SPS_GEMINI_AGENT_URL", "http://127.0.0.1:8012").rstrip("/")
    parsed = urlsplit(base_url)

    # Agent traffic stays on this host; public tunnels and arbitrary URLs are rejected.
    if (
        parsed.scheme != "http"
        or parsed.hostname not in {"127.0.0.1", "localhost", "::1"}
        or parsed.username
        or parsed.password
        or parsed.path not in {"", "/"}
        or parsed.query
        or parsed.fragment
    ):
        raise RuntimeError(
            "SPS_GEMINI_AGENT_URL must be a loopback HTTP URL such as "
            "http://127.0.0.1:8012."
        )
    return f"{base_url}/agent/chat"


def _service_subject() -> str:
    """Choose an explicit service identity or a sole configured allowed subject."""
    configured = os.getenv("SPS_MCP_AGENT_SUBJECT_ID", "").strip()
    allowed = [
        value.strip()
        for value in os.getenv("SPS_MCP_COMMON_AUTH_ALLOWED_SUBJECTS", "").split(",")
        if value.strip()
    ]

    # An explicit subject must also be in the configured allowlist when one exists.
    if configured:
        if allowed and configured not in allowed:
            raise RuntimeError(
                "SPS_MCP_AGENT_SUBJECT_ID is not in "
                "SPS_MCP_COMMON_AUTH_ALLOWED_SUBJECTS."
            )
        return configured

    # Avoid silently choosing an identity when the service allowlist is ambiguous.
    if len(allowed) == 1:
        return allowed[0]
    raise RuntimeError(
        "Set SPS_MCP_AGENT_SUBJECT_ID or configure exactly one "
        "SPS_MCP_COMMON_AUTH_ALLOWED_SUBJECTS entry."
    )


def _agent_timeout_seconds() -> float:
    """Read a bounded timeout; malformed or excessive values fail closed."""
    raw = os.getenv("SPS_GEMINI_AGENT_TIMEOUT_SECONDS", str(DEFAULT_AGENT_TIMEOUT_SECONDS))
    try:
        timeout = float(raw)
    except ValueError as error:
        raise RuntimeError("SPS_GEMINI_AGENT_TIMEOUT_SECONDS must be numeric.") from error
    if not 1 <= timeout <= DEFAULT_AGENT_TIMEOUT_SECONDS:
        raise RuntimeError(
            f"SPS_GEMINI_AGENT_TIMEOUT_SECONDS must be between 1 and "
            f"{DEFAULT_AGENT_TIMEOUT_SECONDS}."
        )
    return timeout


async def sps_gemini_agent_chat(user_input: str) -> str:
    """Run a user request through the local Gemini Agent and return its answer.

    The agent has its configured tools, including Gmail read/send. Use this tool
    only for the user's requested task; requests may trigger external actions
    such as sending mail. The service-to-service bearer is short-lived, minted
    from protected CommonAuth environment settings, and never logged or returned.
    """
    # Reject malformed and oversized prompts before issuing a token or making I/O.
    prompt = user_input.strip()
    if not prompt:
        raise ValueError("user_input must not be empty.")
    if len(prompt) > MAX_AGENT_INPUT_CHARS:
        raise ValueError(
            f"user_input exceeds the {MAX_AGENT_INPUT_CHARS}-character limit."
        )

    # A local-only endpoint prevents arbitrary network access through the MCP tool.
    endpoint = _agent_endpoint()
    token = CommonAuth().issue_access_token(_service_subject())

    try:
        # trust_env=False prevents proxy environment variables from intercepting
        # loopback traffic; the short connect timeout distinguishes service-down cases.
        timeout = httpx.Timeout(_agent_timeout_seconds(), connect=5.0)
        async with httpx.AsyncClient(timeout=timeout, trust_env=False) as client:
            response = await client.post(
                endpoint,
                json={"user_input": prompt},
                headers={"Authorization": f"Bearer {token}"},
            )
        response.raise_for_status()
    except httpx.TimeoutException:
        raise RuntimeError("SPS Gemini Agent request timed out.") from None
    except httpx.HTTPStatusError as error:
        raise RuntimeError(
            f"SPS Gemini Agent returned HTTP {error.response.status_code}."
        ) from None
    except httpx.RequestError:
        raise RuntimeError("SPS Gemini Agent is unavailable on the configured loopback URL.") from None
    finally:
        # Drop the local reference after the request; never include token in diagnostics.
        token = ""

    try:
        result = response.json().get("result")
    except (ValueError, AttributeError):
        raise RuntimeError("SPS Gemini Agent returned an invalid JSON response.") from None
    if not isinstance(result, str) or not result.strip():
        raise RuntimeError("SPS Gemini Agent response did not include a text result.")
    return result

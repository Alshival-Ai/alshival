from __future__ import annotations

import os
from typing import Any, Optional

from .client import get_config

DEFAULT_MCP_URL = "https://mcp.alshival.ai/mcp/"
DEFAULT_GITHUB_MCP_URL = "https://mcp.alshival.ai/github/"


def _clean(value: Optional[str]) -> str:
    return str(value or "").strip()


def _pick(*values: Optional[str]) -> str:
    for value in values:
        cleaned = _clean(value)
        if cleaned:
            return cleaned
    return ""


def _resolved_identity(
    *,
    api_key: Optional[str] = None,
    username: Optional[str] = None,
    email: Optional[str] = None,
) -> tuple[str, str, str]:
    cfg = get_config()
    resolved_api_key = _pick(api_key, cfg.api_key, os.getenv("ALSHIVAL_API_KEY"))
    resolved_username = _pick(username, cfg.username, os.getenv("ALSHIVAL_USERNAME"))
    resolved_email = _pick(email, cfg.email, os.getenv("ALSHIVAL_EMAIL"))
    return resolved_api_key, resolved_username, resolved_email


def _resolved_require_approval(value: Optional[str]) -> str:
    return _pick(value, os.getenv("ALSHIVAL_MCP_REQUIRE_APPROVAL"), "never")


def _build_headers(
    *,
    api_key: str,
    username: str,
    email: str,
    include_accept: bool = True,
) -> dict[str, str]:
    headers: dict[str, str] = {}
    api_key_header = _pick(os.getenv("ALSHIVAL_MCP_API_KEY_HEADER"), "x-api-key")
    username_header = _pick(os.getenv("ALSHIVAL_MCP_USERNAME_HEADER"), "x-user-username")
    email_header = _pick(os.getenv("ALSHIVAL_MCP_EMAIL_HEADER"), "x-user-email")
    if api_key:
        headers[api_key_header] = api_key
    if username:
        headers[username_header] = username
    elif email:
        headers[email_header] = email
    if include_accept:
        headers["accept"] = "application/json, text/event-stream"
    return headers


def _build_tool(
    *,
    server_label: str,
    server_url: str,
    api_key: Optional[str] = None,
    username: Optional[str] = None,
    email: Optional[str] = None,
    require_approval: Optional[str] = None,
) -> dict[str, Any]:
    resolved_api_key, resolved_username, resolved_email = _resolved_identity(
        api_key=api_key,
        username=username,
        email=email,
    )
    return {
        "type": "mcp",
        "server_label": server_label,
        "server_url": _clean(server_url),
        "require_approval": _resolved_require_approval(require_approval),
        "headers": _build_headers(
            api_key=resolved_api_key,
            username=resolved_username,
            email=resolved_email,
        ),
    }


def mcp_tool(
    *,
    server_url: Optional[str] = None,
    api_key: Optional[str] = None,
    username: Optional[str] = None,
    email: Optional[str] = None,
    require_approval: Optional[str] = None,
) -> dict[str, Any]:
    return _build_tool(
        server_label="alshival-mcp",
        server_url=_pick(server_url, os.getenv("ALSHIVAL_MCP_URL"), DEFAULT_MCP_URL),
        api_key=api_key,
        username=username,
        email=email,
        require_approval=require_approval,
    )


def github_mcp_tool(
    *,
    server_url: Optional[str] = None,
    api_key: Optional[str] = None,
    username: Optional[str] = None,
    email: Optional[str] = None,
    require_approval: Optional[str] = None,
) -> dict[str, Any]:
    return _build_tool(
        server_label="github-mcp",
        server_url=_pick(server_url, os.getenv("ALSHIVAL_GITHUB_MCP_URL"), DEFAULT_GITHUB_MCP_URL),
        api_key=api_key,
        username=username,
        email=email,
        require_approval=require_approval,
    )


class MCPToolSpec(dict):
    """Dict-like MCP tool spec with convenient access to the GitHub tool spec."""

    def __init__(self) -> None:
        super().__init__()
        self.refresh()

    @property
    def github(self) -> dict[str, Any]:
        return github_mcp_tool()

    def refresh(self) -> "MCPToolSpec":
        self.clear()
        self.update(mcp_tool())
        return self


mcp = MCPToolSpec()


def refresh_mcp() -> MCPToolSpec:
    return mcp.refresh()


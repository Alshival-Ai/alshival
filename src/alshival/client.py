from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from typing import Optional, Union
from urllib.parse import quote, unquote, urlsplit

ALERT_LEVEL = 45


@dataclass
class ClientConfig:
    username: Optional[str] = None
    email: Optional[str] = None
    # Optional owner username for shared-resource logging paths.
    # When set, logs post to /u/<resource_owner_username>/... while auth stays tied to username/email.
    resource_owner_username: Optional[str] = None
    api_key: Optional[str] = None
    base_url: str = "https://alshival.ai"
    # Optional explicit DevTools portal prefix (for example "/DevTools" or "").
    portal_prefix: Optional[str] = None
    resource_id: Optional[str] = None
    enabled: bool = True
    # Minimum stdlib logging level to forward to Alshival Cloud Logs.
    cloud_level: int = logging.INFO
    timeout_seconds: int = 5
    verify_ssl: bool = True
    # When True, emit SDK transport/config diagnostics to stderr (never raises).
    debug: bool = False


@dataclass
class ParsedResourceRef:
    base_url: str
    portal_prefix: str
    resource_owner_username: str
    resource_id: str


def _env_bool(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "t", "yes", "y", "on"}


def _normalize_portal_prefix(value: Optional[str]) -> Optional[str]:
    if value is None:
        return None
    raw = str(value).strip()
    if not raw:
        return ""
    cleaned = "/" + raw.strip("/")
    return "" if cleaned == "/" else cleaned


def _coerce_level(level: Union[int, str]) -> int:
    if isinstance(level, int):
        return level
    name = level.strip().upper()
    mapping = {
        "ALERT": ALERT_LEVEL,
        "CRITICAL": logging.CRITICAL,
        "FATAL": logging.CRITICAL,
        "ERROR": logging.ERROR,
        "WARNING": logging.WARNING,
        "WARN": logging.WARNING,
        "INFO": logging.INFO,
        "DEBUG": logging.DEBUG,
        "NOTSET": logging.NOTSET,
    }
    if name in mapping:
        return mapping[name]
    raise ValueError(f"Invalid log level: {level!r}")


def _env_level(name: str, default: int) -> int:
    value = os.getenv(name)
    if value is None or value.strip() == "":
        return default
    try:
        return _coerce_level(value)
    except ValueError:
        # Fail-safe: never crash on bad env var.
        return default


def _parse_resource_reference(resource: Optional[str]) -> Optional[ParsedResourceRef]:
    if resource is None:
        return None
    raw = str(resource).strip()
    if not raw:
        return None
    parsed = urlsplit(raw)
    if not parsed.scheme or not parsed.netloc:
        return None
    segments = [segment for segment in parsed.path.split("/") if segment]
    if segments and segments[-1].strip().lower() == "logs":
        segments = segments[:-1]
    owner = ""
    resource_id = ""
    prefix_segments: list[str] = []
    for index in range(max(0, len(segments) - 3)):
        if segments[index] == "u" and segments[index + 2] == "resources":
            owner = unquote(segments[index + 1]).strip()
            resource_id = unquote(segments[index + 3]).strip()
            prefix_segments = segments[:index]
            break
    if not owner or not resource_id:
        return None
    portal_prefix = "/" + "/".join(prefix_segments) if prefix_segments else ""
    if portal_prefix == "/":
        portal_prefix = ""
    return ParsedResourceRef(
        base_url=f"{parsed.scheme}://{parsed.netloc}".rstrip("/"),
        portal_prefix=portal_prefix,
        resource_owner_username=owner,
        resource_id=resource_id,
    )


_resource_env = _parse_resource_reference(os.getenv("ALSHIVAL_RESOURCE") or os.getenv("ALSHIVAL_RESOURCE_URL"))
_base_url_env = (
    os.getenv("ALSHIVAL_BASE_URL")
    or (_resource_env.base_url if _resource_env else None)
    or "https://alshival.ai"
)
_portal_prefix_env = _normalize_portal_prefix(os.getenv("ALSHIVAL_PORTAL_PREFIX"))

_config = ClientConfig(
    username=os.getenv("ALSHIVAL_USERNAME"),
    email=os.getenv("ALSHIVAL_EMAIL"),
    resource_owner_username=(
        os.getenv("ALSHIVAL_RESOURCE_OWNER_USERNAME")
        or (_resource_env.resource_owner_username if _resource_env else None)
    ),
    api_key=os.getenv("ALSHIVAL_API_KEY"),
    base_url=str(_base_url_env).rstrip("/"),
    portal_prefix=_portal_prefix_env if _portal_prefix_env is not None else (_resource_env.portal_prefix if _resource_env else None),
    resource_id=os.getenv("ALSHIVAL_RESOURCE_ID") or (_resource_env.resource_id if _resource_env else None),
    cloud_level=_env_level("ALSHIVAL_CLOUD_LEVEL", logging.INFO),
    debug=_env_bool("ALSHIVAL_DEBUG", False),
)


def configure(
    *,
    username: Optional[str] = None,
    email: Optional[str] = None,
    resource: Optional[str] = None,
    resource_owner_username: Optional[str] = None,
    api_key: Optional[str] = None,
    base_url: Optional[str] = None,
    portal_prefix: Optional[str] = None,
    resource_id: Optional[str] = None,
    enabled: Optional[bool] = None,
    cloud_level: Optional[Union[int, str]] = None,
    timeout_seconds: Optional[int] = None,
    verify_ssl: Optional[bool] = None,
    debug: Optional[bool] = None,
) -> None:
    parsed_resource = _parse_resource_reference(resource) if resource is not None else None
    if parsed_resource is not None:
        if base_url is None:
            base_url = parsed_resource.base_url
        if portal_prefix is None:
            portal_prefix = parsed_resource.portal_prefix
        if resource_owner_username is None:
            resource_owner_username = parsed_resource.resource_owner_username
        if resource_id is None:
            resource_id = parsed_resource.resource_id

    if username is not None:
        _config.username = username
    if email is not None:
        _config.email = email
    if resource_owner_username is not None:
        _config.resource_owner_username = resource_owner_username
    if api_key is not None:
        _config.api_key = api_key
    if base_url is not None:
        _config.base_url = base_url.rstrip("/")
    if portal_prefix is not None:
        _config.portal_prefix = _normalize_portal_prefix(portal_prefix)
    if resource_id is not None:
        _config.resource_id = resource_id
    if enabled is not None:
        _config.enabled = enabled
    if cloud_level is not None:
        _config.cloud_level = _coerce_level(cloud_level)
    if timeout_seconds is not None:
        _config.timeout_seconds = timeout_seconds
    if verify_ssl is not None:
        _config.verify_ssl = verify_ssl
    if debug is not None:
        _config.debug = debug
    try:
        # Keep exported MCP tool specs in sync with latest credentials/config.
        from .mcp_tools import refresh_mcp  # noqa: PLC0415

        refresh_mcp()
    except Exception:
        # Fail-safe: configuration should never raise due to optional helpers.
        return


def _resolved_portal_prefix() -> str:
    cfg = get_config()
    if cfg.portal_prefix is not None:
        return cfg.portal_prefix

    parsed = urlsplit(cfg.base_url)
    path_prefix = _normalize_portal_prefix(parsed.path)
    if path_prefix:
        return path_prefix

    host = (parsed.hostname or "").strip().lower()
    if host in {"alshival.ai", "www.alshival.ai"}:
        # Legacy main-site host still serves DevTools under /DevTools/.
        return "/DevTools"
    return ""


def build_resource_logs_endpoint(username: str, resource_id: str) -> str:
    cfg = get_config()
    parsed = urlsplit(cfg.base_url)
    scheme = parsed.scheme or "https"
    netloc = parsed.netloc or parsed.path
    if not netloc:
        netloc = "alshival.ai"
    base = f"{scheme}://{netloc}"
    portal_prefix = _resolved_portal_prefix()
    safe_user = quote(str(username or "").strip(), safe="")
    safe_resource = quote(str(resource_id or "").strip(), safe="")
    return f"{base}{portal_prefix}/u/{safe_user}/resources/{safe_resource}/logs/"


def set_enabled(enabled: bool) -> None:
    _config.enabled = enabled


def get_config() -> ClientConfig:
    return _config

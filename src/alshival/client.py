from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from typing import Optional
from urllib.parse import quote, unquote, urlsplit

ALERT_LEVEL = 45


@dataclass
class ClientConfig:
    username: Optional[str] = None
    # Derived from `resource` URL for compatibility with older integrations.
    resource_owner_username: Optional[str] = None
    # Derived from `resource` URL.
    resource_route_kind: Optional[str] = None
    resource_route_value: Optional[str] = None
    # Derived from `resource` URL. Example: "/team/devops/resources".
    resource_logs_prefix: Optional[str] = None
    api_key: Optional[str] = None
    base_url: str = "https://alshival.dev"
    # Optional explicit DevTools portal prefix (for example "/DevTools" or "").
    portal_prefix: Optional[str] = None
    # Derived from `resource` URL.
    resource_id: Optional[str] = None
    enabled: bool = True
    # Minimum stdlib logging level to forward to Alshival Cloud Logs.
    # Set to None to disable cloud forwarding.
    cloud_level: Optional[int] = logging.INFO
    timeout_seconds: int = 5
    verify_ssl: bool = True
    # When True, emit SDK transport/config diagnostics to stderr (never raises).
    debug: bool = False


@dataclass
class ParsedResourceRef:
    base_url: str
    portal_prefix: str
    resource_route_kind: str
    resource_route_value: str
    resource_logs_prefix: str
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


def _coerce_level(level: str) -> Optional[int]:
    if not isinstance(level, str):
        raise ValueError(f"Invalid log level: {level!r}")
    name = level.strip().upper()
    if name == "NONE":
        return None
    mapping = {
        "ALERT": ALERT_LEVEL,
        "ERROR": logging.ERROR,
        "WARNING": logging.WARNING,
        "INFO": logging.INFO,
        "DEBUG": logging.DEBUG,
    }
    if name in mapping:
        return mapping[name]
    raise ValueError(f"Invalid log level: {level!r}")


def _env_level(name: str, default: Optional[int]) -> Optional[int]:
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
    route_kind = ""
    route_value = ""
    resource_logs_prefix = ""
    resource_id = ""
    prefix_segments: list[str] = []
    for index, segment in enumerate(segments):
        if segment.strip().lower() == "resources" and (index + 1) < len(segments):
            resource_id = unquote(segments[index + 1]).strip()
            if not resource_id:
                return None
            resource_logs_prefix = "/" + "/".join(segments[: index + 1])
            if resource_logs_prefix == "/":
                resource_logs_prefix = ""
            prefix_segments = segments[:index]
            if index >= 2:
                possible_kind = segments[index - 2].strip().lower()
                possible_value = unquote(segments[index - 1]).strip()
                if possible_kind in {"u", "team"} and possible_value:
                    route_kind = possible_kind
                    route_value = possible_value
                    prefix_segments = segments[: index - 2]
            break
    if not resource_logs_prefix or not resource_id:
        return None
    portal_prefix = "/" + "/".join(prefix_segments) if prefix_segments else ""
    if portal_prefix == "/":
        portal_prefix = ""
    return ParsedResourceRef(
        base_url=f"{parsed.scheme}://{parsed.netloc}".rstrip("/"),
        portal_prefix=portal_prefix,
        resource_route_kind=route_kind,
        resource_route_value=route_value,
        resource_logs_prefix=resource_logs_prefix,
        resource_owner_username=route_value,
        resource_id=resource_id,
    )


def build_client_config_from_env() -> ClientConfig:
    resource_env = _parse_resource_reference(os.getenv("ALSHIVAL_RESOURCE") or os.getenv("ALSHIVAL_RESOURCE_URL"))
    debug_env = _env_bool("ALSHIVAL_DEBUG", False)
    default_cloud_level = logging.DEBUG if debug_env else logging.INFO

    if resource_env is not None:
        # Resource URL is authoritative for routing. This avoids mixed-domain mismatches
        # (for example `ALSHIVAL_BASE_URL=alshival.ai` + `ALSHIVAL_RESOURCE=alshival.dev/u/...`).
        base_url = resource_env.base_url
        portal_prefix = resource_env.portal_prefix
    else:
        base_url = os.getenv("ALSHIVAL_BASE_URL") or "https://alshival.dev"
        portal_prefix = _normalize_portal_prefix(os.getenv("ALSHIVAL_PORTAL_PREFIX"))

    return ClientConfig(
        username=os.getenv("ALSHIVAL_USERNAME"),
        resource_route_kind=(resource_env.resource_route_kind if resource_env else None),
        resource_route_value=(resource_env.resource_route_value if resource_env else None),
        resource_logs_prefix=(resource_env.resource_logs_prefix if resource_env else None),
        resource_owner_username=(resource_env.resource_owner_username if resource_env else None),
        api_key=os.getenv("ALSHIVAL_API_KEY"),
        base_url=str(base_url).rstrip("/"),
        portal_prefix=portal_prefix,
        resource_id=(resource_env.resource_id if resource_env else None),
        cloud_level=_env_level("ALSHIVAL_CLOUD_LEVEL", default_cloud_level),
        debug=debug_env,
    )


_config = build_client_config_from_env()


def configure(
    *,
    username: Optional[str] = None,
    resource: Optional[str] = None,
    api_key: Optional[str] = None,
    base_url: Optional[str] = None,
    portal_prefix: Optional[str] = None,
    enabled: Optional[bool] = None,
    cloud_level: Optional[str] = None,
    timeout_seconds: Optional[int] = None,
    verify_ssl: Optional[bool] = None,
    debug: Optional[bool] = None,
) -> None:
    if resource is not None:
        parsed_resource = _parse_resource_reference(resource)
        if parsed_resource is not None:
            if base_url is None:
                base_url = parsed_resource.base_url
            if portal_prefix is None:
                portal_prefix = parsed_resource.portal_prefix
            _config.resource_route_kind = parsed_resource.resource_route_kind
            _config.resource_route_value = parsed_resource.resource_route_value
            _config.resource_logs_prefix = parsed_resource.resource_logs_prefix
            _config.resource_owner_username = parsed_resource.resource_owner_username
            _config.resource_id = parsed_resource.resource_id
        else:
            _config.resource_route_kind = None
            _config.resource_route_value = None
            _config.resource_logs_prefix = None
            _config.resource_owner_username = None
            _config.resource_id = None

    if username is not None:
        _config.username = username
    if api_key is not None:
        _config.api_key = api_key
    if base_url is not None:
        _config.base_url = base_url.rstrip("/")
    if portal_prefix is not None:
        _config.portal_prefix = _normalize_portal_prefix(portal_prefix)
    if enabled is not None:
        _config.enabled = enabled
    if cloud_level is not None:
        _config.cloud_level = _coerce_level(cloud_level)
    elif debug is True and _config.cloud_level is not None:
        # In SDK debug mode, prefer forwarding debug-level events unless caller explicitly sets cloud_level.
        _config.cloud_level = logging.DEBUG
    if timeout_seconds is not None:
        _config.timeout_seconds = timeout_seconds
    if verify_ssl is not None:
        _config.verify_ssl = verify_ssl
    if debug is not None:
        _config.debug = debug
    try:
        from .logger import refresh_debug_console_handler  # noqa: PLC0415

        refresh_debug_console_handler()
    except Exception:
        # Fail-safe: configuration should never raise due to optional helpers.
        pass
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


def build_resource_logs_endpoint(username: str, resource_id: str, *, route_kind: str = "u") -> str:
    cfg = get_config()
    parsed = urlsplit(cfg.base_url)
    scheme = parsed.scheme or "https"
    netloc = parsed.netloc or parsed.path
    if not netloc:
        netloc = "alshival.dev"
    base = f"{scheme}://{netloc}"
    portal_prefix = _resolved_portal_prefix()
    resolved_route_kind = str(route_kind or "").strip().lower()
    if resolved_route_kind not in {"u", "team"}:
        resolved_route_kind = "u"
    safe_user = quote(str(username or "").strip(), safe="")
    safe_resource = quote(str(resource_id or "").strip(), safe="")
    resource_logs_prefix = str(cfg.resource_logs_prefix or "").strip()
    if resource_logs_prefix:
        cleaned_prefix = "/" + resource_logs_prefix.strip("/")
        return f"{base}{cleaned_prefix}/{safe_resource}/logs/"
    return f"{base}{portal_prefix}/{resolved_route_kind}/{safe_user}/resources/{safe_resource}/logs/"


def set_enabled(enabled: bool) -> None:
    _config.enabled = enabled


def get_config() -> ClientConfig:
    return _config

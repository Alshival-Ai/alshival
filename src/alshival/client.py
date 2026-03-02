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
    # Derived from `resource` URL.
    resource_base_url: Optional[str] = None
    # Derived from `resource` URL. Example: "/team/devops/resources" or "/u/alice/resources".
    resource_logs_prefix: Optional[str] = None
    api_key: Optional[str] = None
    # Derived from `resource` URL.
    resource_id: Optional[str] = None
    enabled: bool = True
    # Minimum stdlib logging level to forward to Alshival Cloud Logs.
    # Set to None to disable cloud forwarding.
    cloud_level: Optional[int] = logging.INFO
    timeout_seconds: int = 5
    verify_ssl: bool = True


@dataclass
class ParsedResourceRef:
    resource_base_url: str
    resource_logs_prefix: str
    resource_id: str


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
    resource_logs_prefix = ""
    resource_id = ""
    for index, segment in enumerate(segments):
        if segment.strip().lower() == "resources" and (index + 1) < len(segments):
            resource_id = unquote(segments[index + 1]).strip()
            if not resource_id:
                return None
            resource_logs_prefix = "/" + "/".join(segments[: index + 1])
            if resource_logs_prefix == "/":
                resource_logs_prefix = ""
            break
    if not resource_logs_prefix or not resource_id:
        return None
    return ParsedResourceRef(
        resource_base_url=f"{parsed.scheme}://{parsed.netloc}".rstrip("/"),
        resource_logs_prefix=resource_logs_prefix,
        resource_id=resource_id,
    )


def build_client_config_from_env() -> ClientConfig:
    resource_env = _parse_resource_reference(os.getenv("ALSHIVAL_RESOURCE") or os.getenv("ALSHIVAL_RESOURCE_URL"))
    default_cloud_level = logging.INFO

    if resource_env is not None:
        resource_base_url = resource_env.resource_base_url
        resource_logs_prefix = resource_env.resource_logs_prefix
        resource_id = resource_env.resource_id
    else:
        resource_base_url = None
        resource_logs_prefix = None
        resource_id = None

    return ClientConfig(
        username=os.getenv("ALSHIVAL_USERNAME"),
        resource_base_url=resource_base_url,
        resource_logs_prefix=resource_logs_prefix,
        api_key=os.getenv("ALSHIVAL_API_KEY"),
        resource_id=resource_id,
        cloud_level=_env_level("ALSHIVAL_CLOUD_LEVEL", default_cloud_level),
    )


_config = build_client_config_from_env()


def configure(
    *,
    username: Optional[str] = None,
    resource: Optional[str] = None,
    api_key: Optional[str] = None,
    enabled: Optional[bool] = None,
    cloud_level: Optional[str] = None,
    timeout_seconds: Optional[int] = None,
    verify_ssl: Optional[bool] = None,
) -> None:
    if resource is not None:
        parsed_resource = _parse_resource_reference(resource)
        if parsed_resource is not None:
            _config.resource_base_url = parsed_resource.resource_base_url
            _config.resource_logs_prefix = parsed_resource.resource_logs_prefix
            _config.resource_id = parsed_resource.resource_id
        else:
            _config.resource_base_url = None
            _config.resource_logs_prefix = None
            _config.resource_id = None

    if username is not None:
        _config.username = username
    if api_key is not None:
        _config.api_key = api_key
    if enabled is not None:
        _config.enabled = enabled
    if cloud_level is not None:
        _config.cloud_level = _coerce_level(cloud_level)
    if timeout_seconds is not None:
        _config.timeout_seconds = timeout_seconds
    if verify_ssl is not None:
        _config.verify_ssl = verify_ssl
def build_resource_logs_endpoint(resource_id: str) -> str:
    cfg = get_config()
    base = str(cfg.resource_base_url or "").strip().rstrip("/")
    safe_resource = quote(str(resource_id or "").strip(), safe="")
    resource_logs_prefix = str(cfg.resource_logs_prefix or "").strip()
    if not base or not resource_logs_prefix:
        return ""
    cleaned_prefix = "/" + resource_logs_prefix.strip("/")
    return f"{base}{cleaned_prefix}/{safe_resource}/logs/"


def set_enabled(enabled: bool) -> None:
    _config.enabled = enabled


def get_config() -> ClientConfig:
    return _config

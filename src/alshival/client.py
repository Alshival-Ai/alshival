from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from typing import Optional, Union

ALERT_LEVEL = 45


@dataclass
class ClientConfig:
    username: Optional[str] = None
    api_key: Optional[str] = None
    base_url: str = "https://alshival.ai"
    resource_id: Optional[str] = None
    enabled: bool = True
    # Minimum stdlib logging level to forward to Alshival Cloud Logs.
    cloud_level: int = logging.INFO
    timeout_seconds: int = 5
    verify_ssl: bool = True
    # When True, emit SDK transport/config diagnostics to stderr (never raises).
    debug: bool = False


def _env_bool(name: str, default: bool = False) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "t", "yes", "y", "on"}


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


_config = ClientConfig(
    username=os.getenv("ALSHIVAL_USERNAME"),
    api_key=os.getenv("ALSHIVAL_API_KEY"),
    base_url=os.getenv("ALSHIVAL_BASE_URL", "https://alshival.ai").rstrip("/"),
    resource_id=os.getenv("ALSHIVAL_RESOURCE_ID"),
    cloud_level=_env_level("ALSHIVAL_CLOUD_LEVEL", logging.INFO),
    debug=_env_bool("ALSHIVAL_DEBUG", False),
)


def configure(
    *,
    username: Optional[str] = None,
    api_key: Optional[str] = None,
    base_url: Optional[str] = None,
    resource_id: Optional[str] = None,
    enabled: Optional[bool] = None,
    cloud_level: Optional[Union[int, str]] = None,
    timeout_seconds: Optional[int] = None,
    verify_ssl: Optional[bool] = None,
    debug: Optional[bool] = None,
) -> None:
    if username is not None:
        _config.username = username
    if api_key is not None:
        _config.api_key = api_key
    if base_url is not None:
        _config.base_url = base_url.rstrip("/")
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


def set_enabled(enabled: bool) -> None:
    _config.enabled = enabled


def get_config() -> ClientConfig:
    return _config

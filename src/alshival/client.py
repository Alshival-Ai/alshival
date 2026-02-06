from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Optional


@dataclass
class ClientConfig:
    username: Optional[str] = None
    api_key: Optional[str] = None
    base_url: str = "https://alshival.ai"
    enabled: bool = True
    timeout_seconds: int = 5


_config = ClientConfig(
    username=os.getenv("ALSHIVAL_USERNAME"),
    api_key=os.getenv("ALSHIVAL_API_KEY"),
    base_url=os.getenv("ALSHIVAL_BASE_URL", "https://alshival.ai"),
)


def configure(
    *,
    username: Optional[str] = None,
    api_key: Optional[str] = None,
    base_url: Optional[str] = None,
    enabled: Optional[bool] = None,
    timeout_seconds: Optional[int] = None,
) -> None:
    if username is not None:
        _config.username = username
    if api_key is not None:
        _config.api_key = api_key
    if base_url is not None:
        _config.base_url = base_url.rstrip("/")
    if enabled is not None:
        _config.enabled = enabled
    if timeout_seconds is not None:
        _config.timeout_seconds = timeout_seconds


def set_enabled(enabled: bool) -> None:
    _config.enabled = enabled


def get_config() -> ClientConfig:
    return _config

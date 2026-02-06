from __future__ import annotations

import datetime as _dt
import traceback
from typing import Any, Optional

import requests

from .client import get_config


class AlshivalLogger:
    """Minimal Alshival logger for sending client logs to Alshival."""

    def __repr__(self) -> str:
        cfg = get_config()
        masked = "set" if cfg.api_key else "unset"
        return (
            "AlshivalLogger("
            f"username={cfg.username or 'unset'}, "
            f"api_key={masked}, "
            f"base_url={cfg.base_url}, "
            f"resource_id={cfg.resource_id or 'unset'}, "
            f"enabled={cfg.enabled}, "
            f"timeout_seconds={cfg.timeout_seconds}"
            ")"
        )

    def details(self) -> dict[str, Any]:
        """Return current configuration details (API key is masked)."""
        cfg = get_config()
        return {
            "username": cfg.username,
            "api_key": "set" if cfg.api_key else "unset",
            "base_url": cfg.base_url,
            "resource_id": cfg.resource_id,
            "enabled": cfg.enabled,
            "timeout_seconds": cfg.timeout_seconds,
        }

    def _send(
        self,
        level: str,
        message: str,
        *,
        extra: Optional[dict[str, Any]] = None,
        resource_id: Optional[str] = None,
    ) -> None:
        """Send a single log event to Alshival."""
        cfg = get_config()
        if not cfg.enabled:
            return
        if not cfg.username or not cfg.api_key:
            return
        payload: dict[str, Any] = {
            "username": cfg.username,
            "api_key": cfg.api_key,
            "logs": [
                {
                    "level": level,
                    "message": message,
                    "ts": _dt.datetime.utcnow().replace(tzinfo=_dt.timezone.utc).isoformat(),
                }
            ],
        }
        resolved_resource = resource_id or cfg.resource_id
        if resolved_resource:
            payload["resource_id"] = resolved_resource
        if extra:
            payload["logs"][0]["extra"] = extra
        try:
            requests.post(
                f"{cfg.base_url.rstrip('/')}/api/logs/ingest/",
                json=payload,
                timeout=cfg.timeout_seconds,
            )
        except Exception:
            # Never crash the host app
            return

    def debug(
        self,
        message: str,
        *,
        extra: Optional[dict[str, Any]] = None,
        resource_id: Optional[str] = None,
    ) -> None:
        """Send a DEBUG log event."""
        self._send("debug", message, extra=extra, resource_id=resource_id)

    def info(
        self,
        message: str,
        *,
        extra: Optional[dict[str, Any]] = None,
        resource_id: Optional[str] = None,
    ) -> None:
        """Send an INFO log event."""
        self._send("info", message, extra=extra, resource_id=resource_id)

    def warning(
        self,
        message: str,
        *,
        extra: Optional[dict[str, Any]] = None,
        resource_id: Optional[str] = None,
    ) -> None:
        """Send a WARNING log event."""
        self._send("warning", message, extra=extra, resource_id=resource_id)

    def error(
        self,
        message: str,
        *,
        extra: Optional[dict[str, Any]] = None,
        resource_id: Optional[str] = None,
    ) -> None:
        """Send an ERROR log event."""
        self._send("error", message, extra=extra, resource_id=resource_id)

    def exception(
        self,
        message: str = "",
        *,
        extra: Optional[dict[str, Any]] = None,
        resource_id: Optional[str] = None,
    ) -> None:
        """Send an EXCEPTION log event including a traceback."""
        trace = traceback.format_exc()
        combined = f"{message}\n{trace}" if message else trace
        self._send("exception", combined, extra=extra, resource_id=resource_id)


log = AlshivalLogger()

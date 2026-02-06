from __future__ import annotations

import datetime as _dt
import traceback
from typing import Any, Optional

import requests

from .client import get_config


class AlshivalLogger:
    def _send(self, level: str, message: str, *, extra: Optional[dict[str, Any]] = None) -> None:
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

    def debug(self, message: str, *, extra: Optional[dict[str, Any]] = None) -> None:
        self._send("debug", message, extra=extra)

    def info(self, message: str, *, extra: Optional[dict[str, Any]] = None) -> None:
        self._send("info", message, extra=extra)

    def warning(self, message: str, *, extra: Optional[dict[str, Any]] = None) -> None:
        self._send("warning", message, extra=extra)

    def error(self, message: str, *, extra: Optional[dict[str, Any]] = None) -> None:
        self._send("error", message, extra=extra)

    def exception(self, message: str = "", *, extra: Optional[dict[str, Any]] = None) -> None:
        trace = traceback.format_exc()
        combined = f"{message}\n{trace}" if message else trace
        self._send("exception", combined, extra=extra)


log = AlshivalLogger()

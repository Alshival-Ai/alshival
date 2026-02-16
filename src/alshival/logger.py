from __future__ import annotations

import datetime as dt
import importlib.metadata
import logging
import threading
import traceback
from typing import Any, Mapping, Optional, Union
from urllib.parse import quote

import requests

from .client import get_config

_RESERVED_RECORD_FIELDS = {
    "name",
    "msg",
    "args",
    "levelname",
    "levelno",
    "pathname",
    "filename",
    "module",
    "exc_info",
    "exc_text",
    "stack_info",
    "lineno",
    "funcName",
    "created",
    "msecs",
    "relativeCreated",
    "thread",
    "threadName",
    "processName",
    "process",
    "message",
    "asctime",
}


def _utc_now_iso() -> str:
    return dt.datetime.utcnow().replace(tzinfo=dt.timezone.utc).isoformat()


def _safe_value(value: Any) -> Any:
    if isinstance(value, (str, int, float, bool)) or value is None:
        return value
    if isinstance(value, (list, tuple)):
        return [_safe_value(item) for item in value]
    if isinstance(value, dict):
        return {str(key): _safe_value(item) for key, item in value.items()}
    return str(value)


def _sdk_version() -> str:
    try:
        return importlib.metadata.version("alshival")
    except importlib.metadata.PackageNotFoundError:
        return "0.2.0"


class AlshivalLogHandler(logging.Handler):
    """A stdlib logging handler that forwards records to Alshival Cloud Logs."""

    def __init__(self, logger_client: "AlshivalLogger", resource_id: Optional[str] = None):
        super().__init__()
        self._logger_client = logger_client
        self.resource_id = resource_id

    def emit(self, record: logging.LogRecord) -> None:
        try:
            message = record.getMessage()
            details: dict[str, Any] = {
                "logger": record.name,
                "module": record.module,
                "function": record.funcName,
                "line": record.lineno,
                "path": record.pathname,
            }
            extra_fields = {
                key: _safe_value(value)
                for key, value in record.__dict__.items()
                if key not in _RESERVED_RECORD_FIELDS
            }
            if extra_fields:
                details["extra"] = extra_fields
            if record.exc_info:
                details["exception"] = "".join(traceback.format_exception(*record.exc_info))
            if record.stack_info:
                details["stack_info"] = record.stack_info
            self._logger_client._send(  # noqa: SLF001 - intentionally using shared transport
                level=record.levelname.lower(),
                message=message,
                extra=details,
                resource_id=self.resource_id,
                logger_name=record.name,
            )
        except Exception:
            self.handleError(record)


class AlshivalLogger:
    """Alshival logger facade with stdlib logging integration."""

    def __init__(self) -> None:
        self._session = requests.Session()
        self._local = threading.local()

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
            f"timeout_seconds={cfg.timeout_seconds}, "
            f"verify_ssl={cfg.verify_ssl}"
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
            "verify_ssl": cfg.verify_ssl,
        }

    def _resource_endpoint(self, username: str, resource_id: str) -> str:
        cfg = get_config()
        safe_user = quote(username.strip(), safe="")
        safe_resource = quote(resource_id.strip(), safe="")
        return f"{cfg.base_url.rstrip('/')}/DevTools/u/{safe_user}/resources/{safe_resource}/logs/"

    def _send_payload(self, *, endpoint: str, payload: dict[str, Any], api_key: str) -> None:
        cfg = get_config()
        try:
            self._session.post(
                endpoint,
                json=payload,
                headers={"x-api-key": api_key},
                timeout=cfg.timeout_seconds,
                verify=cfg.verify_ssl,
            )
        except Exception:
            # Never crash host applications for telemetry transport failures.
            return

    def _send(
        self,
        level: str,
        message: str,
        *,
        extra: Optional[Mapping[str, Any]] = None,
        resource_id: Optional[str] = None,
        logger_name: Optional[str] = None,
    ) -> None:
        """Send a single structured event to Alshival."""
        cfg = get_config()
        if not cfg.enabled:
            return
        if not cfg.username or not cfg.api_key:
            return
        resolved_resource = (resource_id or cfg.resource_id or "").strip()
        if not resolved_resource:
            # Resource-scoped endpoint requires a resource id.
            return

        if getattr(self._local, "in_send", False):
            return
        self._local.in_send = True
        try:
            payload: dict[str, Any] = {
                "resource_id": resolved_resource,
                "sdk": "alshival-python",
                "sdk_version": _sdk_version(),
                "logs": [
                    {
                        "level": level.lower(),
                        "message": message,
                        "logger": logger_name or "alshival",
                        "ts": _utc_now_iso(),
                    }
                ],
            }
            if extra:
                payload["logs"][0]["extra"] = _safe_value(dict(extra))
            endpoint = self._resource_endpoint(cfg.username, resolved_resource)
            self._send_payload(endpoint=endpoint, payload=payload, api_key=cfg.api_key)
        finally:
            self._local.in_send = False

    def log(
        self,
        level: Union[int, str],
        message: str,
        *,
        extra: Optional[Mapping[str, Any]] = None,
        resource_id: Optional[str] = None,
    ) -> None:
        level_name = (
            level.lower()
            if isinstance(level, str)
            else logging.getLevelName(level).lower()
        )
        self._send(level_name, message, extra=extra, resource_id=resource_id)

    def debug(
        self,
        message: str,
        *,
        extra: Optional[Mapping[str, Any]] = None,
        resource_id: Optional[str] = None,
    ) -> None:
        self._send("debug", message, extra=extra, resource_id=resource_id)

    def info(
        self,
        message: str,
        *,
        extra: Optional[Mapping[str, Any]] = None,
        resource_id: Optional[str] = None,
    ) -> None:
        self._send("info", message, extra=extra, resource_id=resource_id)

    def warning(
        self,
        message: str,
        *,
        extra: Optional[Mapping[str, Any]] = None,
        resource_id: Optional[str] = None,
    ) -> None:
        self._send("warning", message, extra=extra, resource_id=resource_id)

    def warn(
        self,
        message: str,
        *,
        extra: Optional[Mapping[str, Any]] = None,
        resource_id: Optional[str] = None,
    ) -> None:
        self.warning(message, extra=extra, resource_id=resource_id)

    def error(
        self,
        message: str,
        *,
        extra: Optional[Mapping[str, Any]] = None,
        resource_id: Optional[str] = None,
    ) -> None:
        self._send("error", message, extra=extra, resource_id=resource_id)

    def critical(
        self,
        message: str,
        *,
        extra: Optional[Mapping[str, Any]] = None,
        resource_id: Optional[str] = None,
    ) -> None:
        self._send("critical", message, extra=extra, resource_id=resource_id)

    def exception(
        self,
        message: str = "",
        *,
        extra: Optional[Mapping[str, Any]] = None,
        resource_id: Optional[str] = None,
    ) -> None:
        trace = traceback.format_exc()
        combined = f"{message}\n{trace}" if message else trace
        self._send("exception", combined, extra=extra, resource_id=resource_id)

    def handler(self, *, level: int = logging.INFO, resource_id: Optional[str] = None) -> AlshivalLogHandler:
        handler = AlshivalLogHandler(self, resource_id=resource_id)
        handler.setLevel(level)
        return handler

    def get_logger(
        self,
        name: str,
        *,
        level: int = logging.INFO,
        resource_id: Optional[str] = None,
        propagate: bool = False,
    ) -> logging.Logger:
        logger = logging.getLogger(name)
        logger.setLevel(level)
        logger.propagate = propagate
        handler = self.handler(level=level, resource_id=resource_id)
        already_attached = any(
            isinstance(existing, AlshivalLogHandler) and getattr(existing, "resource_id", None) == resource_id
            for existing in logger.handlers
        )
        if not already_attached:
            logger.addHandler(handler)
        return logger

    def attach(
        self,
        logger: Union[logging.Logger, str],
        *,
        level: int = logging.INFO,
        resource_id: Optional[str] = None,
    ) -> AlshivalLogHandler:
        target = logging.getLogger(logger) if isinstance(logger, str) else logger
        handler = self.handler(level=level, resource_id=resource_id)
        target.addHandler(handler)
        if target.level == logging.NOTSET:
            target.setLevel(level)
        return handler


log = AlshivalLogger()

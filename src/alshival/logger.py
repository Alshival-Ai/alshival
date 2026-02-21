from __future__ import annotations

import datetime as dt
import importlib.metadata
import logging
import threading
import traceback
from typing import Any, Mapping, Optional

import requests

from .client import ALERT_LEVEL, build_resource_logs_endpoint, get_config

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

if logging.getLevelName(ALERT_LEVEL) == f"Level {ALERT_LEVEL}":
    logging.addLevelName(ALERT_LEVEL, "ALERT")


def _utc_now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat()


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
        # Avoid lying about the version when running from a source tree.
        return "unknown"


def _debug(msg: str) -> None:
    cfg = get_config()
    if not cfg.debug:
        return
    try:
        import sys

        sys.stderr.write(f"[alshival] {msg}\n")
    except Exception:
        return


class CloudLogHandler(logging.Handler):
    """Stdlib logging handler that forwards records to Alshival Cloud Logs.

    Records are forwarded only when record.levelno >= configured cloud level.
    Calls never raise (fail-safe telemetry).
    """

    def __init__(
        self,
        *,
        resource_id: Optional[str] = None,
        cloud_level: Optional[int] = None,
    ) -> None:
        super().__init__()
        self.resource_id = resource_id
        self.cloud_level = cloud_level
        self._local = threading.local()

    def _resource_endpoint(self, username: str, resource_id: str) -> str:
        return build_resource_logs_endpoint(username, resource_id)

    def _session(self) -> requests.Session:
        # requests.Session is not documented as thread-safe; keep one per thread.
        session = getattr(self._local, "session", None)
        if session is None:
            session = requests.Session()
            self._local.session = session
        return session

    def _should_forward(self, record: logging.LogRecord) -> bool:
        cfg = get_config()
        if not cfg.enabled:
            return False
        min_level = self.cloud_level if self.cloud_level is not None else cfg.cloud_level
        if record.levelno < min_level:
            return False
        if not cfg.username or not cfg.api_key:
            return False
        return True

    def _resolved_resource_id(self, record: logging.LogRecord) -> str:
        cfg = get_config()
        # Prefer explicit override passed via the handler, then record extra, then global config.
        candidates = [
            self.resource_id,
            getattr(record, "alshival_resource_id", None),
            cfg.resource_id,
        ]
        for value in candidates:
            if value and str(value).strip():
                return str(value).strip()
        return ""

    def emit(self, record: logging.LogRecord) -> None:
        if getattr(self._local, "in_emit", False):
            return
        self._local.in_emit = True
        try:
            if not self._should_forward(record):
                return

            cfg = get_config()
            resolved_resource = self._resolved_resource_id(record)
            if not resolved_resource:
                _debug("skipping cloud log: missing resource_id (set ALSHIVAL_RESOURCE_ID or pass resource_id)")
                return

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

            payload: dict[str, Any] = {
                "resource_id": resolved_resource,
                "sdk": "alshival-python",
                "sdk_version": _sdk_version(),
                "logs": [
                    {
                        "level": record.levelname.lower(),
                        "message": message,
                        "logger": record.name,
                        "ts": _utc_now_iso(),
                        "extra": details,
                    }
                ],
            }

            endpoint = self._resource_endpoint(cfg.username or "", resolved_resource)
            try:
                resp = self._session().post(
                    endpoint,
                    json=payload,
                    headers={"x-api-key": cfg.api_key or ""},
                    timeout=cfg.timeout_seconds,
                    verify=cfg.verify_ssl,
                )
                if cfg.debug and getattr(resp, "status_code", 0) >= 400:
                    _debug(f"cloud log post failed: status={resp.status_code}")
            except Exception as exc:
                _debug(f"cloud log post failed: {exc!r}")
                return
        except Exception:
            # Logging handlers should never raise into host applications.
            self.handleError(record)
        finally:
            self._local.in_emit = False


# Backwards-compatible alias (older name).
AlshivalLogHandler = CloudLogHandler


def _dedupe_add_handler(target: logging.Logger, handler: CloudLogHandler) -> CloudLogHandler:
    for existing in target.handlers:
        if isinstance(existing, CloudLogHandler) and getattr(existing, "resource_id", None) == handler.resource_id:
            # Allow "reattaching" to update cloud_level/resource binding without duplicating handlers.
            if handler.cloud_level is not None:
                existing.cloud_level = handler.cloud_level
            return existing
    target.addHandler(handler)
    return handler


class AlshivalLogger:
    """Facade over a stdlib logger with optional cloud forwarding.

    - `alshival.log.info(...)` behaves like stdlib logging (passes through to handlers/propagation).
    - Cloud forwarding is controlled independently via `alshival.configure(cloud_level=...)`.
    """

    def __init__(self, name: str = "alshival") -> None:
        self._logger = logging.getLogger(name)
        _dedupe_add_handler(self._logger, CloudLogHandler())

    def __getattr__(self, name: str) -> Any:
        return getattr(self._logger, name)

    def details(self) -> dict[str, Any]:
        """Return current SDK configuration (API key is masked)."""
        cfg = get_config()
        return {
            "username": cfg.username,
            "api_key": "set" if cfg.api_key else "unset",
            "base_url": cfg.base_url,
            "resource_id": cfg.resource_id,
            "enabled": cfg.enabled,
            "cloud_level": cfg.cloud_level,
            "timeout_seconds": cfg.timeout_seconds,
            "verify_ssl": cfg.verify_ssl,
            "debug": cfg.debug,
        }

    def _with_resource(self, kwargs: dict[str, Any], resource_id: Optional[str]) -> dict[str, Any]:
        if not resource_id:
            return kwargs
        extra = kwargs.get("extra")
        merged: dict[str, Any] = {}
        if isinstance(extra, Mapping):
            merged.update(dict(extra))
        merged["alshival_resource_id"] = resource_id
        kwargs["extra"] = merged
        return kwargs

    def log(self, level: int, msg: Any, *args: Any, resource_id: Optional[str] = None, **kwargs: Any) -> None:
        self._logger.log(level, msg, *args, **self._with_resource(kwargs, resource_id))

    def debug(self, msg: Any, *args: Any, resource_id: Optional[str] = None, **kwargs: Any) -> None:
        self._logger.debug(msg, *args, **self._with_resource(kwargs, resource_id))

    def info(self, msg: Any, *args: Any, resource_id: Optional[str] = None, **kwargs: Any) -> None:
        self._logger.info(msg, *args, **self._with_resource(kwargs, resource_id))

    def warning(self, msg: Any, *args: Any, resource_id: Optional[str] = None, **kwargs: Any) -> None:
        self._logger.warning(msg, *args, **self._with_resource(kwargs, resource_id))

    def error(self, msg: Any, *args: Any, resource_id: Optional[str] = None, **kwargs: Any) -> None:
        self._logger.error(msg, *args, **self._with_resource(kwargs, resource_id))

    def critical(self, msg: Any, *args: Any, resource_id: Optional[str] = None, **kwargs: Any) -> None:
        self._logger.critical(msg, *args, **self._with_resource(kwargs, resource_id))

    def alert(self, msg: Any, *args: Any, resource_id: Optional[str] = None, **kwargs: Any) -> None:
        self._logger.log(ALERT_LEVEL, msg, *args, **self._with_resource(kwargs, resource_id))

    def exception(self, msg: Any, *args: Any, resource_id: Optional[str] = None, **kwargs: Any) -> None:
        # Keep stdlib semantics: logs at ERROR with exc_info=True by default.
        kwargs.setdefault("exc_info", True)
        self._logger.exception(msg, *args, **self._with_resource(kwargs, resource_id))

    def handler(
        self,
        *,
        # Back-compat alias: older versions used `level=` to indicate the minimum level forwarded to cloud.
        level: Optional[int] = None,
        cloud_level: Optional[int] = None,
        resource_id: Optional[str] = None,
    ) -> CloudLogHandler:
        resolved_cloud_level = cloud_level if cloud_level is not None else level
        return CloudLogHandler(resource_id=resource_id, cloud_level=resolved_cloud_level)

    def get_logger(
        self,
        name: str,
        *,
        level: int = logging.INFO,
        cloud_level: Optional[int] = None,
        resource_id: Optional[str] = None,
        propagate: bool = False,
    ) -> logging.Logger:
        logger = logging.getLogger(name)
        logger.setLevel(level)
        logger.propagate = propagate
        # If cloud_level isn't provided, default to the logger's level (matches older behavior).
        resolved_cloud_level = cloud_level if cloud_level is not None else level
        handler = CloudLogHandler(resource_id=resource_id, cloud_level=resolved_cloud_level)
        _dedupe_add_handler(logger, handler)
        return logger

    def attach(
        self,
        logger: logging.Logger | str,
        *,
        # Back-compat alias: older versions used `level=` to indicate the minimum level forwarded to cloud.
        level: Optional[int] = None,
        cloud_level: Optional[int] = None,
        resource_id: Optional[str] = None,
    ) -> CloudLogHandler:
        target = logging.getLogger(logger) if isinstance(logger, str) else logger
        resolved_cloud_level = cloud_level if cloud_level is not None else level
        handler = CloudLogHandler(resource_id=resource_id, cloud_level=resolved_cloud_level)
        return _dedupe_add_handler(target, handler)


log = AlshivalLogger()

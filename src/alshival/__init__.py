from .client import ALERT_LEVEL, configure, set_enabled, get_config
from .logger import log
from .mcp_tools import mcp, mcp_tool, github_mcp_tool


def get_logger(name: str, **kwargs):
    return log.get_logger(name, **kwargs)


def handler(**kwargs):
    return log.handler(**kwargs)


def attach(logger, **kwargs):
    return log.attach(logger, **kwargs)


__all__ = [
    "configure",
    "set_enabled",
    "get_config",
    "ALERT_LEVEL",
    "log",
    "mcp",
    "mcp_tool",
    "github_mcp_tool",
    "get_logger",
    "handler",
    "attach",
]

from .client import configure, set_enabled, get_config
from .logger import log


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
    "log",
    "get_logger",
    "handler",
    "attach",
]

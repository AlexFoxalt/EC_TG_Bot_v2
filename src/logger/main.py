import os
import sys
from functools import cache
from typing import Optional

from loguru import logger as _loguru_logger
from loguru._logger import Logger

__all__ = ["get_logger", "logger"]

DEFAULT_LOGGER_NAME = "tg-bot"
DEFAULT_MESSAGE_FORMAT = (
    "<m>{time:YYYY-MM-DD HH:mm:ss.SSS}</m> | <level>{level: <8}</level> | {extra[username]:<25} | {message}"
)


def _env_bool(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "y", "on"}


def _setup_default_logger(context_logger: Logger) -> None:
    context_logger.add(
        sink=sys.stdout,
        colorize=_env_bool("LOGURU_COLORIZE", True),
        format=DEFAULT_MESSAGE_FORMAT,
        backtrace=_env_bool("LOGURU_BACKTRACE", True),
        diagnose=False,  # avoid dumping locals (can leak secrets)
        enqueue=True,  # async/thread safe
    )


def _setup_logger(name: str, level: Optional[str]) -> Logger:
    """
    Return configured logger.

    NOTE: We intentionally set `diagnose=False` to reduce risk of leaking secrets
    via exception local-variable dumps in logs.
    """
    _loguru_logger.remove()

    ctx = _loguru_logger.bind(name=name, username="system")
    _setup_default_logger(ctx)

    ctx.level("INFO", color="<green>")
    ctx.level("WARNING", color="<yellow>")
    ctx.level("ERROR", color="<red>")

    if level:
        # `logger.level()` defines; `logger.remove/add` controls filtering.
        # The add() above defaults to INFO; we re-add with chosen level.
        _loguru_logger.remove()
        ctx.add(
            sink=sys.stdout,
            level=level.upper(),
            colorize=_env_bool("LOGURU_COLORIZE", True),
            format=DEFAULT_MESSAGE_FORMAT,
            backtrace=_env_bool("LOGURU_BACKTRACE", True),
            diagnose=False,
            enqueue=True,
        )

    return ctx


@cache
def get_logger(name: str = DEFAULT_LOGGER_NAME) -> Logger:
    level = os.getenv("LOG_LEVEL", "INFO")
    return _setup_logger(name=name, level=level)


logger = get_logger()

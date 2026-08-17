from __future__ import annotations

import logging

from .formatters import ConsoleFormatter, JSONFormatter

_configured = False


def setup_logging(
    *,
    level: int = logging.INFO,
    json_logs: bool = False,
    noisy_loggers: dict[str, int] | None = None,
) -> None:
    global _configured
    if _configured:
        return

    handler = logging.StreamHandler()
    handler.setFormatter(
        JSONFormatter()
        if json_logs
        else ConsoleFormatter(fmt="%(levelprefix)s %(message)s", use_colors=None)
    )

    root = logging.getLogger()
    root.setLevel(level)
    root.handlers = [handler]

    for name in ("uvicorn", "uvicorn.error"):
        logging.getLogger(name).handlers = []
        logging.getLogger(name).propagate = True

    logging.getLogger("uvicorn.access").disabled = True

    for name, lvl in {
        "httpx": logging.WARNING,
        "httpcore": logging.WARNING,
        **(noisy_loggers or {}),
    }.items():
        logging.getLogger(name).setLevel(lvl)

    _configured = True

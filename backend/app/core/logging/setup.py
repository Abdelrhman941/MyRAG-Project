from __future__ import annotations

import logging

_configured = False


def setup_logging(
    *,
    level: int = logging.INFO,
) -> None:
    """Configure application logging once."""

    global _configured

    if _configured:
        return

    logging.basicConfig(
        level=level,
        format="%(levelname)s: %(message)s",
        force=True,
    )

    logging.getLogger("uvicorn.access").disabled = True
    logging.getLogger("httpx").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)

    _configured = True

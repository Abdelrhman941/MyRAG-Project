from __future__ import annotations

from contextvars import ContextVar

_request_id: ContextVar[str | None] = ContextVar(
    "request_id",
    default=None,
)


def set_request_id(request_id: str) -> None:
    """Store the current request ID in the execution context."""
    _request_id.set(request_id)


def get_request_id() -> str | None:
    """Return the current request ID."""
    return _request_id.get()


def clear_request_id() -> None:
    """Clear the current request ID."""
    _request_id.set(None)

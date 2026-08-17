from typing import Any


class AppError(Exception):
    """Base application error with HTTP mapping."""

    status_code: int = 400
    code: str = "application_error"
    message: str = "Application error."
    headers: dict[str, str] | None = None
    details: list[dict[str, Any]] | None = None

    def __init__(
        self,
        *,
        message: str | None = None,
        details: list[dict[str, Any]] | None = None,
        headers: dict[str, str] | None = None,
    ):
        if message is not None:
            self.message = message
        self.details = details
        self.headers = headers
        super().__init__(self.message)


__all__ = [
    "AppError",
]

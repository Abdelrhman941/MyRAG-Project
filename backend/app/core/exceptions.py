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
        status_code: int | None = None,
        code: str | None = None,
        message: str | None = None,
        details: list[dict[str, Any]] | None = None,
        headers: dict[str, str] | None = None,
    ):
        if status_code is not None:
            self.status_code = status_code
        if code is not None:
            self.code = code
        if message is not None:
            self.message = message
        self.details = details
        self.headers = headers
        super().__init__(self.message)


class StorageError(AppError):
    """Raised when filesystem operations fail."""

    status_code: int = 500
    code: str = "storage_error"
    message: str = "A storage error occurred."


class DuplicateDocumentError(AppError):
    """Raised when uploading a document that already exists (by content hash)."""

    status_code: int = 409
    code: str = "duplicate_document"
    message: str = "This document already exists."


__all__ = [
    "AppError",
    "DuplicateDocumentError",
    "StorageError",
]

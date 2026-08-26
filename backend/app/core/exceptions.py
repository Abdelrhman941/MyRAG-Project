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


class MissingFilenameError(AppError):
    status_code = 400
    code = "missing_filename"
    message = "Filename is required."


class UnsupportedDocumentTypeError(AppError):
    status_code = 422
    code = "unsupported_document_type"
    message = "Unsupported document type."


class FileTooLargeError(AppError):
    status_code = 413
    code = "file_too_large"
    message = "File exceeds the maximum allowed size."


class TooManyFilesError(AppError):
    status_code = 400
    code = "too_many_files"
    message = "Too many files. Maximum 10 files per request."


class ParsingError(AppError):
    status_code = 422
    code = "parsing_failed"
    message = "Failed to parse the document."


class EmptyQueryError(AppError):
    status_code = 400
    code = "empty_query"
    message = "Search query cannot be empty."


class RetrievalError(AppError):
    status_code = 502
    code = "retrieval_unavailable"
    message = "Search service is currently unavailable."


__all__ = [
    "AppError",
    "DuplicateDocumentError",
    "EmptyQueryError",
    "FileTooLargeError",
    "MissingFilenameError",
    "ParsingError",
    "RetrievalError",
    "StorageError",
    "TooManyFilesError",
    "UnsupportedDocumentTypeError",
]


class NotFoundError(AppError):
    status_code = 404
    code = "not_found"
    message = "Resource not found."


__all__.append("NotFoundError")

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
    """Raised when a document with the same content already exists."""

    status_code: int = 409
    code: str = "duplicate_document"
    message: str = "This document already exists."


class MissingFilenameError(AppError):
    """Raised when an uploaded file has no filename."""

    status_code: int = 400
    code: str = "missing_filename"
    message: str = "Filename is required."


class UnsupportedDocumentTypeError(AppError):
    """Raised when an uploaded document type is unsupported."""

    status_code: int = 422
    code: str = "unsupported_document_type"
    message: str = "Unsupported document type."


class FileTooLargeError(AppError):
    """Raised when an uploaded file exceeds the configured size limit."""

    status_code: int = 413
    code: str = "file_too_large"
    message: str = "File exceeds the maximum allowed size."


class TooManyFilesError(AppError):
    """Raised when a batch contains too many files."""

    status_code: int = 400
    code: str = "too_many_files"
    message: str = "Too many files."


class ParsingError(AppError):
    """Raised when document parsing fails."""

    status_code: int = 422
    code: str = "parsing_failed"
    message: str = "Failed to parse the document."


class EmptyQueryError(AppError):
    """Raised when a retrieval query is empty."""

    status_code: int = 400
    code: str = "empty_query"
    message: str = "Search query cannot be empty."


class RetrievalError(AppError):
    """Raised when the retrieval service is unavailable."""

    status_code: int = 502
    code: str = "retrieval_unavailable"
    message: str = "Search service is currently unavailable."


class NotFoundError(AppError):
    """Raised when a requested resource does not exist."""

    status_code = 404
    code = "not_found"
    message = "Resource not found."


class DocumentProcessingConflictError(AppError):
    """Raised when a document cannot be modified during processing."""

    status_code = 409
    code = "document_processing"
    message = "Cannot delete a document while it is being processed."


class InvalidDocumentStateError(AppError):
    """Raised when an operation is invalid for the document's current state."""

    status_code = 409
    code = "invalid_document_state"
    message = "Document is not in a valid state for this operation."


class VectorStoreDeletionError(AppError):
    """Raised when document vectors cannot be deleted."""

    status_code = 502
    code = "vector_deletion_failed"
    message = "Failed to delete document vectors."


class QueueUnavailableError(AppError):
    """Raised when the background job queue is unavailable."""

    status_code = 503
    code = "queue_unavailable"
    message = "Background processing queue is unavailable."


class TransientIngestionError(AppError):
    """Raised when an ingestion failure may succeed on retry."""

    def __init__(
        self,
        message: str = "Transient error during ingestion",
        reason: str = "internal_error",
    ):
        self.reason = reason
        super().__init__(
            message=message,
            code="transient_ingestion_error",
            status_code=500,
        )


class PermanentIngestionError(AppError):
    """Raised when an ingestion failure should not be retried."""

    def __init__(
        self,
        message: str = "Permanent error during ingestion",
        reason: str = "internal_error",
    ):
        self.reason = reason
        super().__init__(
            message=message,
            code="permanent_ingestion_error",
            status_code=400,
        )


class LLMProviderError(AppError):
    """Raised when the configured LLM provider fails."""

    status_code = 502
    code = "llm_provider_error"
    message = "The LLM provider encountered an error."


__all__ = [
    "AppError",
    "DocumentProcessingConflictError",
    "DuplicateDocumentError",
    "EmptyQueryError",
    "FileTooLargeError",
    "InvalidDocumentStateError",
    "LLMProviderError",
    "MissingFilenameError",
    "NotFoundError",
    "ParsingError",
    "PermanentIngestionError",
    "QueueUnavailableError",
    "RetrievalError",
    "StorageError",
    "TooManyFilesError",
    "TransientIngestionError",
    "UnsupportedDocumentTypeError",
    "VectorStoreDeletionError",
]

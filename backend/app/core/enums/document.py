from enum import StrEnum


class DocumentType(StrEnum):
    """Supported document types."""

    PDF = "pdf"
    TXT = "txt"
    MD = "md"

    @property
    def extension(self) -> str:
        """Return the canonical file extension."""
        return f".{self.value}"


class DocumentStatus(StrEnum):
    """Document processing status."""

    PROCESSING = "processing"
    READY = "ready"
    FAILED = "failed"

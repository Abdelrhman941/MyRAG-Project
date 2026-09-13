from enum import StrEnum


class DocumentType(StrEnum):
    """Supported document types."""

    DOCX = "docx"
    MD = "md"
    PDF = "pdf"
    TXT = "txt"

    @property
    def extension(self) -> str:
        """Return the canonical file extension."""
        return f".{self.value}"


class DocumentStatus(StrEnum):
    """Document processing status."""

    UPLOADED = "uploaded"
    PROCESSING = "processing"
    READY = "ready"
    FAILED = "failed"
    DELETING = "deleting"

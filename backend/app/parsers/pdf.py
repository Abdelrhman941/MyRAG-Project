import logging
from typing import BinaryIO

from pypdf import PdfReader
from pypdf.errors import PdfReadError

from ..models import ParsedSegment
from .utils import normalize_text

logger = logging.getLogger(__name__)


def parse_pdf(stream: BinaryIO) -> list[ParsedSegment]:
    """Parse PDF document into page segments."""
    try:
        reader = PdfReader(stream)
    except PdfReadError as e:
        # Re-raise so core catches it as a ParsingError
        raise ValueError("Failed to read PDF file") from e

    if reader.is_encrypted:
        raise ValueError("PDF is encrypted and cannot be parsed")

    segments: list[ParsedSegment] = []

    # Lazy import to avoid circular imports if core.py imports this

    for i, page in enumerate(reader.pages):
        try:
            text = page.extract_text()
            if text:
                normalized = normalize_text(text)
                if normalized:
                    segments.append(ParsedSegment(text=normalized, page_number=i + 1))
        except Exception as e:
            logger.warning("Failed to extract text from page %d: %s", i + 1, e)
            continue

    return segments

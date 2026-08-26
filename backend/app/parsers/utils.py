import logging
import re
from typing import BinaryIO

logger = logging.getLogger(__name__)


def normalize_text(text: str) -> str:
    """Normalize text by collapsing horizontal whitespace and standardizing newlines.

    Preserves paragraph breaks (double newlines) which are important for chunking.
    """
    # Convert CRLF to LF
    text = text.replace("\r\n", "\n")
    # Collapse 3+ newlines to 2 newlines
    text = re.sub(r"\n{3,}", "\n\n", text)
    # Collapse multiple spaces/tabs to a single space
    text = re.sub(r"[ \t]+", " ", text)
    return text.strip()


def decode_text(stream: BinaryIO) -> str:
    """Decode raw bytes to string, falling back to latin-1 if utf-8 fails."""
    raw_bytes = stream.read()
    try:
        return raw_bytes.decode("utf-8")
    except UnicodeDecodeError:
        logger.info("UTF-8 decoding failed, falling back to latin-1")
        try:
            return raw_bytes.decode("latin-1")
        except UnicodeDecodeError as e:
            raise ValueError("Failed to decode text file") from e

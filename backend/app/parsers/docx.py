import logging
from typing import BinaryIO

import docx

from ..models import ParsedSegment

logger = logging.getLogger(__name__)


def parse_docx(stream: BinaryIO) -> list[ParsedSegment]:
    """Parse DOCX file and extract paragraphs as segments."""
    try:
        doc = docx.Document(stream)
    except Exception as e:
        raise ValueError("Failed to read DOCX file") from e

    from .utils import normalize_text

    segments: list[ParsedSegment] = []

    for para in doc.paragraphs:
        text = para.text
        if text:
            normalized = normalize_text(text)
            if normalized:
                segments.append(ParsedSegment(text=normalized))

    return segments

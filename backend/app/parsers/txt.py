import logging
from typing import BinaryIO

from ..models import ParsedSegment
from .utils import decode_text, normalize_text

logger = logging.getLogger(__name__)


def parse_txt(stream: BinaryIO) -> list[ParsedSegment]:
    """Parse raw text, decoding and normalizing it."""
    text = decode_text(stream)
    normalized = normalize_text(text)

    if not normalized:
        return []

    return [ParsedSegment(text=normalized)]

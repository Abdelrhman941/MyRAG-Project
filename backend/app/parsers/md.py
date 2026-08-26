import logging
from typing import BinaryIO

from markdown_it import MarkdownIt

from ..models import ParsedSegment
from .utils import decode_text, normalize_text

logger = logging.getLogger(__name__)


def parse_md(stream: BinaryIO) -> list[ParsedSegment]:
    """Parse Markdown file and extract semantic plain text."""
    # 1. Decode text
    raw_md = decode_text(stream)

    if not raw_md.strip():
        return []

    # 2. Parse Markdown
    md = MarkdownIt("commonmark")
    tokens = md.parse(raw_md)

    # 3. Extract text semantically
    extracted_text = []

    def _extract(token_list):
        for token in token_list:
            if (
                token.type == "text"
                or token.type == "code_inline"
                or token.type == "code_block"
                or token.type == "fence"
            ):
                extracted_text.append(token.content)
            elif token.type == "softbreak" or token.type == "hardbreak":
                extracted_text.append("\n")
            elif token.type == "paragraph_close" or token.type == "heading_close":
                extracted_text.append("\n\n")
            elif token.type == "list_item_close":
                extracted_text.append("\n")

            if token.children:
                _extract(token.children)

    _extract(tokens)

    final_text = "".join(extracted_text)

    # 4. Normalize
    normalized = normalize_text(final_text)

    if not normalized:
        return []

    return [ParsedSegment(text=normalized)]

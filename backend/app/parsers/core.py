import io
import logging
from uuid import UUID

from ..core import DocumentType
from ..core.exceptions import ParsingError
from ..models import ParsedSegment
from .docx import parse_docx
from .md import parse_md
from .pdf import parse_pdf
from .txt import parse_txt

logger = logging.getLogger(__name__)


def parse(
    content: bytes, doc_type: DocumentType, document_id: UUID
) -> list[ParsedSegment]:
    """Parse a document's content into a list of normalized segments."""
    stream = io.BytesIO(content)

    try:
        match doc_type:
            case DocumentType.PDF:
                return parse_pdf(stream)
            case DocumentType.TXT:
                return parse_txt(stream)
            case DocumentType.MD:
                return parse_md(stream)
            case DocumentType.DOCX:
                return parse_docx(stream)
            case _:
                return []
    except Exception as e:
        logger.warning("Parsing failed for document %s: %s", document_id, e)
        raise ParsingError(details=[{"document_id": str(document_id)}]) from e

from uuid import uuid4

from app.chunking.core import chunk
from app.models.ingestion import ParsedSegment


def test_chunk_preserves_segment_metadata():
    doc_id = uuid4()
    segments = [
        ParsedSegment(text="A" * 1000, page_number=1, section="Intro"),
        ParsedSegment(text="B" * 1000, page_number=2, section="Body"),
    ]

    chunks = chunk(segments, doc_id)

    # Verify we got chunks and index is global
    assert len(chunks) > 0

    # Check that metadata is preserved and chunk index is continuous
    for idx, c in enumerate(chunks):
        assert c.chunk_index == idx

        if c.text.startswith("A"):
            assert c.page_number == 1
            assert c.section == "Intro"
        elif c.text.startswith("B"):
            assert c.page_number == 2
            assert c.section == "Body"

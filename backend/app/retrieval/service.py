import logging
from uuid import UUID

from ..core.config import Settings
from ..core.exceptions import EmptyQueryError, RetrievalError
from ..embeddings import get_embedding_model
from ..infrastructure.ports import VectorStorePort
from ..models import Chunk, RetrievalResult

logger = logging.getLogger(__name__)


class RetrievalService:
    def __init__(self, vector_store: VectorStorePort, settings: Settings):
        self.vector_store = vector_store
        self.settings = settings

    async def retrieve(
        self, query: str, session_id: UUID, top_k: int | None = None
    ) -> list[RetrievalResult]:
        if not query or not query.strip():
            raise EmptyQueryError()

        limit = top_k if top_k is not None else self.settings.RETRIEVAL_TOP_K

        # Embed query
        model = get_embedding_model(self.settings.EMBEDDING_MODEL)
        import asyncio

        dense, sparse = await asyncio.to_thread(model.encode_batch, [query], 1)

        query_dense = dense[0]
        query_sparse = sparse[0] if self.settings.RETRIEVAL_HYBRID else None

        # Query vector store
        try:
            raw_results = await self.vector_store.query(
                query_dense=query_dense,
                query_sparse=query_sparse,
                session_id=session_id,
                limit=limit,
            )
        except Exception as e:
            logger.exception("Failed to query vector store")
            raise RetrievalError() from e

        # Map to domain objects
        results = []
        min_score = self.settings.RETRIEVAL_MIN_SCORE

        for raw in raw_results:
            if raw["score"] < min_score:
                continue

            payload = raw["payload"]
            chunk = Chunk(
                document_id=UUID(payload["document_id"]),
                chunk_index=payload["chunk_index"],
                text=payload["text"],
                page_number=payload.get("page_number"),
                section=payload.get("section"),
            )
            results.append(
                RetrievalResult(
                    chunk=chunk,
                    score=raw["score"],
                    original_file_name=payload.get("original_file_name", ""),
                )
            )

        return results

from __future__ import annotations

import logging
from typing import Any
from uuid import NAMESPACE_DNS, UUID, uuid5

from qdrant_client import AsyncQdrantClient
from qdrant_client.http import models as rest

from ...core.config import Settings
from ...models import Chunk
from ..ports import VectorSearchHit

logger = logging.getLogger(__name__)


class QdrantVectorStore:
    """Qdrant adapter for dense and sparse hybrid retrieval."""

    def __init__(self, settings: Settings) -> None:
        self.client = AsyncQdrantClient(
            url=settings.QDRANT_URL,
            check_compatibility=False,
        )
        self.collection_name = settings.QDRANT_COLLECTION
        self.embedding_dimension = settings.EMBEDDING_DIMENSION

    async def ensure_collection(self) -> None:
        """Ensure the collection and required payload indexes exist."""
        exists = await self.client.collection_exists(
            self.collection_name,
        )

        if not exists:
            try:
                await self.client.create_collection(
                    collection_name=self.collection_name,
                    vectors_config={
                        "dense": rest.VectorParams(
                            size=self.embedding_dimension,
                            distance=rest.Distance.COSINE,
                        ),
                    },
                    sparse_vectors_config={
                        "sparse": rest.SparseVectorParams(),
                    },
                )

                logger.info(
                    "Created Qdrant collection '%s'",
                    self.collection_name,
                )

            except Exception:
                # Another process may have created the collection
                # concurrently between the existence check and creation.
                if not await self.client.collection_exists(self.collection_name):
                    raise

        await self._ensure_payload_indexes()

    async def _ensure_payload_indexes(self) -> None:
        """Ensure payload indexes required by retrieval exist."""
        await self.client.create_payload_index(
            collection_name=self.collection_name,
            field_name="session_id",
            field_schema=rest.PayloadSchemaType.KEYWORD,
        )

        await self.client.create_payload_index(
            collection_name=self.collection_name,
            field_name="document_id",
            field_schema=rest.PayloadSchemaType.KEYWORD,
        )

    async def upsert_chunks(
        self,
        chunks: list[Chunk],
        dense_vectors: list[list[float]],
        sparse_vectors: list[dict[int, float]],
        payload_metadata: dict[str, Any],
    ) -> None:
        """Upsert document chunks using deterministic point IDs."""
        if not chunks:
            return

        if not (len(chunks) == len(dense_vectors) == len(sparse_vectors)):
            raise ValueError(
                "Chunk and vector counts must match.",
            )

        points: list[rest.PointStruct] = []

        for index, chunk in enumerate(chunks):
            point_id = str(
                uuid5(
                    NAMESPACE_DNS,
                    f"{chunk.document_id}:{chunk.chunk_index}",
                )
            )

            sparse_vector = sparse_vectors[index]

            payload: dict[str, Any] = {
                "document_id": str(chunk.document_id),
                "chunk_index": chunk.chunk_index,
                "text": chunk.text,
            }

            if chunk.page_number is not None:
                payload["page_number"] = chunk.page_number

            if chunk.section is not None:
                payload["section"] = chunk.section

            payload.update(payload_metadata)

            points.append(
                rest.PointStruct(
                    id=point_id,
                    vector={
                        "dense": dense_vectors[index],
                        "sparse": rest.SparseVector(
                            indices=list(sparse_vector.keys()),
                            values=list(sparse_vector.values()),
                        ),
                    },
                    payload=payload,
                )
            )

        await self.client.upsert(
            collection_name=self.collection_name,
            points=points,
        )

    async def delete_by_document(
        self,
        document_id: UUID,
    ) -> None:
        """Delete all points associated with a document."""
        await self.client.delete(
            collection_name=self.collection_name,
            points_selector=rest.Filter(
                must=[
                    rest.FieldCondition(
                        key="document_id",
                        match=rest.MatchValue(
                            value=str(document_id),
                        ),
                    ),
                ],
            ),
        )

    async def query(
        self,
        query_dense: list[float],
        query_sparse: dict[int, float] | None,
        session_id: UUID,
        limit: int = 5,
    ) -> list[VectorSearchHit]:
        """Retrieve the most relevant chunks for a session."""
        session_filter = rest.Filter(
            must=[
                rest.FieldCondition(
                    key="session_id",
                    match=rest.MatchValue(
                        value=str(session_id),
                    ),
                ),
            ],
        )

        if query_sparse is not None:
            prefetch = [
                rest.Prefetch(
                    query=query_dense,
                    using="dense",
                    limit=limit * 2,
                    filter=session_filter,
                ),
                rest.Prefetch(
                    query=rest.SparseVector(
                        indices=list(query_sparse.keys()),
                        values=list(query_sparse.values()),
                    ),
                    using="sparse",
                    limit=limit * 2,
                    filter=session_filter,
                ),
            ]

            response = await self.client.query_points(
                collection_name=self.collection_name,
                prefetch=prefetch,
                query_filter=session_filter,
                query=rest.FusionQuery(
                    fusion=rest.Fusion.RRF,
                ),
                limit=limit,
                with_payload=True,
            )

        else:
            response = await self.client.query_points(
                collection_name=self.collection_name,
                query=query_dense,
                using="dense",
                limit=limit,
                with_payload=True,
                query_filter=session_filter,
            )

        results: list[VectorSearchHit] = []

        for point in response.points:
            if point.payload is None:
                continue

            results.append(
                {
                    "id": str(point.id),
                    "score": point.score,
                    "payload": point.payload,
                }
            )

        return results

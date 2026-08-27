import logging
from typing import Any
from uuid import NAMESPACE_DNS, UUID, uuid5

from qdrant_client import AsyncQdrantClient
from qdrant_client.http import models as rest

from ...core.config import Settings
from ...models import Chunk

logger = logging.getLogger(__name__)


class QdrantVectorStore:
    """Qdrant adapter implementing VectorStorePort.

    Collection name: ``chunks``
    Named dense vector (1024-dim, Cosine) + named sparse vector.
    Point IDs are deterministic: uuid5(NAMESPACE_DNS, f"{document_id}:{chunk_index}").
    """

    def __init__(self, settings: Settings) -> None:
        self.client = AsyncQdrantClient(url=settings.QDRANT_URL)
        self.collection_name = "chunks"

    async def ensure_collection(self) -> None:
        """Ensure the target collection exists with the required configuration."""
        exists = await self.client.collection_exists(self.collection_name)
        if not exists:
            try:
                await self.client.create_collection(
                    collection_name=self.collection_name,
                    vectors_config={
                        "dense": rest.VectorParams(
                            size=1024, distance=rest.Distance.COSINE
                        )
                    },
                    sparse_vectors_config={"sparse": rest.SparseVectorParams()},
                )
                logger.info("Created Qdrant collection '%s'", self.collection_name)
            except Exception as e:
                # Handle race condition where another task creates it concurrently
                if await self.client.collection_exists(self.collection_name):
                    pass
                else:
                    raise e

    async def upsert_chunks(
        self,
        chunks: list[Chunk],
        dense_vectors: list[list[float]],
        sparse_vectors: list[dict[int, float]],
        payload_metadata: dict[str, Any],
    ) -> None:
        """Upsert embedded chunks into the vector store."""
        if not chunks:
            return

        points = []
        for i, chunk in enumerate(chunks):
            # point ID = uuid5(document_id + chunk_index)
            point_id = str(
                uuid5(NAMESPACE_DNS, f"{chunk.document_id}:{chunk.chunk_index}")
            )

            sparse_vec = sparse_vectors[i]
            indices = list(sparse_vec.keys())
            values = list(sparse_vec.values())

            payload = {
                "document_id": str(chunk.document_id),
                "chunk_index": chunk.chunk_index,
                "text": chunk.text,
            }
            payload.update(payload_metadata)

            points.append(
                rest.PointStruct(
                    id=point_id,
                    vector={
                        "dense": dense_vectors[i],
                        "sparse": rest.SparseVector(indices=indices, values=values),
                    },
                    payload=payload,
                )
            )

        await self.client.upsert(collection_name=self.collection_name, points=points)

    async def delete_by_document(self, document_id: UUID) -> None:
        """Delete all vectors associated with a document ID."""
        await self.client.delete(
            collection_name=self.collection_name,
            points_selector=rest.Filter(
                must=[
                    rest.FieldCondition(
                        key="document_id", match=rest.MatchValue(value=str(document_id))
                    )
                ]
            ),
        )

    async def query(
        self,
        query_dense: list[float],
        query_sparse: dict[int, float] | None,
        session_id: UUID,
        limit: int = 5,
    ) -> list[dict[str, Any]]:
        from qdrant_client.models import FieldCondition, Filter, MatchValue

        session_filter = Filter(
            must=[
                FieldCondition(
                    key="session_id", match=MatchValue(value=str(session_id))
                )
            ]
        )
        """Retrieve the top-*limit* chunks closest to the query vectors."""
        if query_sparse is not None:
            # Hybrid search via Query API
            prefetch = [
                rest.Prefetch(
                    query=query_dense,
                    using="dense",
                    limit=limit * 2,
                ),
                rest.Prefetch(
                    query=rest.SparseVector(
                        indices=list(query_sparse.keys()),
                        values=list(query_sparse.values()),
                    ),
                    using="sparse",
                    limit=limit * 2,
                ),
            ]
            response = await self.client.query_points(
                collection_name=self.collection_name,
                prefetch=prefetch,
                query_filter=session_filter,
                query=rest.FusionQuery(fusion=rest.Fusion.RRF),
                limit=limit,
                with_payload=True,
            )
        else:
            # Dense-only search
            response = await self.client.query_points(
                collection_name=self.collection_name,
                query=query_dense,
                using="dense",
                limit=limit,
                with_payload=True,
                query_filter=session_filter,
            )

        results = []
        for point in response.points:
            if point.payload is not None:
                res = dict(point.payload)
                res["_score"] = point.score
                results.append(res)

        return results

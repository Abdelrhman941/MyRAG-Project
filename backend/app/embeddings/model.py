"""
Lazy singleton wrapper around the BGE-M3 embedding model.

BGE-M3 produces both:
- Dense (1024-dim): accessed via SentenceTransformer.encode()
- Sparse (SPLADE-style token weights): accessed via the model's internal
  ``sparse_linear`` head, applied on top of XLM-RoBERTa hidden states.

The model is loaded once per process on first call to get_embedding_model().
Subsequent calls return the same instance. Python's GIL and module-level
locking ensure thread safety during lazy initialisation.
"""

from __future__ import annotations

import logging
import threading

import torch

logger = logging.getLogger(__name__)

_model_lock = threading.Lock()
_model_instance: EmbeddingModel | None = None  # populated lazily


class EmbeddingModel:
    """Wraps BGE-M3 to produce dense and sparse embeddings on CPU."""

    def __init__(self, model_name: str) -> None:
        from sentence_transformers import SentenceTransformer

        logger.info(
            "Loading embedding model '%s' (first load may be slow)...",
            model_name,
        )
        self._model = SentenceTransformer(model_name, device="cpu")
        self._model.eval()
        logger.info("Embedding model '%s' loaded.", model_name)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def encode_batch(
        self, texts: list[str], batch_size: int = 16
    ) -> tuple[list[list[float]], list[dict[int, float]]]:
        """Encode *texts* and return (dense_vectors, sparse_vectors).

        Both lists are parallel to *texts*.
        Dense vectors: 1024-dim, L2-normalised.
        Sparse vectors: ``{token_id: weight}`` dicts (non-zero entries only).
        """
        results_dense: list[list[float]] = []
        results_sparse: list[dict[int, float]] = []

        first_module = self._model[0]
        hf_model = getattr(first_module, "auto_model", None)
        tokenizer = getattr(first_module, "tokenizer", None)

        if hf_model is None or tokenizer is None:
            raise RuntimeError(
                "SentenceTransformer does not contain an auto_model/tokenizer."
            )

        sparse_linear: torch.nn.Module | None = getattr(hf_model, "sparse_linear", None)
        if sparse_linear is None:
            raise ValueError(
                "BGE-M3 sparse_linear head not found. "
                "This model requires explicit sparse support and "
                "heuristic fallbacks are not permitted."
            )

        for start in range(0, len(texts), batch_size):
            batch = texts[start : start + batch_size]
            encoded = tokenizer(
                batch,
                padding=True,
                truncation=True,
                max_length=8192,
                return_tensors="pt",
            )
            encoded = {k: v.to("cpu") for k, v in encoded.items()}

            with torch.no_grad():
                # 1. Base transformer forward pass
                output = hf_model(**encoded, return_dict=True)
                hidden: torch.Tensor = output.last_hidden_state  # (B, L, H)

                # 2. Sparse vectors via internal head
                weights: torch.Tensor = torch.relu(sparse_linear(hidden)).squeeze(
                    -1
                )  # (B, L)

                # 3. Dense vectors via SentenceTransformer pooling/norm pipeline
                features = {
                    "token_embeddings": hidden,
                    "attention_mask": encoded["attention_mask"],
                }
                # Pass through the remaining pipeline (Pooling, Normalize)
                for module in self._model[1:]:  # type: ignore
                    features = module(features)

                dense: torch.Tensor = features["sentence_embedding"]

            input_ids: torch.Tensor = encoded["input_ids"]
            attention_mask: torch.Tensor = encoded["attention_mask"]

            for b in range(len(batch)):
                # Store dense
                results_dense.append(dense[b].tolist())

                # Store sparse
                mask = attention_mask[b].bool()
                ids = input_ids[b][mask].tolist()
                ws = weights[b][mask].tolist()

                sparse: dict[int, float] = {}
                for tid, w in zip(ids, ws, strict=True):
                    if w > 0.0 and (tid not in sparse or w > sparse[tid]):
                        # Keep maximum weight when a token appears multiple times
                        sparse[tid] = float(w)
                results_sparse.append(sparse)

        return results_dense, results_sparse


# ------------------------------------------------------------------
# Singleton accessor
# ------------------------------------------------------------------
def get_embedding_model(model_name: str = "BAAI/bge-m3") -> EmbeddingModel:
    """Return the process-wide EmbeddingModel singleton (lazy init)."""
    global _model_instance
    if _model_instance is None:
        with _model_lock:
            if _model_instance is None:
                _model_instance = EmbeddingModel(model_name)
    return _model_instance

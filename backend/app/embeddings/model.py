"""
Lazy singleton wrapper around the BGE-M3 embedding model.
"""

from __future__ import annotations

import logging
import threading

logger = logging.getLogger(__name__)

_model_lock = threading.Lock()
_model_instance: EmbeddingModel | None = None


class EmbeddingModel:
    def __init__(self, model_name: str) -> None:
        from FlagEmbedding import BGEM3FlagModel  # type: ignore
        from huggingface_hub import snapshot_download

        logger.info(f"Loading embedding model '{model_name}'...")
        if model_name != "BAAI/bge-m3":
            raise ValueError(f"Only BAAI/bge-m3 is supported, got {model_name}")

        pinned_sha = "5617a9f61b028005a4858fdac845db406aefb181"
        allow = ["*.json", "*.txt", "*.model", "*.bin", "*.pt", "*.md"]
        model_path = snapshot_download(
            repo_id=model_name,
            revision=pinned_sha,
            allow_patterns=allow,
            ignore_patterns=["*onnx*"],
        )

        self._model = BGEM3FlagModel(model_path, use_fp16=False, device="cpu")
        logger.info(f"Embedding model '{model_name}' loaded.")

    def encode_batch(
        self, texts: list[str], batch_size: int = 16
    ) -> tuple[list[list[float]], list[dict[int, float]]]:
        if not texts:
            return [], []

        output = self._model.encode(
            texts,
            batch_size=batch_size,
            max_length=8192,
            return_dense=True,
            return_sparse=True,
            return_colbert_vecs=False,
        )
        dense_vecs = output.get("dense_vecs")
        lexical_weights = output.get("lexical_weights")
        if dense_vecs is None or lexical_weights is None:
            raise ValueError("BGEM3FlagModel failed to return required outputs.")
        results_dense = [vec.tolist() for vec in dense_vecs]
        results_sparse = []
        for lex_weight in lexical_weights:
            sparse = {int(k): float(v) for k, v in lex_weight.items()}
            results_sparse.append(sparse)
        return results_dense, results_sparse


def get_embedding_model(model_name: str = "BAAI/bge-m3") -> EmbeddingModel:
    global _model_instance
    if _model_instance is None:
        with _model_lock:
            if _model_instance is None:
                _model_instance = EmbeddingModel(model_name)
    return _model_instance

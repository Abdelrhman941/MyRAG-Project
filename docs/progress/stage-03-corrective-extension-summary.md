# Stage 03 Corrective Extension Summary

## What Was Done

1. **Replaced SentenceTransformer with BGEM3FlagModel**:
   - `SentenceTransformer` does not support loading the native BGE-M3 `sparse_linear` weights out of the box because they are separated into a `.pt` file instead of standard HF config blocks.
   - Introduced `FlagEmbedding` library as a dependency to natively support generating sparse vectors using BAAI's `BGEM3FlagModel`.
   - Used `huggingface_hub.snapshot_download` to explicitly pin the model to SHA `5617a9f61b028005a4858fdac845db406aefb181`.
   - Optimized local caching by skipping the massive `.onnx` models (`ignore_patterns=["*onnx*"]`).

2. **Fixed Token Output and Retrieval Format**:
   - `BGEM3FlagModel.encode(return_sparse=True)` yields lexical weights as dictionaries with string keys (e.g. `{"1132": 0.5}`).
   - Cast these string keys to integers empirically to fit Qdrant `SparseVector` integer constraints.

3. **Dependency Conflict Mitigation**:
   - Encountered an `AttributeError` from `transformers.tokenization_utils_base` when passing dictionaries vs lists during `tokenizer.pad()`.
   - Systematically debugged this to a version compatibility bug in `FlagEmbedding` vs `transformers >= 5.x/4.40`.
   - Downgraded to `transformers<4.40` which resolves the strict tokenizer `dict` vs `list` padding constraints correctly.

4. **Testing in Memory**:
   - Edited `verify_retrieval.py` to instantiate `QdrantVectorStore` mapped to `:memory:` and natively bypassed API logic to upsert a test chunk and issue a query.
   - Successfully completed hybrid dense + sparse (RRF) retrieval.

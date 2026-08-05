"""Sentence-embedding generation for CLO/PLO semantic mapping.

Uses `all-MiniLM-L6-v2` (384 dimensions) to match the `vector(384)` columns on
`plos.embedding` and `clos.embedding`.

The model is loaded lazily on first use so importing this module (and therefore
booting the API or collecting tests) never pays the model-load cost.
"""

import asyncio
import threading

MODEL_NAME = "all-MiniLM-L6-v2"
EMBEDDING_DIM = 384

_model = None
_model_lock = threading.Lock()


def get_model():
    """Return the shared SentenceTransformer, loading it on first call."""
    global _model
    if _model is None:
        with _model_lock:
            if _model is None:
                from sentence_transformers import SentenceTransformer

                _model = SentenceTransformer(MODEL_NAME)
    return _model


def encode_text(text: str) -> list[float]:
    """Encode a single string into a normalized 384-dim embedding.

    Normalizing here means cosine distance and L2 distance rank identically,
    and lets `similarity_score` be derived as `1 - cosine_distance`.
    """
    vector = get_model().encode(text, normalize_embeddings=True)
    return [float(value) for value in vector]


async def aencode_text(text: str) -> list[float]:
    """Async wrapper that offloads the CPU-bound encode off the event loop."""
    return await asyncio.to_thread(encode_text, text)

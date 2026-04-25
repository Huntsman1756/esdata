"""Shared embedding utilities for workers.

Uses sentence-transformers with a lightweight multilingual model
for generating text embeddings stored in pgvector columns.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Sequence

logger = logging.getLogger(__name__)

_model: object | None = None


def get_model():
    """Lazy-load the embedding model (singleton)."""
    global _model
    if _model is None:
        try:
            from sentence_transformers import SentenceTransformer
            _model = SentenceTransformer(
                "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2",
                device="cpu",
            )
        except ImportError:
            logger.warning(
                "sentence-transformers not installed. "
                "Install with: pip install sentence-transformers"
            )
            return None
    return _model


def embed_texts(texts: list[str], normalize: bool = True) -> list[list[float]] | None:
    """Generate embeddings for a batch of texts.

    Returns None if the model is not available.
    """
    model = get_model()
    if model is None:
        return None

    if not texts:
        return []

    try:
        import numpy as np
        embeddings = model.encode(
            texts,
            show_progress_bar=False,
            normalize_embeddings=normalize,
            convert_to_numpy=True,
        )
        if isinstance(embeddings, np.ndarray):
            return embeddings.tolist()
        return embeddings  # type: ignore[return-value]
    except Exception:
        logger.exception("Error generating embeddings for %d texts", len(texts))
        return None


def embed_single(text: str) -> list[float] | None:
    """Embed a single text string."""
    if not text or not text.strip():
        return None
    results = embed_texts([text])
    if results is None or len(results) < 1:
        return None
    return results[0]

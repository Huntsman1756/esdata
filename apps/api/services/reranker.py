from __future__ import annotations

import math
import re
from functools import lru_cache
from typing import NamedTuple


MODEL_NAME = "cross-encoder/mmarco-mMiniLMv2-L12-H384-v1"


class RankedChunk(NamedTuple):
    chunk_id: str
    text: str
    source_document: str
    article_number: str | None
    rerank_score: float


def _tokenize(text: str) -> set[str]:
    return {token for token in re.findall(r"[a-z0-9áéíóúñ]+", text.lower()) if token}


def _fallback_score(query: str, text: str) -> float:
    query_tokens = _tokenize(query)
    text_tokens = _tokenize(text)
    if not query_tokens or not text_tokens:
        return 0.0

    overlap = len(query_tokens & text_tokens) / len(query_tokens)
    phrase_bonus = 0.15 if query.lower() in text.lower() else 0.0
    return round(min(1.0, overlap + phrase_bonus), 4)


@lru_cache(maxsize=1)
def _load_model():
    try:
        from sentence_transformers import CrossEncoder

        return CrossEncoder(MODEL_NAME, max_length=512)
    except Exception:
        return None


def rerank(query: str, chunks: list[dict], top_k: int = 5) -> list[RankedChunk]:
    if not chunks:
        return []

    model = _load_model()
    if model is None:
        scores = [_fallback_score(query, chunk["text"]) for chunk in chunks]
    else:
        pairs = [(query, chunk["text"]) for chunk in chunks]
        scores = model.predict(pairs, show_progress_bar=False)

    ranked = sorted(zip(scores, chunks), key=lambda item: float(item[0]), reverse=True)

    return [
        RankedChunk(
            chunk_id=str(chunk["chunk_id"]),
            text=chunk["text"],
            source_document=chunk["source_document"],
            article_number=chunk.get("article_number"),
            rerank_score=float(score),
        )
        for score, chunk in ranked[:top_k]
    ]


def normalize_rerank_score(score: float) -> float:
    if 0.0 <= score <= 1.0:
        return float(score)
    return 1.0 / (1.0 + math.exp(-float(score)))

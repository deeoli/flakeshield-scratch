"""
Embeddings (v0.1)

Goal:
Generate sentence embeddings for failure text so we can compute semantic similarity.

Rules:
- No training, no fine-tuning
- CPU-safe default
- Keep it optional and reversible
"""

from __future__ import annotations

from functools import lru_cache
from typing import Optional, Sequence, List

from sentence_transformers import SentenceTransformer


MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"


@lru_cache(maxsize=1)
def _model() -> SentenceTransformer:
    """
    Cache the model so we load it once per process.
    Loading is expensive; inference is cheap.
    """
    return SentenceTransformer(MODEL_NAME)


def embed_texts(texts: Sequence[str]) -> List[List[float]]:
    """
    Embed a list of texts into vectors.

    Returns:
      List of vectors (each vector is a list of floats).

    Notes:
    - convert_to_numpy=False keeps this dependency-light (plain Python lists).
    """
    m = _model()
    vectors = m.encode(list(texts), normalize_embeddings=True, convert_to_numpy=False)
    # SentenceTransformer may return list[ndarray] or list[list]; ensure pure lists
    return [v.tolist() if hasattr(v, "tolist") else list(v) for v in vectors]


def make_failure_text(message: Optional[str], traceback: Optional[str]) -> Optional[str]:
    """
    Canonical text we embed for a failure.

    Strategy:
    - Prefer (message + traceback) because message alone is often too short/noisy.
    - Return None if both are missing.
    """
    if not message and not traceback:
        return None
    if message and traceback:
        return f"{message}\n{traceback}"
    return message or traceback

"""
Similarity lookup using persisted embeddings (Phase B Step 1).

Pure function for finding similar failure embeddings by cosine similarity.
No writes, no side effects.
"""

import sqlite3
from typing import List, Optional, Tuple

import numpy as np


def _cosine_similarity(a: np.ndarray, b: np.ndarray) -> float:
    """
    Compute cosine similarity between two vectors.

    Args:
        a, b: 1D numpy arrays (float32)

    Returns:
        Cosine similarity score (float, range [-1, 1])
    """
    # Normalize vectors
    a_norm = a / (np.linalg.norm(a) + 1e-10)
    b_norm = b / (np.linalg.norm(b) + 1e-10)
    return float(np.dot(a_norm, b_norm))


def get_top_k_similar(
    conn: sqlite3.Connection,
    vector: np.ndarray,
    model_name: str,
    k: int = 5,
    exclude_fingerprint: Optional[str] = None,
) -> List[Tuple[str, float]]:
    """
    Find top-k most similar failure embeddings by cosine similarity.

    Args:
        conn: SQLite connection (must have failure_embeddings table)
        vector: Query vector (1D float32 numpy array)
        model_name: Embedding model name
        k: Number of top results to return (default 5)
        exclude_fingerprint: Optional fingerprint to exclude from results

    Returns:
        List of (fingerprint, similarity_score) tuples sorted by score DESC.
        If no embeddings exist, returns empty list.

    Side effects:
        None (read-only query)
    """
    cur = conn.cursor()

    # Load all embeddings for this model
    rows = cur.execute(
        "SELECT fingerprint, dim, vector FROM failure_embeddings WHERE model_name = ?",
        (model_name,),
    ).fetchall()

    if not rows:
        return []

    # Compute similarities
    similarities = []

    for fingerprint, dim, blob in rows:
        # Skip excluded fingerprint
        if exclude_fingerprint and fingerprint == exclude_fingerprint:
            continue

        # Reconstruct vector
        try:
            emb_vec = np.frombuffer(blob, dtype=np.float32)

            # Validate dim
            if len(emb_vec) != dim:
                continue  # Skip malformed rows

            # Compute similarity
            score = _cosine_similarity(vector, emb_vec)
            similarities.append((fingerprint, score))

        except (ValueError, TypeError):
            # Skip rows that can't be deserialized
            continue

    # Sort by score descending, take top-k
    similarities.sort(key=lambda x: x[1], reverse=True)
    return similarities[:k]

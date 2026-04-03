"""
Known vs novel failure classification using persisted embeddings.

Pure function for classifying fingerprints as known (embedded) or novel (new).
"""

import sqlite3
from typing import Any, Callable, Dict, List, Tuple


def classify_known_novel(
    conn: sqlite3.Connection,
    failure_groups: Dict[str, Any],
    model_name: str,
    embed_texts: Callable,
    get_embedding: Callable,
    upsert_embedding: Callable,
) -> Tuple[List[str], List[str]]:
    """
    Classify failure fingerprints as known or novel based on embedding persistence.

    Args:
        conn: SQLite connection (not closed by this function)
        failure_groups: dict mapping fingerprint -> {"count": int, "examples": [...]}
        model_name: name of embedding model
        embed_texts: callable(texts: List[str]) -> List[ndarray]
        get_embedding: callable(conn, fingerprint, model_name) -> ndarray or None
        upsert_embedding: callable(conn, fingerprint, model_name, vector) -> None

    Returns:
        (known_failures, novel_failures) - lists of fingerprint strings

    Raises:
        If any embedding/DB operation fails, exception propagates (caller handles).
    """
    known_failures = []
    novel_failures = []

    if not failure_groups:
        return known_failures, novel_failures

    fingerprints = list(failure_groups.keys())
    fps_to_embed = []
    texts_to_embed = []

    # First pass: check which are already persisted
    for fp in fingerprints:
        existing = get_embedding(conn, fp, model_name)
        if existing is not None:
            known_failures.append(fp)
        else:
            # Prepare text for embedding (choose first example message or fallback to fp)
            exs = failure_groups.get(fp, {}).get("examples", [])
            text = exs[0].get("message") if exs else fp

            fps_to_embed.append(fp)
            texts_to_embed.append(text)

    # Second pass: embed and persist novel failures
    if texts_to_embed:
        vecs = embed_texts(texts_to_embed)
        for fp, vec in zip(fps_to_embed, vecs):
            upsert_embedding(conn, fp, model_name, vec)
            novel_failures.append(fp)

    return known_failures, novel_failures

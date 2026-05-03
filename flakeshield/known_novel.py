"""
Known vs novel failure classification using persisted embeddings.

Pure function for classifying fingerprints as known (embedded) or novel (new).
"""

import sqlite3
from typing import Any, Callable, Dict, List, Optional, Tuple


def _fingerprint_in_prior_runs(
    conn: sqlite3.Connection,
    fingerprint: str,
    current_run_ids: frozenset[str],
) -> bool:
    """True if this fingerprint appears in test_results from any run not in the current batch."""
    if not current_run_ids:
        return False
    placeholders = ",".join("?" * len(current_run_ids))
    row = conn.execute(
        f"""
        SELECT 1 FROM test_results
        WHERE fingerprint = ? AND run_id NOT IN ({placeholders})
        LIMIT 1
        """,
        (fingerprint, *current_run_ids),
    ).fetchone()
    return row is not None


def classify_known_novel(
    conn: sqlite3.Connection,
    failure_groups: Dict[str, Any],
    model_name: str,
    embed_texts: Callable,
    get_embedding: Callable,
    upsert_embedding: Callable,
    current_run_ids: Optional[frozenset[str]] = None,
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

    Args:
        current_run_ids: Run IDs in the JUnit batch being analyzed. When set,
            any fingerprint already present in ``test_results`` under a
            different ``run_id`` is treated as **known** (recurring) even if
            the embedding row is missing (e.g. semantic was off in a prior CI
            run). Stops known/novel from flipping when only embeddings are new.

    Returns:
        (known_failures, novel_failures) - lists of fingerprint strings

    Raises:
        If any embedding/DB operation fails, exception propagates (caller handles).
    """
    known_failures: list[str] = []
    novel_failures: list[str] = []

    if not failure_groups:
        return known_failures, novel_failures

    fingerprints = list(failure_groups.keys())
    fps_to_embed: list[str] = []
    texts_to_embed: list[str] = []
    novel_fps_ordered: list[str] = []

    for fp in fingerprints:
        existing = get_embedding(conn, fp, model_name)
        prior_in_db = False
        if current_run_ids:
            prior_in_db = _fingerprint_in_prior_runs(conn, fp, current_run_ids)

        exs = failure_groups.get(fp, {}).get("examples", [])
        text = exs[0].get("message") if exs else fp

        if existing is not None:
            known_failures.append(fp)
        elif prior_in_db:
            known_failures.append(fp)
            fps_to_embed.append(fp)
            texts_to_embed.append(text)
        else:
            novel_fps_ordered.append(fp)
            fps_to_embed.append(fp)
            texts_to_embed.append(text)

    if texts_to_embed:
        vecs = embed_texts(texts_to_embed)
        for fp, vec in zip(fps_to_embed, vecs):
            upsert_embedding(conn, fp, model_name, vec)

    novel_failures.extend(novel_fps_ordered)

    return known_failures, novel_failures

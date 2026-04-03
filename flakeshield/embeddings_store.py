"""
SQLite embedding persistence primitives (v0.1)

Goal:
- Store and retrieve failure embeddings idempotently
- No similarity search or ML inference here; only I/O
- Vectors stored as float32 bytes in BLOB
"""

import sqlite3
from typing import Optional, Union, List

import numpy as np


def upsert_embedding(
    conn: sqlite3.Connection,
    fingerprint: str,
    model_name: str,
    vector: Union[np.ndarray, List[float]],
) -> None:
    """
    Insert or update an embedding in the database.

    Args:
        conn: SQLite connection (must have failure_embeddings table)
        fingerprint: Failure fingerprint (key)
        model_name: Embedding model name (e.g., 'all-MiniLM-L6-v2')
        vector: 1D array-like (numpy array or list of floats)

    Returns:
        None

    Side effects:
        Inserts or updates one row in failure_embeddings.
        On conflict(fingerprint, model_name), updates dim, vector, created_at.
    """
    # Normalize to numpy float32 array
    vec = np.asarray(vector, dtype=np.float32)

    if vec.ndim != 1:
        raise ValueError(f"vector must be 1D; got shape {vec.shape}")

    dim = int(len(vec))
    blob = vec.tobytes()

    cur = conn.cursor()
    cur.execute(
        """
        INSERT INTO failure_embeddings (fingerprint, model_name, dim, vector, created_at)
        VALUES (?, ?, ?, ?, datetime('now'))
        ON CONFLICT(fingerprint, model_name) DO UPDATE SET
            dim = excluded.dim,
            vector = excluded.vector,
            created_at = datetime('now')
        """,
        (fingerprint, model_name, dim, blob),
    )
    conn.commit()


def get_embedding(
    conn: sqlite3.Connection,
    fingerprint: str,
    model_name: str,
) -> Optional[np.ndarray]:
    """
    Retrieve an embedding from the database.

    Args:
        conn: SQLite connection
        fingerprint: Failure fingerprint (key)
        model_name: Embedding model name

    Returns:
        numpy array (float32, 1D) or None if not found

    Raises:
        ValueError: If stored vector size does not match dim column.
    """
    cur = conn.cursor()
    row = cur.execute(
        "SELECT dim, vector FROM failure_embeddings WHERE fingerprint = ? AND model_name = ?",
        (fingerprint, model_name),
    ).fetchone()

    if row is None:
        return None

    dim, blob = row
    vec = np.frombuffer(blob, dtype=np.float32)

    # Validate reconstruction
    if len(vec) != dim:
        raise ValueError(
            f"Vector size mismatch: stored dim={dim}, but blob reconstructed to {len(vec)}"
        )

    return vec

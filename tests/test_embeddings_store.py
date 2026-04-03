"""
Tests for embeddings_store.py

Verify roundtrip, upsert behavior, and error handling.
"""

import pytest
import numpy as np
from pathlib import Path

from flakeshield.embeddings_store import upsert_embedding, get_embedding
from flakeshield.storage import connect


def test_upsert_and_get_embedding(tmp_path):
    """Test inserting and retrieving an embedding."""
    db_path = tmp_path / "test.db"
    conn = connect(str(db_path))

    fingerprint = "test_fp_1"
    model_name = "all-MiniLM-L6-v2"
    vector = np.array([0.1, 0.2, 0.3, 0.4, 0.5], dtype=np.float32)

    # Insert
    upsert_embedding(conn, fingerprint, model_name, vector)

    # Retrieve
    retrieved = get_embedding(conn, fingerprint, model_name)

    assert retrieved is not None
    assert np.allclose(retrieved, vector)

    conn.close()


def test_upsert_overwrites_existing(tmp_path):
    """Test that upsert with same key overwrites the previous value."""
    db_path = tmp_path / "test.db"
    conn = connect(str(db_path))

    fingerprint = "test_fp_2"
    model_name = "all-MiniLM-L6-v2"
    vector_a = np.array([0.1, 0.2], dtype=np.float32)
    vector_b = np.array([0.5, 0.6], dtype=np.float32)

    # Insert first
    upsert_embedding(conn, fingerprint, model_name, vector_a)
    retrieved_a = get_embedding(conn, fingerprint, model_name)
    assert np.allclose(retrieved_a, vector_a)

    # Upsert with different vector
    upsert_embedding(conn, fingerprint, model_name, vector_b)
    retrieved_b = get_embedding(conn, fingerprint, model_name)
    assert np.allclose(retrieved_b, vector_b)

    # Verify only one row exists
    cur = conn.cursor()
    count = cur.execute(
        "SELECT COUNT(*) FROM failure_embeddings WHERE fingerprint = ? AND model_name = ?",
        (fingerprint, model_name),
    ).fetchone()[0]
    assert count == 1

    conn.close()


def test_get_nonexistent_returns_none(tmp_path):
    """Test that getting a nonexistent embedding returns None."""
    db_path = tmp_path / "test.db"
    conn = connect(str(db_path))

    result = get_embedding(conn, "nonexistent_fp", "nonexistent_model")
    assert result is None

    conn.close()


def test_vector_roundtrip_list_input(tmp_path):
    """Test that list input is handled correctly and roundtrips."""
    db_path = tmp_path / "test.db"
    conn = connect(str(db_path))

    fingerprint = "test_fp_3"
    model_name = "all-MiniLM-L6-v2"
    vector_list = [0.7, 0.8, 0.9]

    # Insert as list
    upsert_embedding(conn, fingerprint, model_name, vector_list)

    # Retrieve and compare
    retrieved = get_embedding(conn, fingerprint, model_name)
    assert retrieved is not None
    assert np.allclose(retrieved, np.array(vector_list, dtype=np.float32))

    conn.close()


def test_idempotent_upsert_multiple_times(tmp_path):
    """Test that upserting the same data multiple times is safe."""
    db_path = tmp_path / "test.db"
    conn = connect(str(db_path))

    fingerprint = "test_fp_4"
    model_name = "model_v1"
    vector = np.array([0.2, 0.4, 0.6], dtype=np.float32)

    # Upsert 3 times
    for _ in range(3):
        upsert_embedding(conn, fingerprint, model_name, vector)

    # Should still have 1 row
    cur = conn.cursor()
    count = cur.execute(
        "SELECT COUNT(*) FROM failure_embeddings WHERE fingerprint = ? AND model_name = ?",
        (fingerprint, model_name),
    ).fetchone()[0]
    assert count == 1

    # And it should be retrievable
    retrieved = get_embedding(conn, fingerprint, model_name)
    assert np.allclose(retrieved, vector)

    conn.close()


def test_different_models_different_rows(tmp_path):
    """Test that same fingerprint with different models creates separate rows."""
    db_path = tmp_path / "test.db"
    conn = connect(str(db_path))

    fingerprint = "test_fp_5"
    model_a = "model_a"
    model_b = "model_b"
    vector_a = np.array([0.1, 0.2], dtype=np.float32)
    vector_b = np.array([0.3, 0.4], dtype=np.float32)

    # Insert with different models
    upsert_embedding(conn, fingerprint, model_a, vector_a)
    upsert_embedding(conn, fingerprint, model_b, vector_b)

    # Retrieve both
    retrieved_a = get_embedding(conn, fingerprint, model_a)
    retrieved_b = get_embedding(conn, fingerprint, model_b)

    assert np.allclose(retrieved_a, vector_a)
    assert np.allclose(retrieved_b, vector_b)

    # Verify 2 rows exist
    cur = conn.cursor()
    count = cur.execute(
        "SELECT COUNT(*) FROM failure_embeddings WHERE fingerprint = ?",
        (fingerprint,),
    ).fetchone()[0]
    assert count == 2

    conn.close()


def test_large_embedding_vector(tmp_path):
    """Test storing and retrieving a large embedding (e.g., 384 dims)."""
    db_path = tmp_path / "test.db"
    conn = connect(str(db_path))

    fingerprint = "test_fp_large"
    model_name = "all-MiniLM-L6-v2"
    vector = np.random.rand(384).astype(np.float32)

    # Insert
    upsert_embedding(conn, fingerprint, model_name, vector)

    # Retrieve
    retrieved = get_embedding(conn, fingerprint, model_name)

    assert retrieved is not None
    assert len(retrieved) == 384
    assert np.allclose(retrieved, vector)

    conn.close()

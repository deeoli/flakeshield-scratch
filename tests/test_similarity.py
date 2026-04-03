"""
Tests for similarity.py (Phase B Step 1).

Verify cosine similarity lookup and ranking.
"""

import numpy as np
import pytest

from flakeshield.embeddings_store import upsert_embedding
from flakeshield.similarity import get_top_k_similar
from flakeshield.storage import connect


def test_top_k_ordering(tmp_path):
    """
    Test that top-k results are ordered by similarity (highest first).
    """
    db_path = str(tmp_path / "test_similarity.db")
    conn = connect(db_path)

    model_name = "test-model"

    # Create 3 distinct vectors
    vec_a = np.array([1.0, 0.0, 0.0, 0.0], dtype=np.float32)  # unit vector along x
    vec_b = np.array([0.0, 1.0, 0.0, 0.0], dtype=np.float32)  # unit vector along y
    vec_c = np.array(
        [1.0, 1.0, 0.0, 0.0], dtype=np.float32
    )  # diagonal (45 degrees from x)

    # Insert embeddings
    upsert_embedding(conn, "fp_a", model_name, vec_a)
    upsert_embedding(conn, "fp_b", model_name, vec_b)
    upsert_embedding(conn, "fp_c", model_name, vec_c)

    # Query with a vector very similar to vec_a
    query_vec = np.array([0.9, 0.1, 0.0, 0.0], dtype=np.float32)

    # Get top 3
    results = get_top_k_similar(conn, query_vec, model_name, k=3)

    assert len(results) == 3, f"Expected 3 results, got {len(results)}"

    # Check ordering: should be sorted by similarity DESC
    fp_1, score_1 = results[0]
    fp_2, score_2 = results[1]
    fp_3, score_3 = results[2]

    assert (
        score_1 >= score_2 >= score_3
    ), f"Scores not ordered: {score_1:.4f}, {score_2:.4f}, {score_3:.4f}"

    # At least the first result should be fp_a (closest to query)
    # (exact order of b and c may vary, but a should be highest)
    assert fp_1 == "fp_a", f"Expected fp_a as top result, got {fp_1}"
    assert score_1 > 0.9, f"Expected high similarity for fp_a, got {score_1:.4f}"

    conn.close()


def test_excludes_self(tmp_path):
    """
    Test that exclude_fingerprint parameter works correctly.
    """
    db_path = str(tmp_path / "test_exclude.db")
    conn = connect(db_path)

    model_name = "test-model"

    # Insert 2 embeddings
    vec_a = np.array([1.0, 0.0, 0.0], dtype=np.float32)
    vec_b = np.array([0.9, 0.1, 0.0], dtype=np.float32)  # very close to vec_a

    upsert_embedding(conn, "fp_a", model_name, vec_a)
    upsert_embedding(conn, "fp_b", model_name, vec_b)

    # Query with vec_a, but exclude fp_a
    results = get_top_k_similar(
        conn, vec_a, model_name, k=5, exclude_fingerprint="fp_a"
    )

    # Should only get fp_b
    assert len(results) == 1, f"Expected 1 result after exclusion, got {len(results)}"
    assert results[0][0] == "fp_b", f"Expected fp_b, got {results[0][0]}"

    conn.close()


def test_empty_database(tmp_path):
    """
    Test that empty database returns empty list.
    """
    db_path = str(tmp_path / "test_empty.db")
    conn = connect(db_path)

    model_name = "test-model"
    query_vec = np.ones(4, dtype=np.float32)

    results = get_top_k_similar(conn, query_vec, model_name, k=5)

    assert results == [], f"Expected empty list for empty DB, got {results}"

    conn.close()


def test_k_limits_results(tmp_path):
    """
    Test that k parameter correctly limits results.
    """
    db_path = str(tmp_path / "test_k_limit.db")
    conn = connect(db_path)

    model_name = "test-model"

    # Insert 5 embeddings
    for i in range(5):
        vec = np.random.RandomState(i).rand(8).astype(np.float32)
        upsert_embedding(conn, f"fp_{i}", model_name, vec)

    query_vec = np.ones(8, dtype=np.float32)

    # Test k=2
    results_k2 = get_top_k_similar(conn, query_vec, model_name, k=2)
    assert len(results_k2) == 2, f"Expected 2 results for k=2, got {len(results_k2)}"

    # Test k=10 (more than available)
    results_k10 = get_top_k_similar(conn, query_vec, model_name, k=10)
    assert (
        len(results_k10) == 5
    ), f"Expected 5 results for k=10 (5 available), got {len(results_k10)}"

    conn.close()


def test_different_model_names_isolated(tmp_path):
    """
    Test that embeddings with different model names are isolated.
    """
    db_path = str(tmp_path / "test_models.db")
    conn = connect(db_path)

    model_a = "model-a"
    model_b = "model-b"

    vec = np.ones(4, dtype=np.float32)

    # Insert into model-a
    upsert_embedding(conn, "fp_1", model_a, vec)

    # Query model-b with same vector
    results = get_top_k_similar(conn, vec, model_b, k=5)

    assert (
        results == []
    ), f"Expected no results for model-b (only model-a has embeddings), got {results}"

    # Query model-a
    results = get_top_k_similar(conn, vec, model_a, k=5)

    assert len(results) == 1, f"Expected 1 result for model-a, got {len(results)}"

    conn.close()

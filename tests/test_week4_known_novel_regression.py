"""
Week 4 regression test: Novel becomes known on second run.

Verifies that fingerprints classified as "novel" on the first semantic run
are correctly classified as "known" on a second run with the same database.
"""

import sqlite3

import numpy as np
import pytest

from flakeshield.known_novel import classify_known_novel
from flakeshield.storage import connect


def test_novel_becomes_known_on_second_run(tmp_path, monkeypatch):
    """
    Test that a failure fingerprint transitions from novel (first run)
    to known (second run) when using persisted embeddings.
    """
    # Setup: create temp DB
    db_path = str(tmp_path / "test_week4.db")
    conn = connect(db_path)

    # Prepare a minimal failure_groups structure
    fingerprint = "test_fingerprint_user_not_found"
    failure_groups = {
        fingerprint: {
            "count": 1,
            "examples": [
                {
                    "message": "AssertionError: user not found: id=123",
                    "test_id": "test_users::test_lookup",
                    "run_id": "report_run1.xml",
                }
            ],
        }
    }

    model_name = "test-embedding-model"

    # Mock embed_texts to return a stable, small vector
    def fake_embed_texts(texts):
        """Return stable 8-dim vectors for testing."""
        return [np.ones(8, dtype=np.float32) for _ in texts]

    # Import the functions we need to pass to classify_known_novel
    from flakeshield.embeddings_store import get_embedding, upsert_embedding

    # --- First run: should classify as novel ---
    known1, novel1 = classify_known_novel(
        conn,
        failure_groups,
        model_name,
        embed_texts=fake_embed_texts,
        get_embedding=get_embedding,
        upsert_embedding=upsert_embedding,
    )

    assert fingerprint in novel1, f"Expected {fingerprint} to be novel on run 1"
    assert fingerprint not in known1, f"Expected {fingerprint} NOT to be known on run 1"

    # Verify that 1 row was written to DB
    cur = conn.cursor()
    count1 = cur.execute(
        "SELECT COUNT(*) FROM failure_embeddings WHERE fingerprint=? AND model_name=?",
        (fingerprint, model_name),
    ).fetchone()[0]
    assert count1 == 1, f"Expected 1 embedding row after first run, got {count1}"

    # --- Second run: should classify as known ---
    known2, novel2 = classify_known_novel(
        conn,
        failure_groups,
        model_name,
        embed_texts=fake_embed_texts,
        get_embedding=get_embedding,
        upsert_embedding=upsert_embedding,
    )

    assert fingerprint in known2, f"Expected {fingerprint} to be known on run 2"
    assert fingerprint not in novel2, f"Expected {fingerprint} NOT to be novel on run 2"

    # Verify that still only 1 row exists (upsert, not insert)
    count2 = cur.execute(
        "SELECT COUNT(*) FROM failure_embeddings WHERE fingerprint=? AND model_name=?",
        (fingerprint, model_name),
    ).fetchone()[0]
    assert (
        count2 == 1
    ), f"Expected 1 embedding row after second run (upsert), got {count2}"

    conn.close()


def test_multiple_fingerprints_mixed_known_novel(tmp_path):
    """
    Test that multiple fingerprints are correctly classified as known/novel.
    """
    db_path = str(tmp_path / "test_multi.db")
    conn = connect(db_path)

    fp1 = "fingerprint_error_1"
    fp2 = "fingerprint_error_2"
    fp3 = "fingerprint_error_3"

    failure_groups = {
        fp1: {
            "count": 1,
            "examples": [{"message": "Error 1", "test_id": "t1", "run_id": "r1"}],
        },
        fp2: {
            "count": 1,
            "examples": [{"message": "Error 2", "test_id": "t2", "run_id": "r1"}],
        },
        fp3: {
            "count": 1,
            "examples": [{"message": "Error 3", "test_id": "t3", "run_id": "r1"}],
        },
    }

    model_name = "test-model"

    def fake_embed_texts(texts):
        return [
            np.random.RandomState(i).rand(16).astype(np.float32)
            for i in range(len(texts))
        ]

    from flakeshield.embeddings_store import get_embedding, upsert_embedding

    # First run: all should be novel
    known1, novel1 = classify_known_novel(
        conn,
        failure_groups,
        model_name,
        embed_texts=fake_embed_texts,
        get_embedding=get_embedding,
        upsert_embedding=upsert_embedding,
    )

    assert set(novel1) == {
        fp1,
        fp2,
        fp3,
    }, f"Run 1: expected all novel, got known={known1}, novel={novel1}"
    assert len(known1) == 0, f"Run 1: expected no known, got {known1}"

    # Second run: all should be known
    known2, novel2 = classify_known_novel(
        conn,
        failure_groups,
        model_name,
        embed_texts=fake_embed_texts,
        get_embedding=get_embedding,
        upsert_embedding=upsert_embedding,
    )

    assert set(known2) == {
        fp1,
        fp2,
        fp3,
    }, f"Run 2: expected all known, got known={known2}, novel={novel2}"
    assert len(novel2) == 0, f"Run 2: expected no novel, got {novel2}"

    conn.close()


def test_empty_failure_groups():
    """Test that empty failure_groups returns empty lists."""
    import tempfile

    with tempfile.TemporaryDirectory() as tmp_dir:
        db_path = f"{tmp_dir}/test.db"
        conn = connect(db_path)

        def fake_embed_texts(texts):
            return [np.ones(8, dtype=np.float32) for _ in texts]

        from flakeshield.embeddings_store import get_embedding, upsert_embedding

        known, novel = classify_known_novel(
            conn,
            {},  # empty
            "model",
            embed_texts=fake_embed_texts,
            get_embedding=get_embedding,
            upsert_embedding=upsert_embedding,
        )

        assert known == []
        assert novel == []

        conn.close()

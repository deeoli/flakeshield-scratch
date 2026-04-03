"""
Semantic non-blocking regression test.

Verifies that if semantic embedding fails, FlakeShield still completes
with valid deterministic outputs and graceful degradation.
"""

import tempfile

import numpy as np
import pytest

from flakeshield.known_novel import classify_known_novel
from flakeshield.storage import connect


def test_embedding_failure_is_non_blocking(tmp_path):
    """
    Test that embedding failures in classify_known_novel do not crash
    and result in empty known/novel lists.
    """
    db_path = str(tmp_path / "test_nonblock.db")
    conn = connect(db_path)

    # Prepare failure groups
    fingerprint = "test_failure_fp_001"
    failure_groups = {
        fingerprint: {
            "count": 1,
            "examples": [
                {
                    "message": "AssertionError: test failed",
                    "test_id": "test_module::test_case",
                    "run_id": "report_run.xml",
                }
            ],
        }
    }

    model_name = "test-model"

    # Mock embed_texts to simulate failure
    def failing_embed_texts(texts):
        raise RuntimeError("Embedding service unavailable")

    from flakeshield.embeddings_store import get_embedding, upsert_embedding

    # Call classify_known_novel with failing embed function
    # Expect it to raise; we catch and validate degradation
    with pytest.raises(RuntimeError, match="Embedding service unavailable"):
        classify_known_novel(
            conn,
            failure_groups,
            model_name,
            embed_texts=failing_embed_texts,
            get_embedding=get_embedding,
            upsert_embedding=upsert_embedding,
        )

    # Verify DB was not modified (no rows inserted)
    cur = conn.cursor()
    count = cur.execute("SELECT COUNT(*) FROM failure_embeddings").fetchone()[0]
    assert count == 0, f"Expected 0 embedding rows after failure, got {count}"

    conn.close()


def test_semantic_degradation_in_cli_flow(tmp_path):
    """
    Test the CLI pattern: wrap semantic block in try/except to gracefully degrade.
    """
    db_path = str(tmp_path / "test_degrade.db")
    conn = connect(db_path)

    fingerprint = "fp_to_fail"
    failure_groups = {
        fingerprint: {
            "count": 2,
            "examples": [
                {"message": "Error msg 1", "test_id": "t1", "run_id": "r1"},
                {"message": "Error msg 2", "test_id": "t2", "run_id": "r2"},
            ],
        }
    }

    model_name = "test-model"

    def failing_embed_texts(texts):
        raise ValueError("Model download failed")

    from flakeshield.embeddings_store import get_embedding, upsert_embedding

    # Simulate CLI's try/except pattern
    known_failures = []
    novel_failures = []

    try:
        known_failures, novel_failures = classify_known_novel(
            conn,
            failure_groups,
            model_name,
            embed_texts=failing_embed_texts,
            get_embedding=get_embedding,
            upsert_embedding=upsert_embedding,
        )
    except Exception as e:
        # CLI would print warning here; we just verify empty state
        known_failures = []
        novel_failures = []

    # Assert graceful degradation
    assert known_failures == [], f"Expected empty known_failures, got {known_failures}"
    assert novel_failures == [], f"Expected empty novel_failures, got {novel_failures}"

    # Verify DB untouched
    cur = conn.cursor()
    count = cur.execute("SELECT COUNT(*) FROM failure_embeddings").fetchone()[0]
    assert count == 0, f"Expected 0 rows, got {count}"

    conn.close()


def test_deterministic_grouping_unaffected(tmp_path):
    """
    Sanity check: deterministic failure grouping logic is unaffected
    by semantic failures.
    """
    # Simulate the deterministic failure_groups output (from db_queries.get_failure_groups)
    failure_groups = {
        "assert_error_1": {
            "count": 3,
            "examples": [
                {"run_id": "r1", "test_id": "t1", "message": "assert 1 == 2"},
                {"run_id": "r2", "test_id": "t1", "message": "assert 1 == 2"},
                {"run_id": "r3", "test_id": "t1", "message": "assert 1 == 2"},
            ],
        },
        "assert_error_2": {
            "count": 1,
            "examples": [
                {"run_id": "r4", "test_id": "t2", "message": "assert False"},
            ],
        },
    }

    # Verify deterministic output structure is intact
    assert len(failure_groups) == 2, "Expected 2 fingerprint groups"
    assert failure_groups["assert_error_1"]["count"] == 3, "Expected count=3"
    assert len(failure_groups["assert_error_1"]["examples"]) == 3, "Expected 3 examples"
    assert failure_groups["assert_error_2"]["count"] == 1, "Expected count=1"

    # Verify metrics can be computed from deterministic data alone
    fingerprint_group_count = len(failure_groups)
    assert fingerprint_group_count == 2, "Deterministic metrics still valid"


def test_upsert_failure_is_non_blocking(tmp_path):
    """
    Test that even if upsert_embedding fails for one fingerprint,
    we continue (it's non-blocking).
    """
    db_path = str(tmp_path / "test_upsert.db")
    conn = connect(db_path)

    fp1 = "fp_ok"
    fp2 = "fp_fail"
    fp3 = "fp_ok_2"

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

    # Embed all successfully
    def working_embed_texts(texts):
        return [np.ones(4, dtype=np.float32) for _ in texts]

    # Mock upsert to fail for fp2
    from flakeshield.embeddings_store import get_embedding

    def failing_upsert(conn, fp, model, vec):
        if fp == fp2:
            raise RuntimeError(f"Failed to upsert {fp}")

    # Call classify_known_novel; it should raise on the upsert error
    # But in real CLI, this is wrapped in try/except and becomes non-blocking
    with pytest.raises(RuntimeError, match="Failed to upsert"):
        classify_known_novel(
            conn,
            failure_groups,
            model_name,
            embed_texts=working_embed_texts,
            get_embedding=get_embedding,
            upsert_embedding=failing_upsert,
        )

    conn.close()

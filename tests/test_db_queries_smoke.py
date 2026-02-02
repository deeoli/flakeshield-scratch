import os
import sqlite3

from flakeshield.db_queries import get_failure_groups, get_flaky_tests


def _make_empty_db(tmp_path):
    db_path = tmp_path / "test.db"
    conn = sqlite3.connect(db_path)
    # Create the minimal table expected by db_queries.
    # If your actual schema differs, this test will tell us and we’ll adjust once.
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS test_results (
            run_id TEXT NOT NULL,
            test_id TEXT NOT NULL,
            suite TEXT,
            status TEXT NOT NULL,
            duration_sec REAL,
            failure_type TEXT,
            message TEXT,
            traceback TEXT,
            fingerprint TEXT,
            PRIMARY KEY (run_id, test_id)
        );
        """
    )
    conn.commit()
    return conn


def test_db_queries_empty_db_return_empty(tmp_path):
    conn = _make_empty_db(tmp_path)
    try:
        groups = get_failure_groups(conn, limit=20)
        flakies = get_flaky_tests(conn, min_runs=2)
    finally:
        conn.close()

    assert groups == {} or groups == []
    assert flakies == {}

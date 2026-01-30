"""
DB queries (v0.1)

Read aggregated intelligence from SQLite so reporting does not require XML files.
"""

import sqlite3
from typing import Any


def get_failure_groups(
    conn: sqlite3.Connection, limit: int = 20
) -> dict[str, dict[str, Any]]:
    """
    Group failures by fingerprint directly from the DB.
    Returns:
      { fingerprint: {"count": int, "examples": [{"run_id","test_id","message"}...] } }
    """
    cur = conn.cursor()

    # Top fingerprints by frequency
    rows = cur.execute(
        """
        SELECT fingerprint, COUNT(*) AS cnt
        FROM test_results
        WHERE status IN ('failed','error') AND fingerprint IS NOT NULL
        GROUP BY fingerprint
        ORDER BY cnt DESC
        LIMIT ?
        """,
        (limit,),
    ).fetchall()

    groups: dict[str, dict[str, Any]] = {}

    for fp, cnt in rows:
        ex = cur.execute(
            """
            SELECT run_id, test_id, message
            FROM test_results
            WHERE fingerprint = ?
            ORDER BY run_id
            LIMIT 5
            """,
            (fp,),
        ).fetchall()

        groups[fp] = {
            "count": int(cnt),
            "examples": [{"run_id": r, "test_id": t, "message": m} for (r, t, m) in ex],
        }

    return groups


def get_flaky_tests(conn, min_runs: int = 4):
    """
    Return a dict of flaky tests with confidence metadata.

    A test is flaky if:
      - it has >= min_runs observations
      - it has >1 distinct terminal status (passed/failed/error)

    Returns:
      {
        test_id: {
          "statuses": ["failed","passed"],
          "runs_seen": int,
          "pass_count": int,
          "fail_count": int,
          "flake_rate": float,
          "confidence": "low" | "medium" | "high",
        }
      }
    """
    cur = conn.cursor()
    rows = cur.execute(
        """
        SELECT test_id, status
        FROM test_results
        WHERE status IN ('passed', 'failed', 'error')
        """
    ).fetchall()

    by_test_statuses = {}
    by_test_count = {}
    by_test_pass = {}
    by_test_fail = {}

    for test_id, status in rows:
        by_test_statuses.setdefault(test_id, set()).add(status)
        by_test_count[test_id] = by_test_count.get(test_id, 0) + 1

        if status == "passed":
            by_test_pass[test_id] = by_test_pass.get(test_id, 0) + 1
        else:  # failed or error
            by_test_fail[test_id] = by_test_fail.get(test_id, 0) + 1

    def confidence_level(runs_seen: int) -> str:
        if runs_seen >= 10:
            return "high"
        if runs_seen >= 6:
            return "medium"
        return "low"

    out = {}
    for test_id, statuses in by_test_statuses.items():
        runs_seen = by_test_count.get(test_id, 0)
        if runs_seen < min_runs:
            continue
        if len(statuses) <= 1:
            continue

        pass_count = by_test_pass.get(test_id, 0)
        fail_count = by_test_fail.get(test_id, 0)
        flake_rate = (fail_count / runs_seen) if runs_seen else 0.0

        out[test_id] = {
            "statuses": sorted(list(statuses)),
            "runs_seen": runs_seen,
            "pass_count": pass_count,
            "fail_count": fail_count,
            "flake_rate": flake_rate,
            "confidence": confidence_level(runs_seen),
        }

    return out

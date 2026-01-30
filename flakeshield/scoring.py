"""
Flake scoring (v0.1)

Goal: rank tests by how "flaky" they are using history in SQLite.

Simple heuristic:
- Consider only statuses in {passed, failed, error}
- A test is flaky if it has both pass and fail/error in history
- Score = min(pass_count, fail_or_error_count)
  (bigger means more alternation evidence)
"""

import sqlite3
from typing import List, Tuple


def top_flakiest(
    conn: sqlite3.Connection,
    limit: int = 10,
) -> List[Tuple[str, int, int, int]]:
    """
    Returns list of:
      (test_id, runs_seen, pass_count, fail_or_error_count)
    """
    cur = conn.cursor()

    rows = cur.execute(
        """
        SELECT
          test_id,
          COUNT(DISTINCT run_id) AS runs_seen,
          SUM(CASE WHEN status = 'passed' THEN 1 ELSE 0 END) AS pass_count,
          SUM(CASE WHEN status IN ('failed', 'error') THEN 1 ELSE 0 END) AS fail_count
        FROM test_results
        WHERE status IN ('passed', 'failed', 'error')
        GROUP BY test_id
        HAVING pass_count > 0 AND fail_count > 0
        ORDER BY MIN(pass_count, fail_count) DESC, runs_seen DESC
        LIMIT ?
        """,
        (limit,),
    ).fetchall()

    return rows

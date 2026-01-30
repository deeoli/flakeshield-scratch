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

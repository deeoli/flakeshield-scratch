"""Simple deterministic regression detection.

This module provides a helper for identifying fingerprints that began failing in
"current" run but were not failing in the immediately preceding run.  It is
entirely deterministic and relies solely on the existing ``test_results``
table; no semantic components are involved.
"""

from __future__ import annotations

import sqlite3
from typing import Iterable, List, Dict


def detect_regressions(
    conn: sqlite3.Connection, runs_considered: Iterable[str]
) -> List[Dict[str, str]]:
    """Return list of regression records for the latest run.

    ``runs_considered`` should be the ordered list of run_id values that were
    just inserted/processed (the same list stored in the JSON report under
    ``runs_considered``).  If fewer than two runs are provided, the function
    returns an empty list.

    The output format is:

        [
          {"fingerprint": fp, "since_run": prev_run, "current_run": cur_run},
          ...
        ]

    ``fingerprint`` values are sorted alphabetically for deterministic
    output.
    """

    ids = list(runs_considered)
    if len(ids) < 2:
        return []
    prev_run = ids[-2]
    cur_run = ids[-1]

    cur = conn.cursor()
    cur.execute(
        """
        SELECT DISTINCT fingerprint
        FROM test_results
        WHERE run_id = ? AND status IN ('failed','error') AND fingerprint IS NOT NULL
        """,
        (cur_run,),
    )
    cur_failures = {row[0] for row in cur.fetchall()}

    cur.execute(
        """
        SELECT DISTINCT fingerprint
        FROM test_results
        WHERE run_id = ? AND status IN ('failed','error') AND fingerprint IS NOT NULL
        """,
        (prev_run,),
    )
    prev_failures = {row[0] for row in cur.fetchall()}

    new = sorted(cur_failures - prev_failures)
    return [
        {"fingerprint": fp, "since_run": prev_run, "current_run": cur_run} for fp in new
    ]

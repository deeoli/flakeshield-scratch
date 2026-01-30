"""
FlakeShield storage (SQLite) — v0.1

Goal:
- Persist parsed test cases so we can do history, trends, and scoring later.
- Keep it minimal: one SQLite file, one table, simple inserts.
"""

import sqlite3
from typing import Iterable

from flakeshield.contracts import Runs


SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS test_results (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  run_id TEXT NOT NULL,
  suite TEXT,
  test_id TEXT NOT NULL,
  status TEXT NOT NULL,
  duration_sec REAL,
  failure_type TEXT,
  message TEXT,
  traceback TEXT,
  fingerprint TEXT
);

CREATE INDEX IF NOT EXISTS idx_test_results_run_id ON test_results(run_id);
CREATE INDEX IF NOT EXISTS idx_test_results_test_id ON test_results(test_id);
CREATE INDEX IF NOT EXISTS idx_test_results_status ON test_results(status);
"""


def connect(db_path: str) -> sqlite3.Connection:
    conn = sqlite3.connect(db_path)
    conn.executescript(SCHEMA_SQL)
    conn.commit()
    return conn


def iter_rows(runs: Runs) -> Iterable[tuple]:
    for run in runs:
        for case in run["cases"]:
            yield (
                case["run_id"],
                case.get("suite"),
                case["test_id"],
                case["status"],
                case.get("duration_sec"),
                case.get("failure_type"),
                case.get("message"),
                case.get("traceback"),
                case.get("fingerprint"),
            )


def insert_runs(conn: sqlite3.Connection, runs: Runs) -> int:
    rows = list(iter_rows(runs))
    conn.executemany(
        """
        INSERT INTO test_results (
          run_id, suite, test_id, status, duration_sec,
          failure_type, message, traceback, fingerprint
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        rows,
    )
    conn.commit()
    return len(rows)

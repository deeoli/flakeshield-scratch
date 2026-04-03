import sqlite3
from flakeshield.regressions import detect_regressions
from flakeshield.storage import connect, insert_runs


def make_run(run_id, fps):
    # fps is iterable of fingerprint strings that will be marked failed
    return {
        "run_id": run_id,
        "cases": [
            {
                "run_id": run_id,
                "test_id": f"t{idx}",
                "status": "failed",
                "fingerprint": fp,
            }
            for idx, fp in enumerate(fps)
        ],
    }


def test_regressions_empty_with_one_run(tmp_path):
    db = str(tmp_path / "fs.db")
    conn = connect(db)
    try:
        # insert a single run with one failure
        insert_runs(conn, [make_run("r1", ["fpA"])])
        regs = detect_regressions(conn, ["r1"])
        assert regs == []
    finally:
        conn.close()


def test_new_failure_is_regression(tmp_path):
    db = str(tmp_path / "fs.db")
    conn = connect(db)
    try:
        insert_runs(conn, [make_run("r1", ["fpA"])])
        insert_runs(conn, [make_run("r2", ["fpA", "fpB"])])
        regs = detect_regressions(conn, ["r1", "r2"])
        assert regs == [{"fingerprint": "fpB", "since_run": "r1", "current_run": "r2"}]
    finally:
        conn.close()


def test_failure_becoming_passed_is_not_regression(tmp_path):
    db = str(tmp_path / "fs.db")
    conn = connect(db)
    try:
        insert_runs(conn, [make_run("r1", ["fpA"])])
        # current run has the same fp but status passed
        conn.execute(
            "INSERT OR IGNORE INTO test_results (run_id, suite, test_id, status, fingerprint) VALUES (?,?,?,?,?)",
            ("r2", None, "t0", "passed", "fpA"),
        )
        conn.commit()
        regs = detect_regressions(conn, ["r1", "r2"])
        assert regs == []
    finally:
        conn.close()

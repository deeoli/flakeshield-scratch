#!/usr/bin/env python3
"""
Minimal external simulation harness to stress-test FlakeShield decision quality.
No production/schema/contract changes. Generates JUnit XML, runs FlakeShield,
computes metrics vs ground truth. Output to stdout only.
"""

import json
import os
import subprocess
import sys
from pathlib import Path
import glob

# Ground-truth fingerprints (computed via same logic as FlakeShield)
from flakeshield.fingerprint import fingerprint_failure
from xml.sax import saxutils

# --- Constants ---
OUT_DIR = Path(__file__).resolve().parent / "out"
NUM_RUNS = 10
TESTS_PER_RUN = 10  # 8-12 range: 10

# Distinct messages so fingerprints are stable
FLAKY_MESSAGE = "AssertionError: flaky condition failed"
FLAKY_TRACEBACK = "  File <path>:<n>, in test_flaky"
RECURRING_MESSAGE = "AssertionError: recurring regression timeout"
RECURRING_TRACEBACK = "  File <path>:<n>, in test_recurring"
NOVEL_MESSAGE = "AssertionError: novel bug connection refused"
NOVEL_TRACEBACK = "  File <path>:<n>, in test_novel"


def build_ground_truth():
    truth = {
        "flaky_fingerprints": {fingerprint_failure(FLAKY_MESSAGE, FLAKY_TRACEBACK)},
        "recurring_fingerprints": {
            fingerprint_failure(RECURRING_MESSAGE, RECURRING_TRACEBACK)
        },
        "novel_fingerprints": {fingerprint_failure(NOVEL_MESSAGE, NOVEL_TRACEBACK)},
    }
    return truth


def emit_junit_xml(run_index: int, out_path: Path) -> None:
    """Write one minimal JUnit XML file for this run (1-based run_index)."""
    run_id = run_index  # 1..10
    cases = []

    # Always-pass tests (fill up to TESTS_PER_RUN)
    for i in range(TESTS_PER_RUN - 3):
        cases.append(
            f'    <testcase classname="sim.suite" name="test_pass_{i}" time="0.01"/>'
        )

    # Flaky: fail on even runs only (2,4,6,8,10)
    if run_id % 2 == 0:
        cases.append(
            f'    <testcase classname="sim.suite" name="test_flaky" time="0.01">'
            + f'<failure message="{saxutils.escape(FLAKY_MESSAGE)}">{saxutils.escape(FLAKY_TRACEBACK)}</failure>'
            + f"</testcase>"
        )
    else:
        cases.append(
            '    <testcase classname="sim.suite" name="test_flaky" time="0.01"/>'
        )

    # Recurring: fail on runs 1-8
    if run_id <= 8:
        cases.append(
            f'    <testcase classname="sim.suite" name="test_recurring" time="0.01">'
            + f'<failure message="{saxutils.escape(RECURRING_MESSAGE)}">{saxutils.escape(RECURRING_TRACEBACK)}</failure>'
            + f"</testcase>"
        )
    else:
        cases.append(
            '    <testcase classname="sim.suite" name="test_recurring" time="0.01"/>'
        )

    # Novel: fail on runs 9-10 only
    if run_id >= 9:
        cases.append(
            f'    <testcase classname="sim.suite" name="test_novel" time="0.01">'
            + f'<failure message="{saxutils.escape(NOVEL_MESSAGE)}">{saxutils.escape(NOVEL_TRACEBACK)}</failure>'
            + f"</testcase>"
        )
    else:
        cases.append(
            '    <testcase classname="sim.suite" name="test_novel" time="0.01"/>'
        )

    xml = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        "<testsuites>\n"
        f'  <testsuite name="sim" tests="{len(cases)}" failures="{sum(1 for c in cases if "<failure" in c)}">\n'
        + "\n".join(cases)
        + "\n  </testsuite>\n"
        "</testsuites>\n"
    )
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(xml, encoding="utf-8")


def generate_run_files() -> list[Path]:
    """Write run_01.xml ... run_10.xml; return list of paths created."""
    created = []
    for i in range(1, NUM_RUNS + 1):
        p = OUT_DIR / f"run_{i:02d}.xml"
        emit_junit_xml(i, p)
        created.append(p)
    return created


def run_flakeshield(deterministic_only: bool) -> bool:
    """Run FlakeShield; if deterministic_only False, try semantic. Return True if semantic succeeded."""
    # Use a glob pattern for reports; build_reports will expand it internally.
    reports = str(OUT_DIR / "run_*.xml")
    out_prefix = str(OUT_DIR / "flake_report")
    db_path = str(OUT_DIR / "flakeshield.db")

    # Print which Python interpreter we are using for visibility
    print("Using Python:", sys.executable)

    # Build base command; pass the glob pattern as a single argument.
    cmd = [
        sys.executable,
        "-m",
        "flakeshield.cli",
        "--reports",
        reports,
        "--out",
        out_prefix,
        "--db",
        db_path,
    ]

    try:
        subprocess.run(cmd, check=True, capture_output=True, timeout=120)
    except subprocess.CalledProcessError as e:
        # Print stdout/stderr to aid debugging, then re-raise
        print("FlakeShield deterministic run failed", file=sys.stderr)
        print(e.stdout.decode(errors="ignore"), file=sys.stderr)
        print(e.stderr.decode(errors="ignore"), file=sys.stderr)
        raise

    if deterministic_only:
        return False

    cmd_semantic = cmd + ["--enable-semantic"]
    try:
        result = subprocess.run(cmd_semantic, capture_output=True, timeout=180)
        if result.returncode != 0:
            print("FlakeShield semantic run failed", file=sys.stderr)
            print(result.stdout.decode(errors="ignore"), file=sys.stderr)
            print(result.stderr.decode(errors="ignore"), file=sys.stderr)
        return result.returncode == 0
    except subprocess.CalledProcessError as e:
        print(
            "FlakeShield semantic run failed with CalledProcessError", file=sys.stderr
        )
        print(e.stdout.decode(errors="ignore"), file=sys.stderr)
        print(e.stderr.decode(errors="ignore"), file=sys.stderr)
        return False


def load_and_rank(json_path: Path) -> list[str]:
    """Load report JSON and return ordered list of fingerprints (top first)."""
    data = json.loads(json_path.read_text(encoding="utf-8"))
    risk = data.get("risk_assessment") or {}
    failure_groups = data.get("failure_groups") or {}
    novel_list = data.get("novel_failures") or []

    if risk:
        # Sort descending by risk_score
        order = sorted(
            risk.keys(),
            key=lambda fp: float(risk[fp].get("risk_score", 0.0)),
            reverse=True,
        )
        return order

    # Fallback: novel first, then by failure_groups count descending
    def rank_key(fp):
        in_novel = 1 if fp in novel_list else 0
        count = failure_groups.get(fp, {}).get("count", 0)
        return (-in_novel, -count)

    all_fps = set(failure_groups.keys()) | set(novel_list)
    return sorted(all_fps, key=rank_key)


def compute_metrics(ranked: list[str], truth: dict) -> dict:
    """Compute novel_in_top3_rate, avg_rank_recurring, high_risk_false_positive_rate."""
    top3 = set(ranked[:3]) if len(ranked) >= 3 else set(ranked)
    novel_truth = truth["novel_fingerprints"]
    recurring_truth = truth["recurring_fingerprints"]

    novel_in_top3 = len(top3 & novel_truth)
    novel_in_top3_rate = novel_in_top3 / 3.0 if len(top3) == 3 else 0.0

    ranks_recurring = []
    for fp in recurring_truth:
        try:
            idx = ranked.index(fp)
            ranks_recurring.append(idx + 1)  # 1-based rank
        except ValueError:
            pass
    avg_rank_recurring = (
        sum(ranks_recurring) / len(ranks_recurring) if ranks_recurring else float("nan")
    )

    # Top-3 that are NOT novel AND NOT recurring (e.g. flaky or other)
    fp_false_positive = top3 - novel_truth - recurring_truth
    high_risk_false_positive_rate = (
        len(fp_false_positive) / 3.0 if len(top3) == 3 else 0.0
    )

    return {
        "novel_in_top3_rate": novel_in_top3_rate,
        "avg_rank_recurring": avg_rank_recurring,
        "high_risk_false_positive_rate": high_risk_false_positive_rate,
    }


def main() -> None:
    os.chdir(Path(__file__).resolve().parents[2])  # repo root

    truth = build_ground_truth()
    created = generate_run_files()

    print("Paths created (XML):")
    for p in created:
        print(f"  {p}")

    print("\nRunning FlakeShield (deterministic)...")
    run_flakeshield(deterministic_only=True)

    print("Running FlakeShield (semantic, optional)...")
    semantic_ok = run_flakeshield(deterministic_only=False)
    print(f"Semantic run succeeded: {semantic_ok}")

    json_path = OUT_DIR / "flake_report.json"
    if not json_path.exists():
        print("ERROR: flake_report.json not found", file=sys.stderr)
        sys.exit(1)

    ranked = load_and_rank(json_path)
    metrics = compute_metrics(ranked, truth)

    print("\nTop-5 ranked fingerprints:")
    for i, fp in enumerate(ranked[:5], start=1):
        print(f"  {i}. {fp[:80]}{'...' if len(fp) > 80 else ''}")

    print("\nMetrics:")
    print(f"  novel_in_top3_rate: {metrics['novel_in_top3_rate']:.4f}")
    print(f"  avg_rank_recurring: {metrics['avg_rank_recurring']}")
    print(
        f"  high_risk_false_positive_rate: {metrics['high_risk_false_positive_rate']:.4f}"
    )

    # List all files in out/ for return
    all_out = sorted(OUT_DIR.iterdir(), key=lambda p: p.name)
    print("\nAll files in tools/simulation/out/:")
    for p in all_out:
        print(f"  {p}")


if __name__ == "__main__":
    main()

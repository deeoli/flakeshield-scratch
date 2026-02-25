import json
import sqlite3
from flakeshield.pr_summary import render_pr_summary


def test_renders_without_semantic_fields():
    # minimal report with no semantic/risk information should not crash and
    # produce a sensible placeholder.
    report = {
        "runs_considered": ["r1", "r2"],
        "run_count": 2,
        "flaky_tests": {},
        "failure_groups": {},
        "metrics": {},
    }
    md = render_pr_summary(report)
    assert isinstance(md, str)
    assert "No issues" in md


def test_includes_flaky_and_regressions_when_present(tmp_path):
    report = {
        "flaky_tests": {
            "test.foo": {"flake_rate": 0.33, "runs_seen": 3},
            "test.bar": {"flake_rate": 0.50, "runs_seen": 2},
        },
        "risk_assessment": {"fp1": "HIGH", "fp2": "LOW"},
        "regressions": [
            {"fingerprint": "fpA", "since_run": "r1", "current_run": "r2"},
            {"fingerprint": "fpB", "since_run": "r1", "current_run": "r2"},
        ],
        "novel_failures": ["fpX", "fpY"],
    }
    md = render_pr_summary(report)
    # flaky tests section
    assert "Flaky tests" in md
    assert "test.bar" in md and "test.foo" in md
    # risk section should include only HIGH? our implementation prints all
    assert "High risk failures" in md
    assert "fp1" in md
    # regressions
    assert "Regressions" in md and "fpA" in md
    # novel
    assert "Novel failures" in md and "fpX" in md


def test_cli_pr_summary(tmp_path):
    # exercise the new CLI entry point
    json_path = tmp_path / "report.json"
    out_path = tmp_path / "pr.md"
    sample = {"flaky_tests": {"t": {"flake_rate": 0.1, "runs_seen": 1}}}
    json_path.write_text(json.dumps(sample))
    from flakeshield.cli import main
    # simulate command line invocation
    import sys
    old_argv = sys.argv
    sys.argv = ["flakeshield", "pr-summary", "--json", str(json_path), "--out", str(out_path)]
    try:
        main()
    finally:
        sys.argv = old_argv
    assert out_path.exists()
    assert "Flaky tests" in out_path.read_text()

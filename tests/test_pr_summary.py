import json
import sqlite3
from flakeshield.pr_summary import render_pr_summary


def test_renders_without_semantic_fields():
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


def test_includes_flaky_and_fix_first_when_present(tmp_path):
    report = {
        "run_count": 3,
        "flaky_tests": {
            "test.foo": {"flake_rate": 0.33, "runs_seen": 3},
            "test.bar": {"flake_rate": 0.50, "runs_seen": 2},
        },
        "failure_groups": {
            "timeout fp": {
                "count": 2,
                "examples": [
                    {
                        "run_id": "r1",
                        "test_id": "test.foo",
                        "message": "TimeoutError: request timed out",
                    }
                ],
            }
        },
        "risk_assessment": {
            "timeout fp": {"risk_tier": "HIGH", "risk_score": 0.85, "reasons": {}},
            "fp2": {"risk_tier": "LOW", "risk_score": 0.10, "reasons": {}},
        },
        "regressions": [
            {"fingerprint": "fpA", "since_run": "r1", "current_run": "r2"},
        ],
        "novel_failures": ["fpX"],
        "overview": {
            "total_tests": 10,
            "failures": 2,
            "flaky_tests": 2,
            "failure_groups": 2,
        },
    }
    md = render_pr_summary(report)
    assert "Top Issues To Fix" in md
    assert "Network timeout while calling task service" in md
    assert "Status:" in md
    assert "Risk:" in md
    assert "Flaky tests" in md
    assert "Overview" in md
    assert "Suggested Next Steps" in md


def test_cli_pr_summary(tmp_path):
    json_path = tmp_path / "report.json"
    out_path = tmp_path / "pr.md"
    sample = {"flaky_tests": {"t": {"flake_rate": 0.1, "runs_seen": 1}}}
    json_path.write_text(json.dumps(sample))
    from flakeshield.cli import main

    import sys

    old_argv = sys.argv
    sys.argv = [
        "flakeshield",
        "pr-summary",
        "--json",
        str(json_path),
        "--out",
        str(out_path),
    ]
    try:
        main()
    finally:
        sys.argv = old_argv
    assert out_path.exists()
    assert "FlakeShield" in out_path.read_text()


def test_fix_first_fallback_to_regressions():
    report = {
        "flaky_tests": {},
        "failure_groups": {},
        "regressions": [{"fingerprint": "fpA", "since_run": "r1"}],
    }
    md = render_pr_summary(report)
    assert "Regressions" in md
    assert "since r1" in md

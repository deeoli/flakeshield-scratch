"""Tests for actionable markdown UX helpers."""

from flakeshield.report_ux import (
    build_fix_first_item,
    build_fix_first_list,
    compute_overview_metrics,
    failure_status,
    human_title,
    suggested_next_steps,
    why_this_matters_text,
)


def test_human_title_timeout():
    assert human_title(message="TimeoutError: request timed out after 30s") == (
        "Network timeout while calling task service"
    )


def test_human_title_race():
    assert human_title(message="race condition detected in async fetch") == (
        "Race condition in task fetch"
    )


def test_human_title_assertion():
    title = human_title(message="AssertionError: expected 200, got 500")
    assert title.startswith("Assertion mismatch:")


def test_human_title_connection():
    assert human_title(message="Connection refused to localhost:8080") == (
        "Connection failure to dependency"
    )


def test_human_title_fallback_test_id():
    assert human_title(test_id="tests::test_user_login_flow") == "Test user login flow"


def test_failure_status_new():
    assert (
        failure_status(
            is_novel=True, is_flaky_related=False, group_count=1, seen_runs=1
        )
        == "New"
    )


def test_failure_status_flaky():
    assert (
        failure_status(
            is_novel=False, is_flaky_related=True, group_count=3, seen_runs=3
        )
        == "Flaky"
    )


def test_failure_status_recurring():
    assert (
        failure_status(
            is_novel=False, is_flaky_related=False, group_count=4, seen_runs=2
        )
        == "Recurring"
    )


def test_compute_overview_metrics():
    runs = [
        {
            "cases": [
                {"test_id": "a", "status": "passed"},
                {"test_id": "b", "status": "failed"},
            ]
        },
        {
            "cases": [
                {"test_id": "a", "status": "failed"},
                {"test_id": "c", "status": "passed"},
            ]
        },
    ]
    overview = compute_overview_metrics(runs, failure_groups={"fp1": {}}, flaky_tests={"b": {}})
    assert overview["total_tests"] == 3
    assert overview["failures"] == 2
    assert overview["flaky_tests"] == 1
    assert overview["failure_groups"] == 1


def test_suggested_next_steps_timeout_and_race():
    items = [
        {
            "title": "Network timeout while calling task service",
            "message": "timeout",
            "fingerprint": "timeout",
        },
        {"title": "Race condition in task fetch", "message": "async race"},
    ]
    steps = suggested_next_steps(items)
    assert "Investigate service availability and retry behavior" in steps
    assert "Review async synchronization and timing dependencies" in steps
    assert len(steps) <= 3


def test_build_fix_first_list_from_failure_groups_without_risk():
    groups = {
        "timeout fp": {
            "count": 3,
            "examples": [
                {
                    "run_id": "r1",
                    "test_id": "t1",
                    "message": "TimeoutError: request timed out",
                }
            ],
        }
    }
    items = build_fix_first_list(groups, {}, {}, total_runs=2)
    assert len(items) == 1
    assert items[0]["title"] == "Network timeout while calling task service"
    assert items[0]["status"] in {"New", "Recurring"}


def test_why_this_matters_recurring():
    text = why_this_matters_text("Recurring", flake_rate=0.8)
    assert "Most common failure cluster" in text

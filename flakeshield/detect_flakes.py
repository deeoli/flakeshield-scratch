"""
FlakeShield — Flake Detection v0.1

Rule:
A test is flaky if its status differs across runs.
"""

from typing import Dict, List, Set


def detect_flaky_tests(runs: List[Dict]) -> Dict[str, Set[str]]:
    """
    Input:
      runs = list of parsed run dicts (output of parse_junit)

    Output:
      {
        test_id: {status1, status2, ...}
      }
      Only includes tests with >1 unique status.
    """
    history: Dict[str, Set[str]] = {}

    for run in runs:
        for case in run["cases"]:
            test_id = case["test_id"]
            status = case["status"]

            history.setdefault(test_id, set()).add(status)

    # Keep only tests whose status changes
    flaky = {
        test_id: statuses
        for test_id, statuses in history.items()
        if len(statuses) > 1
    }

    return flaky

"""
Failure grouping (v0.1)

Group failing tests by a normalized fingerprint of their error text.
This reduces CI noise by collapsing repeated failures into root causes.
"""

from flakeshield.contracts import Runs
from collections import defaultdict
from typing import Any, Dict, List

from flakeshield.fingerprint import fingerprint_failure


def group_failures(runs: Runs) -> dict[str, dict]:
    """
    Returns:
      {
        fingerprint: {
          "count": int,
          "examples": [
             {"test_id": "...", "run_id": "...", "message": "..."}
          ]
        }
      }
    """
    groups: Dict[str, Dict[str, Any]] = defaultdict(
        lambda: {"count": 0, "examples": []}
    )

    for run in runs:
        for case in run["cases"]:
            status = case["status"]
            if status not in ("failed", "error"):
                continue

            fp = fingerprint_failure(
                case.get("message"),
                case.get("traceback"),
            )

            if fp is None:
                fp = "<no-fingerprint>"

            groups[fp]["count"] += 1

            if len(groups[fp]["examples"]) < 5:
                groups[fp]["examples"].append(
                    {
                        "test_id": case["test_id"],
                        "run_id": case["run_id"],
                        "message": case.get("message"),
                    }
                )

    return dict(groups)

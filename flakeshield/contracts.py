"""
FlakeShield internal data contracts.

These structures define the stable shape of data passed
between ingestion, analysis, and reporting.
"""

from typing import Dict, List, Optional, TypedDict


class TestCase(TypedDict):
    run_id: str
    suite: Optional[str]
    test_id: str
    status: str  # passed | failed | error | skipped
    duration_sec: Optional[float]
    failure_type: Optional[str]
    message: Optional[str]
    traceback: Optional[str]
    fingerprint: Optional[str]


class TestRun(TypedDict):
    run_id: str
    suite: Optional[str]
    cases: List[TestCase]


Runs = List[TestRun]

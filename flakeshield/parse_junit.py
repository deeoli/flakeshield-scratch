"""
FlakeShield — Pytest JUnit XML Parser (v0.1)

Purpose:
- Translate Pytest's JUnit XML output into FlakeShield's
  canonical minimal schema.
- This file is deliberately boring, explicit, and readable.
- No ML, no heuristics, no cleverness — just deterministic parsing.

Why this matters:
- Stable ingestion is the foundation of reliable CI intelligence.
- If this breaks, everything downstream becomes untrustworthy.
"""

from __future__ import annotations

import json
import os
import sys
import xml.etree.ElementTree as ET
from typing import Any, Dict, List, Optional


def _text(el: Optional[ET.Element]) -> Optional[str]:
    """
    Safely extract inner text from an XML element.

    Why:
    - JUnit failure/error elements often contain multi-line text
      (tracebacks, assertions).
    - We want the raw text, trimmed, or None if empty.
    """
    if el is None:
        return None

    # itertext() walks all nested text nodes
    txt = "".join(el.itertext()).strip()
    return txt or None


def parse_pytest_junit(xml_path: str) -> Dict[str, Any]:
    """
    Parse a Pytest-generated JUnit XML file into FlakeShield schema.

    Input:
    - Path to a single JUnit XML file (one test run)

    Output:
    {
      "run_id": "...",
      "suite": "...",
      "cases": [ {testcase schema}, ... ]
    }

    Design rules:
    - Never throw away information silently
    - Missing optional fields must not crash parsing
    - Status detection must be deterministic
    """
    # Load and parse XML
    tree = ET.parse(xml_path)
    root = tree.getroot()

    # Pytest usually wraps everything in <testsuites><testsuite>
    # but sometimes the root is directly <testsuite>
    testsuite = root.find("testsuite")
    if testsuite is None:
        if root.tag == "testsuite":
            testsuite = root
        else:
            raise ValueError("Could not find <testsuite> element in XML.")

    # Run-level metadata
    run_id = os.path.basename(xml_path)  # stable, reproducible
    suite = testsuite.attrib.get("name")

    cases: List[Dict[str, Any]] = []

    # Iterate through each test case in the suite
    for tc in testsuite.findall("testcase"):
        classname = tc.attrib.get("classname", "")
        name = tc.attrib.get("name", "")

        # Stable identity across runs
        test_id = f"{classname}::{name}".strip("::")

        # Status is inferred from child tags
        failure = tc.find("failure")
        error = tc.find("error")
        skipped = tc.find("skipped")

        if failure is not None:
            status = "failed"
            message = failure.attrib.get("message")
            failure_type = failure.attrib.get("type")
            traceback = _text(failure)

        elif error is not None:
            status = "error"
            message = error.attrib.get("message")
            failure_type = error.attrib.get("type")
            traceback = _text(error)

        elif skipped is not None:
            status = "skipped"
            message = skipped.attrib.get("message")
            failure_type = skipped.attrib.get("type")
            # Keeping skipped text helps humans understand why
            traceback = _text(skipped)

        else:
            # No child tags → test passed
            status = "passed"
            message = None
            failure_type = None
            traceback = None

        # Duration is useful for flake patterns but not mandatory
        time_str = tc.attrib.get("time")
        duration_sec = float(time_str) if time_str is not None else None

        # Append canonical testcase record
        cases.append(
            {
                "run_id": run_id,
                "suite": suite,
                "test_id": test_id,
                "status": status,
                "duration_sec": duration_sec,
                "failure_type": failure_type,
                "message": message,
                "traceback": traceback,
                "fingerprint": None,  # derived later (grouping step)
            }
        )

    return {
        "run_id": run_id,
        "suite": suite,
        "cases": cases,
    }


def main() -> int:
    print("DEBUG: main() started")

    """
    CLI entrypoint.

    Usage:
        python parse_junit.py report.xml

    Prints parsed JSON to stdout.
    """
    if len(sys.argv) != 2:
        print("Usage: python parse_junit.py path/to/report.xml", file=sys.stderr)
        return 2

    xml_path = sys.argv[1]
    data = parse_pytest_junit(xml_path)

    # Pretty-print JSON so humans can inspect it
    print(json.dumps(data, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""
Tests for JUnit XML parsing functionality.

Tests both single <testsuite> format (pytest) and multi-<testsuite> format (Vitest/Jest).
"""

import os
import tempfile
import xml.etree.ElementTree as ET
from pathlib import Path

from flakeshield.parse_junit import parse_pytest_junit


def test_parse_single_testsuite_root():
    """Test parsing pytest-style single <testsuite> root."""
    xml_content = """<?xml version="1.0" encoding="utf-8"?>
<testsuite name="test_suite" tests="2" failures="0" errors="0" skipped="0" time="0.123">
    <testcase classname="TestClass" name="test_passed" time="0.045">
    </testcase>
    <testcase classname="TestClass" name="test_failed" time="0.078">
        <failure message="Assertion failed" type="AssertionError">Traceback here</failure>
    </testcase>
</testsuite>"""

    import tempfile
    import os
    with tempfile.NamedTemporaryFile(mode='w', suffix='.xml', delete=False) as f:
        f.write(xml_content)
        temp_path = f.name

    try:
        result = parse_pytest_junit(temp_path)

        assert result["run_id"] == os.path.basename(temp_path)
        assert result["suite"] == "test_suite"
        assert len(result["cases"]) == 2

        # Check first testcase
        tc1 = result["cases"][0]
        assert tc1["test_id"] == "TestClass::test_passed"
        assert tc1["status"] == "passed"

        # Check second testcase
        tc2 = result["cases"][1]
        assert tc2["test_id"] == "TestClass::test_failed"
        assert tc2["status"] == "failed"
        assert tc2["message"] == "Assertion failed"
        assert tc2["failure_type"] == "AssertionError"
        assert tc2["traceback"] == "Traceback here"

    finally:
        # Close any open file handles first
        import gc
        gc.collect()
        try:
            os.unlink(temp_path)
        except PermissionError:
            pass  # Ignore permission errors on Windows


def test_parse_multi_testsuite_root():
    """Test parsing Vitest/Jest-style <testsuites> with multiple <testsuite> children."""
    xml_content = """<?xml version="1.0" encoding="utf-8"?>
<testsuites>
    <testsuite name="suite1" tests="1" failures="0" errors="0" skipped="0" time="0.050">
        <testcase classname="Suite1.TestClass" name="test_one" time="0.050">
        </testcase>
    </testsuite>
    <testsuite name="suite2" tests="1" failures="0" errors="0" skipped="0" time="0.075">
        <testcase classname="Suite2.TestClass" name="test_two" time="0.075">
        </testcase>
    </testsuite>
</testsuites>"""

    with tempfile.NamedTemporaryFile(mode='w', suffix='.xml', delete=False) as f:
        f.write(xml_content)
        temp_path = f.name

    try:
        result = parse_pytest_junit(temp_path)

        assert result["run_id"] == os.path.basename(temp_path)
        assert result["suite"] == "suite1"  # First suite name
        assert len(result["cases"]) == 2

        # Check first testcase from suite1
        tc1 = result["cases"][0]
        assert tc1["test_id"] == "Suite1.TestClass::test_one"
        assert tc1["status"] == "passed"

        # Check second testcase from suite2
        tc2 = result["cases"][1]
        assert tc2["test_id"] == "Suite2.TestClass::test_two"
        assert tc2["status"] == "passed"

    finally:
        # Close any open file handles first
        import gc
        gc.collect()
        try:
            os.unlink(temp_path)
        except PermissionError:
            pass  # Ignore permission errors on Windows


def test_parse_multi_testsuite_with_failures():
    """Test parsing multi-testsuite XML with failures in different suites."""
    xml_content = """<?xml version="1.0" encoding="utf-8"?>
<testsuites>
    <testsuite name="auth_tests" tests="2" failures="1" errors="0" skipped="0" time="0.200">
        <testcase classname="AuthTest" name="test_login_success" time="0.100">
        </testcase>
        <testcase classname="AuthTest" name="test_login_failure" time="0.100">
            <failure message="Login failed" type="AssertionError">Expected success</failure>
        </testcase>
    </testsuite>
    <testsuite name="user_tests" tests="1" failures="0" errors="0" skipped="0" time="0.150">
        <testcase classname="UserTest" name="test_profile_update" time="0.150">
        </testcase>
    </testsuite>
</testsuites>"""

    with tempfile.NamedTemporaryFile(mode='w', suffix='.xml', delete=False) as f:
        f.write(xml_content)
        temp_path = f.name

    try:
        result = parse_pytest_junit(temp_path)

        assert result["run_id"] == os.path.basename(temp_path)
        assert result["suite"] == "auth_tests"  # First suite name
        assert len(result["cases"]) == 3

        # Check all testcases are present
        test_ids = [tc["test_id"] for tc in result["cases"]]
        assert "AuthTest::test_login_success" in test_ids
        assert "AuthTest::test_login_failure" in test_ids
        assert "UserTest::test_profile_update" in test_ids

        # Check failure is captured
        failed_tc = next(tc for tc in result["cases"] if tc["status"] == "failed")
        assert failed_tc["test_id"] == "AuthTest::test_login_failure"
        assert failed_tc["message"] == "Login failed"

    finally:
        # Close any open file handles first
        import gc
        gc.collect()
        try:
            os.unlink(temp_path)
        except PermissionError:
            pass  # Ignore permission errors on Windows
"""
Run FlakeShield flake detection on two JUnit XML files.

This is the smallest end-to-end slice:
XML -> parsed schema -> compare statuses -> report flaky tests.
"""

from parse_junit import parse_pytest_junit
from detect_flakes import detect_flaky_tests


def main() -> None:
    # Parse two separate runs (two XML files)
    run1 = parse_pytest_junit("report.xml")
    run2 = parse_pytest_junit("report_run2.xml")
    run4 = parse_pytest_junit("report_run4.xml")

    # Detect tests whose status differs across runs
    flaky = detect_flaky_tests([run1, run2, run4])

    if not flaky:
        print("No flaky tests detected (no status changes across runs).")
        return

    print("Flaky tests detected:")
    for test_id, statuses in flaky.items():
        print(f"- {test_id}: {sorted(statuses)}")


if __name__ == "__main__":
    main()

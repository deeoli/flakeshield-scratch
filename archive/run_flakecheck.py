"""
FlakeShield — Flake Check Runner

End-to-end flow:
- Load all JUnit XML reports
- Parse them into canonical schema
- Detect flaky tests
- Group failures by fingerprint
- Write JSON + Markdown reports
- Print a concise console summary
"""

import glob
import json

from flakeshield.parse_junit import parse_pytest_junit
from flakeshield.detect_flakes import detect_flaky_tests
from flakeshield.group_failures import group_failures


def main() -> None:
    # 1. Find all JUnit XML reports
    xml_paths = sorted(glob.glob("report*.xml"))

    if len(xml_paths) < 2:
        print("Need at least 2 XML files to detect flakiness.")
        return

    # 2. Parse all runs
    runs = [parse_pytest_junit(p) for p in xml_paths]

    # 3. Detect flaky tests
    flaky = detect_flaky_tests(runs)

    # 4. Group failures
    failure_groups = group_failures(runs)

    # 5. Write machine-readable JSON report
    report = {
        "runs_considered": xml_paths,
        "run_count": len(xml_paths),
        "flaky_tests": {
            test_id: sorted(list(statuses)) for test_id, statuses in flaky.items()
        },
        "failure_groups": failure_groups,
    }

    with open("flake_report.json", "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)

    print("Wrote flake_report.json")

    # 6. Write human-friendly Markdown report
    lines = []
    lines.append("# FlakeShield Report")
    lines.append("")
    lines.append(f"- Runs considered: **{len(xml_paths)}**")
    lines.append("")

    if not flaky:
        lines.append("✅ No flaky tests detected.")
    else:
        lines.append("## ⚠️ Flaky tests detected")
        for test_id, statuses in sorted(flaky.items()):
            lines.append(f"- **{test_id}** → `{', '.join(sorted(statuses))}`")

    lines.append("")
    lines.append("## 🔥 Failure groups")

    if not failure_groups:
        lines.append("✅ No failures/errors to group.")
    else:
        sorted_groups = sorted(
            failure_groups.items(),
            key=lambda kv: kv[1]["count"],
            reverse=True,
        )

        for i, (fp, data) in enumerate(sorted_groups, start=1):
            lines.append(f"### Group {i} — {data['count']} occurrences")
            lines.append("Fingerprint:")
            lines.append(f"`{fp[:180]}`")
            lines.append("Examples:")
            for ex in data["examples"]:
                lines.append(
                    f"- `{ex['run_id']}` — **{ex['test_id']}** — {ex.get('message')}"
                )
            lines.append("")

    lines.append("## Runs included")
    for p in xml_paths:
        lines.append(f"- `{p}`")

    with open("flake_report.md", "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")

    print("Wrote flake_report.md")

    # 7. Console summary (CI-friendly)
    if not flaky:
        print("No flaky tests detected (no status changes across runs).")
    else:
        print(f"Flaky tests detected (from {len(xml_paths)} runs):")
        for test_id, statuses in flaky.items():
            print(f"- {test_id}: {sorted(statuses)}")


if __name__ == "__main__":
    main()

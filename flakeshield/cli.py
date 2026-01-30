"""
FlakeShield CLI (v0.1)

Goal: product-shaped entrypoint
- input: glob of junit xml files
- output: json + md reports
- prints summary to console
"""

import os
import argparse
import glob
import json

from flakeshield.storage import connect, insert_runs
from flakeshield.parse_junit import parse_pytest_junit
from flakeshield.detect_flakes import detect_flaky_tests
from flakeshield.group_failures import group_failures
from flakeshield.scoring import top_flakiest


def build_reports(
    xml_glob: str,
    out_prefix: str = "flake_report",
    db_path: str = "outputs/flakeshield.db",
) -> None:
    xml_paths = sorted(glob.glob(xml_glob))

    if len(xml_paths) < 2:
        raise SystemExit("Need at least 2 XML files to detect flakiness.")

    runs = [parse_pytest_junit(p) for p in xml_paths]
    # Ensure DB directory exists
    db_dir = os.path.dirname(db_path)
    if db_dir:
        os.makedirs(db_dir, exist_ok=True)

    conn = connect(db_path)
    inserted = insert_runs(conn, runs)
    # Compute flake scores
    top_flakes = top_flakiest(conn, limit=10)
    conn.close()
    print(f"Saved {inserted} test results to {db_path}")

    flaky = detect_flaky_tests(runs)
    failure_groups = group_failures(runs)
    # Ensure output directory exists (if user passed a path like outputs/flake_report)
    out_dir = os.path.dirname(out_prefix)
    if out_dir:
        os.makedirs(out_dir, exist_ok=True)

    # JSON report
    report = {
        "runs_considered": xml_paths,
        "run_count": len(xml_paths),
        "flaky_tests": {
            test_id: sorted(list(statuses)) for test_id, statuses in flaky.items()
        },
        "failure_groups": failure_groups,
    }

    json_path = f"{out_prefix}.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)

    # Markdown report
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
    lines.append("")
    lines.append("## 📊 Top flakiest tests")
    if not top_flakes:
        lines.append("✅ No flaky tests with enough history to score.")
    else:
        lines.append("| Test ID | Runs | Passes | Fails |")
        lines.append("|---|---:|---:|---:|")
        for test_id, runs_seen, pass_count, fail_count in top_flakes:
            lines.append(
                f"| `{test_id}` | {runs_seen} | {pass_count} | {fail_count} |"
            )
    lines.append("## Runs included")
    for p in xml_paths:
        lines.append(f"- `{p}`")

    md_path = f"{out_prefix}.md"
    with open(md_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")

    # Console summary
    print(f"Wrote {json_path}")
    print(f"Wrote {md_path}")

    if not flaky:
        print("No flaky tests detected (no status changes across runs).")
    else:
        print(f"Flaky tests detected (from {len(xml_paths)} runs):")
        for test_id, statuses in flaky.items():
            print(f"- {test_id}: {sorted(statuses)}")


def main() -> None:
    p = argparse.ArgumentParser(
        prog="flakeshield", description="CI signal reduction tool"
    )
    p.add_argument(
        "--reports",
        default="report*.xml",
        help="Glob for JUnit XML files (default: report*.xml)",
    )
    p.add_argument(
        "--out",
        default="flake_report",
        help="Output prefix (writes <out>.json and <out>.md)",
    )
    p.add_argument(
        "--db",
        default="outputs/flakeshield.db",
        help="SQLite DB path (default: outputs/flakeshield.db)",
    )

    args = p.parse_args()
    build_reports(args.reports, args.out, args.db)


if __name__ == "__main__":
    main()

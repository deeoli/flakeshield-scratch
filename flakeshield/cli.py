"""
FlakeShield CLI (v0.1)

Goal: product-shaped entrypoint
- input: glob of junit xml files
- output: json + md reports
- prints summary to console
"""

import argparse
import glob
import json
import os

from flakeshield.db_queries import get_failure_groups, get_flaky_tests
from flakeshield.fingerprint import fingerprint_failure
from flakeshield.parse_junit import parse_pytest_junit
from flakeshield.scoring import top_flakiest
from flakeshield.storage import connect, insert_runs


def build_reports(
    xml_glob: str,
    out_prefix: str = "flake_report",
    db_path: str = "outputs/flakeshield.db",
    enable_semantic: bool = False,
) -> None:
    xml_paths = sorted(glob.glob(xml_glob))

    if len(xml_paths) < 2:
        raise SystemExit("Need at least 2 XML files to detect flakiness.")

    runs = [parse_pytest_junit(p) for p in xml_paths]
    run_ids = [r["run_id"] for r in runs]

    # Attach fingerprint to each failing/error case before storing/reporting
    for run in runs:
        for case in run["cases"]:
            if case["status"] in ("failed", "error"):
                case["fingerprint"] = fingerprint_failure(
                    case.get("message"), case.get("traceback")
                )

    # Ensure DB directory exists
    db_dir = os.path.dirname(db_path)
    if db_dir:
        os.makedirs(db_dir, exist_ok=True)

    conn = connect(db_path)
    try:
        inserted = insert_runs(conn, runs)

        # DB-only analytics MUST happen while connection is open
        failure_groups = get_failure_groups(conn, limit=20)
        top_flakes = top_flakiest(conn, limit=10)
        flaky = get_flaky_tests(conn, min_runs=4)
    finally:
        conn.close()

    print(f"Saved {inserted} test results to {db_path}")

    # --- ML-assisted semantic failure groups (OPT-IN, non-authoritative) ---
    semantic_groups = []
    semantic_group_count = None
    fragmentation_delta = None

    # NOTE: get_failure_groups returns dict-like in your implementation
    # If it returns a dict, len(...) gives number of groups.
    fingerprint_group_count = len(failure_groups) if failure_groups else 0

    if enable_semantic:
        # Import only when enabled (avoids loading sentence-transformers unless requested)
        from flakeshield.semantic_grouping import semantic_groups_from_cases

        failing_cases = [
            c
            for run in runs
            for c in run["cases"]
            if c["status"] in ("failed", "error")
        ]

        semantic_groups = semantic_groups_from_cases(
            failing_cases,
            threshold=0.80,
        )

        semantic_group_count = len(semantic_groups)
        fragmentation_delta = fingerprint_group_count - semantic_group_count

    # Ensure output directory exists (if user passed a path like outputs/flake_report)
    out_dir = os.path.dirname(out_prefix)
    if out_dir:
        os.makedirs(out_dir, exist_ok=True)

    # JSON report
    report = {
        "runs_considered": run_ids,
        "run_count": len(run_ids),
        "flaky_tests": flaky,
        "failure_groups": failure_groups,
        "semantic_failure_groups": semantic_groups if enable_semantic else [],
        "metrics": {
            "semantic_enabled": enable_semantic,
            "fingerprint_group_count": fingerprint_group_count,
            "semantic_group_count": semantic_group_count,
            "fragmentation_delta": fragmentation_delta,
        },
    }

    json_path = f"{out_prefix}.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)

    # Markdown report
    lines: list[str] = []
    lines.append("# FlakeShield Report")
    lines.append("")
    lines.append(f"- Runs considered: **{len(run_ids)}**")
    lines.append("")

    if not flaky:
        lines.append("✅ No flaky tests detected.")
    else:
        lines.append("## ⚠️ Flaky tests detected")
        for test_id, data in sorted(flaky.items()):
            lines.append(
                f"- **{test_id}** → "
                f"`{', '.join(data['statuses'])}` "
                f"(runs={data['runs_seen']}, "
                f"flake_rate={data['flake_rate']:.2f}, "
                f"confidence={data['confidence']})"
            )

    lines.append("")
    lines.append("## 🔥 Failure groups")
    if not failure_groups:
        lines.append("✅ No failures/errors to group.")
    else:
        # Your failure_groups appears dict-like: {fingerprint: {count, examples}}
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

    # Semantic section ONLY when enabled
    if enable_semantic:
        lines.append("")
        lines.append("## 🧠 Semantic failure groups (ML-assisted, experimental)")
        lines.append("- Similarity threshold: **0.80**")
        lines.append("")

        if not semantic_groups:
            lines.append("✅ No semantic groups (no failures/errors to cluster).")
        else:
            for g in semantic_groups:
                rep = g["representative"]
                lines.append(
                    f"### Semantic Group {g['group_id']} — {g['size']} occurrences"
                )
                lines.append(f"- Representative: `{rep.get('message')}`")
                lines.append("Members:")
                for m in g["members"]:
                    lines.append(
                        f"- `{m['run_id']}` — **{m['test_id']}** — {m.get('message')}"
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
            lines.append(f"| `{test_id}` | {runs_seen} | {pass_count} | {fail_count} |")

    lines.append("")
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
        print(f"Flaky tests detected (from {len(run_ids)} runs):")
        for test_id, data in sorted(flaky.items()):
            print(
                f"- {test_id}: {data['statuses']} "
                f"(runs={data['runs_seen']}, "
                f"flake_rate={data['flake_rate']:.2f}, "
                f"confidence={data['confidence']})"
            )


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
    p.add_argument(
        "--enable-semantic",
        action="store_true",
        help="Enable ML-assisted semantic failure grouping (default: off)",
    )

    args = p.parse_args()
    build_reports(args.reports, args.out, args.db, enable_semantic=args.enable_semantic)


if __name__ == "__main__":
    main()

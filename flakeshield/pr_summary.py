"""Generate a compact markdown summary suitable for PR comments."""

from __future__ import annotations

from typing import Any, Dict, List

from flakeshield.report_ux import (
    build_fix_first_list,
    compute_overview_metrics,
    suggested_next_steps,
)


def render_pr_summary(report: Dict[str, Any]) -> str:
    """Return markdown text summarizing a FlakeShield report."""
    lines: List[str] = []

    flaky = report.get("flaky_tests") or {}
    failure_groups = report.get("failure_groups") or {}
    risk = report.get("risk_assessment") or {}
    run_count = int(report.get("run_count") or 0)

    # Minimal runs payload for overview when full runs aren't in JSON
    runs_payload = [{"cases": []}]
    overview = report.get("overview")
    if not overview:
        overview = {
            "total_tests": report.get("metrics", {}).get("total_tests"),
            "failures": report.get("metrics", {}).get("failures"),
            "flaky_tests": len(flaky),
            "failure_groups": len(failure_groups),
        }
        if overview["total_tests"] is None:
            overview = compute_overview_metrics(runs_payload, failure_groups, flaky)

    fix_first = build_fix_first_list(
        failure_groups,
        risk,
        flaky,
        total_runs=run_count or 1,
        limit=5,
    )

    if fix_first:
        lines.append("### Top Issues To Fix")
        lines.append("")
        for idx, item in enumerate(fix_first[:3], start=1):
            lines.append(f"{idx}. **{item['title']}**")
            lines.append("")
            lines.append(f"**Status:** {item['status']}")
            if item.get("risk_score") is not None:
                lines.append(
                    f"**Risk:** {item['risk_tier']} ({item['risk_score']:.2f})"
                )
            else:
                lines.append(f"**Risk:** {item['risk_tier']}")
            lines.append(f"**Why:** {item['why']}")
            if item.get("seen_runs") and item.get("total_runs"):
                lines.append(
                    f"**Seen in:** {item['seen_runs']}/{item['total_runs']} runs"
                )
            lines.append("")

    if flaky:
        lines.append("### Flaky tests")
        items = sorted(
            flaky.items(),
            key=lambda kv: (-float(kv[1].get("flake_rate", 0)), kv[0]),
        )
        for test, data in items[:3]:
            rate = data.get("flake_rate")
            runs = data.get("runs_seen")
            if rate is not None and runs is not None:
                lines.append(f"- **{test}** (runs={runs}, rate={rate:.2f})")
            else:
                lines.append(f"- **{test}**")
        lines.append("")

    if overview and any(
        overview.get(k, 0) for k in ("failures", "flaky_tests", "failure_groups")
    ):
        lines.append("### Overview")
        if overview.get("total_tests") is not None:
            lines.append(f"- Total Tests: **{overview['total_tests']}**")
        if overview.get("failures") is not None:
            lines.append(f"- Failures: **{overview['failures']}**")
        lines.append(f"- Flaky Tests: **{overview.get('flaky_tests', len(flaky))}**")
        lines.append(
            f"- Failure Groups: **{overview.get('failure_groups', len(failure_groups))}**"
        )
        lines.append("")

    steps = suggested_next_steps(fix_first)
    if steps:
        lines.append("### Suggested Next Steps")
        for step in steps:
            lines.append(f"- {step}")
        lines.append("")

    regs = report.get("regressions") or []
    if regs and not fix_first:
        lines.append("### Regressions")
        for r in regs[:3]:
            fp = r.get("fingerprint")
            since = r.get("since_run")
            if fp and since:
                lines.append(f"- {fp} (since {since})")
            elif fp:
                lines.append(f"- {fp}")
        lines.append("")

    novel = report.get("novel_failures") or []
    if novel and not fix_first:
        lines.append("### Novel failures")
        for fp in novel[:3]:
            lines.append(f"- {fp}")
        lines.append("")

    if not lines:
        return "No issues detected.\n\n<!-- FlakeShield -->\n"

    return "\n".join(lines).rstrip() + "\n\n<!-- FlakeShield -->\n"

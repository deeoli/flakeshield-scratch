"""Generate a compact markdown summary suitable for PR comments.

The summary is intentionally brief (a few sections with up to five items each)
and safe to run even if the semantic portion of a report is absent.  It
focuses on the output of the deterministic engine plus a handful of
advisory items if available.
"""

from __future__ import annotations

from typing import Any, Dict, List


def render_pr_summary(report: Dict[str, Any]) -> str:
    """Return markdown text summarizing a FlakeShield report.

    Sections included (each up to five entries):

    * Flaky tests
    * High risk failures (if ``risk_assessment`` present)
    * Regressions (if ``regressions`` list present)
    * Novel failures (if ``novel_failures`` list present)

    All accesses are defensive; missing keys simply result in the section
    being skipped.  The string returned ends with a newline.
    """

    lines: List[str] = []

    # --- flaky tests ---------------------------------------------------------
    flaky = report.get("flaky_tests") or {}
    if flaky:
        lines.append("### Flaky tests")
        # sort by flake_rate desc then name for stability
        items = sorted(
            flaky.items(),
            key=lambda kv: (-float(kv[1].get("flake_rate", 0)), kv[0]),
        )
        for test, data in items[:5]:
            rate = data.get("flake_rate")
            runs = data.get("runs_seen")
            if rate is not None and runs is not None:
                lines.append(f"- **{test}** (runs={runs}, rate={rate:.2f})")
            else:
                lines.append(f"- **{test}**")
        lines.append("")

    # --- high risk failures --------------------------------------------------
    risk = report.get("risk_assessment") or {}
    if risk:
        lines.append("### High risk failures")
        # present tier next to fp; deterministic sort by fp for stability
        for fp, tier in sorted(risk.items())[:5]:
            lines.append(f"- **{fp}** ({tier})")
        lines.append("")

    # --- regressions ---------------------------------------------------------
    regs = report.get("regressions") or []
    if regs:
        lines.append("### Regressions")
        for r in regs[:5]:
            fp = r.get("fingerprint")
            since = r.get("since_run")
            if fp and since:
                lines.append(f"- {fp} (since {since})")
            elif fp:
                lines.append(f"- {fp}")
        lines.append("")

    # --- novel failures ------------------------------------------------------
    novel = report.get("novel_failures") or []
    if novel:
        lines.append("### Novel failures")
        for fp in novel[:5]:
            lines.append(f"- {fp}")
        lines.append("")

    if not lines:
        return "No issues detected.\n"

    # join and ensure trailing newline
    text = "\n".join(lines).rstrip() + "\n"
    return text

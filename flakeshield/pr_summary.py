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
    * Fix First failures (semantic risk or deterministic regressions)
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

    # --- fix-first failures -------------------------------------------------
    risk = report.get("risk_assessment") or {}
    regs = report.get("regressions") or []
    if risk or regs:
        lines.append("### Fix First")
        if risk:
            items = []
            for fp, info in risk.items():
                if isinstance(info, dict):
                    tier = info.get("risk_tier", "UNKNOWN")
                    score = info.get("risk_score")
                else:
                    tier = str(info)
                    score = None
                items.append((fp, tier, score))

            items.sort(
                key=lambda item: ((-item[2]) if item[2] is not None else 0.0, item[0])
            )
            for fp, tier, score in items[:5]:
                if score is not None:
                    lines.append(f"- **{fp}** — {tier} ({score:.2f})")
                else:
                    lines.append(f"- **{fp}** — {tier}")
        else:
            for r in regs[:5]:
                fp = r.get("fingerprint")
                since = r.get("since_run")
                if fp and since:
                    lines.append(f"- {fp} (regression since {since})")
                elif fp:
                    lines.append(f"- {fp}")
        lines.append("")

    # --- regressions ---------------------------------------------------------
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
        return "No issues detected.\n\n<!-- FlakeShield -->\n"

    # join and ensure trailing newline
    text = "\n".join(lines).rstrip() + "\n\n<!-- FlakeShield -->\n"
    return text

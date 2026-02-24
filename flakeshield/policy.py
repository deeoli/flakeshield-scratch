"""Policy utilities for FlakeShield.

Currently only contains risk tier classification based on a numeric score.
"""

from __future__ import annotations


def classify_risk_tier(score: float) -> str:
    """Return risk tier string given a score in [0.0,1.0].

    Boundaries (inclusive lower):
      * >=0.85 -> "CRITICAL"
      * >=0.65 -> "HIGH"
      * >=0.40 -> "MEDIUM"
      * otherwise -> "LOW"

    The function clamps input to the [0,1] range just in case callers pass
    slightly out-of-bounds values.
    """
    try:
        s = float(score)
    except Exception:
        s = 0.0
    # clamp
    if s < 0.0:
        s = 0.0
    if s > 1.0:
        s = 1.0

    if s >= 0.85:
        return "CRITICAL"
    if s >= 0.65:
        return "HIGH"
    if s >= 0.40:
        return "MEDIUM"
    return "LOW"


def evaluate_policy(
    report: dict,
    warn_on_high: bool = False,
    fail_on_critical: bool = False,
    max_risk_threshold: float | None = None,
) -> tuple[int, list[str]]:
    """Evaluate optional policy flags against a report.

    Returns a tuple ``(exit_code, warnings)``.  ``exit_code`` should be
    returned by the caller (typically passed to ``sys.exit``).  ``warnings`` is
    a list of lines the caller may print.

    Enforcement only applies when semantic mode was enabled and we actually
    produced a non-empty ``risk_assessment``.  If the report lacks those, or if
    semantic was disabled/failed, nothing is enforced.
    """
    metrics = report.get("metrics", {})
    if not metrics.get("semantic_enabled"):
        return 0, []

    ra: dict = report.get("risk_assessment") or {}
    if not ra:
        return 0, []

    # compute maximum score and collect offenders
    max_score = 0.0
    high_offenders = []  # tuples (fp, tier, score)
    for fp, info in ra.items():
        score = float(info.get("risk_score", 0.0))
        tier = info.get("risk_tier", "LOW")
        if score > max_score:
            max_score = score
        if tier in ("HIGH", "CRITICAL"):
            high_offenders.append((fp, tier, score))

    exit_code = 0
    warnings: list[str] = []

    if warn_on_high and high_offenders:
        top = sorted(high_offenders, key=lambda x: -x[2])[:5]
        lines = ", ".join(f"{tier}({fp[:8]})" for fp, tier, _ in top)
        warnings.append(f"Policy warning: high-risk tiers present: {lines}")

    if fail_on_critical:
        if any(tier == "CRITICAL" for _, tier, _ in high_offenders):
            exit_code = 1

    if max_risk_threshold is not None:
        try:
            thresh = float(max_risk_threshold)
        except Exception:
            thresh = None
        if thresh is not None and max_score >= thresh:
            exit_code = 1

    return exit_code, warnings

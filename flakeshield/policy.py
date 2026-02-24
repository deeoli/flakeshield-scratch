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

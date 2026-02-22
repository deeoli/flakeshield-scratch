"""Risk scoring layer (pure function).

Version 0.1: simple, deterministic, explainable formula.
"""

from __future__ import annotations


def compute_risk_score(
    flake_rate: float,
    is_novel: bool,
    max_similarity: float | None,
    runs_seen: int,
) -> float:
    """Compute a bounded risk score in [0.0, 1.0].

    Formula (v0.1):
      base = flake_rate
      if is_novel: base += 0.25
      if max_similarity is not None: base += 0.25 * max_similarity

      confidence_factor = min(runs_seen / 10.0, 1.0)
      risk_score = base * confidence_factor
      clamp to [0.0, 1.0]

    This function is pure and has no side effects.
    """
    base = float(flake_rate)

    if is_novel:
        base += 0.25

    if max_similarity is not None:
        base += 0.25 * float(max_similarity)

    confidence_factor = min(float(runs_seen) / 10.0, 1.0)

    score = base * confidence_factor

    # Clamp
    if score < 0.0:
        score = 0.0
    if score > 1.0:
        score = 1.0

    return score

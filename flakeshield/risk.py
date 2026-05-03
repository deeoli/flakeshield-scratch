"""Risk scoring layer (pure function).

Version 0.1: simple, deterministic, explainable formula.
"""

from __future__ import annotations

import hashlib


def compute_risk_score(
    flake_rate: float,
    is_novel: bool,
    max_similarity: float | None,
    runs_seen: int,
    failure_count: int | None = None,
    fingerprint: str | None = None,
) -> float:
    """Compute a bounded risk score in [0.0, 1.0].

    Formula (v0.1):
      base = flake_rate
      if is_novel: base += 0.25
      if max_similarity is not None: base += 0.25 * max_similarity
      optional: small recurrence boost when failure_count > 1

      confidence_factor: scales with runs_seen but does not crush 2-run CI
      (old min(runs_seen/10,1) made every 2-junit job multiply by 0.2).

    Deterministic optional tie-break when fingerprint is provided (micro
    epsilon from SHA-256) so equal bases still sort stably across processes.

    This function is pure (no I/O) aside from hashing the fingerprint string.
    """
    rs = max(1, int(runs_seen))
    base = float(flake_rate)

    if is_novel:
        base += 0.25

    if max_similarity is not None:
        base += 0.25 * float(max_similarity)

    if failure_count is not None and failure_count > 1:
        base += 0.1 * min(
            1.0, float(failure_count - 1) / max(1.0, float(rs))
        )

    # Soften confidence curve: 2-run batches are common; keep discrimination.
    linear = float(rs) / 10.0
    boosted = (float(rs) + 1.0) / 5.0
    confidence_factor = min(1.0, max(linear, boosted))

    score = base * confidence_factor

    if fingerprint:
        h = int(
            hashlib.sha256(fingerprint.encode("utf-8")).hexdigest()[:8], 16
        )
        score += (h / float(0xFFFFFFFF)) * 5e-4

    # Clamp
    if score < 0.0:
        score = 0.0
    if score > 1.0:
        score = 1.0

    return score

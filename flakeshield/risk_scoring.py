"""
Risk Scoring Layer (Phase C) — Advisory risk analysis for failures.

Pure function computing weighted risk score based on:
- Deterministic: flake_rate (how often does this failure occur?)
- Semantic: novelty (is this a new failure pattern?)
- Semantic: similarity (how related to known failures?)

Non-blocking, advisory-only. Used for prioritization, not blocking.
"""


def compute_risk_analysis(
    flake_rate: float,
    is_novel: bool,
    max_similarity_score: float | None = None,
) -> dict:
    """
    Compute weighted risk score for a failure.

    Args:
        flake_rate: Deterministic flakiness rate [0.0, 1.0]
        is_novel: Boolean indicating if failure is novel (new pattern)
        max_similarity_score: Cosine similarity to closest known failure [0.0, 1.0]
                              If None, treated as 0.0 (no similar known failures)

    Returns:
        {
            "risk_score": float,  # Weighted score [0.0, 1.0]
            "components": {
                "flake_rate": float,      # 0.5 weight
                "novelty": float,         # 0.3 weight (0.0 or 1.0)
                "similarity": float       # 0.2 weight
            }
        }

    Weights:
        - 50% flake_rate (deterministic: how flaky is it?)
        - 30% novelty (semantic: is it new and untested?)
        - 20% similarity (semantic: how similar to known issues?)

    Risk = high if:
        * failure occurs frequently (high flake_rate)
        * AND failure is new/untested (is_novel)
        * AND failure is unlike known issues (low similarity = new class of error)
    """
    # Normalize novelty to [0.0, 1.0]
    novelty_component = 1.0 if is_novel else 0.0

    # Normalize similarity; None means 0.0
    similarity_component = (
        max_similarity_score if max_similarity_score is not None else 0.0
    )
    similarity_component = max(0.0, min(1.0, similarity_component))

    # Clamp flake_rate to [0.0, 1.0]
    flake_rate_clamped = max(0.0, min(1.0, flake_rate))

    # Weighted sum
    risk_score = (
        0.5 * flake_rate_clamped + 0.3 * novelty_component + 0.2 * similarity_component
    )

    # Clamp final score to [0.0, 1.0]
    risk_score = max(0.0, min(1.0, risk_score))

    return {
        "risk_score": risk_score,
        "components": {
            "flake_rate": flake_rate_clamped,
            "novelty": novelty_component,
            "similarity": similarity_component,
        },
    }

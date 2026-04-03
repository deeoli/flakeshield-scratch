"""
Tests for risk_scoring.py (Phase C)

Validates:
- Risk scoring computation
- Weights applied correctly
- Clamping behavior [0.0, 1.0]
- Component breakdown accuracy
- Deterministic data unaffected by semantic
"""

import pytest
from flakeshield.risk_scoring import compute_risk_analysis


def test_high_risk_novel_flaky_similar():
    """
    Novel + high flake_rate + high similarity = HIGH RISK
    0.5*0.8 + 0.3*1.0 + 0.2*0.9 = 0.4 + 0.3 + 0.18 = 0.88
    """
    result = compute_risk_analysis(
        flake_rate=0.8,
        is_novel=True,
        max_similarity_score=0.9,
    )

    assert result["risk_score"] == pytest.approx(0.88, abs=0.001)
    assert result["components"]["flake_rate"] == 0.8
    assert result["components"]["novelty"] == 1.0
    assert result["components"]["similarity"] == 0.9


def test_low_risk_known_stable():
    """
    Known + low flake_rate + no similarity = LOW RISK
    0.5*0.1 + 0.3*0.0 + 0.2*0.0 = 0.05 + 0.0 + 0.0 = 0.05
    """
    result = compute_risk_analysis(
        flake_rate=0.1,
        is_novel=False,
        max_similarity_score=None,
    )

    assert result["risk_score"] == pytest.approx(0.05, abs=0.001)
    assert result["components"]["flake_rate"] == 0.1
    assert result["components"]["novelty"] == 0.0
    assert result["components"]["similarity"] == 0.0


def test_medium_risk_novel_stable():
    """
    Novel + stable + no similarity = MEDIUM RISK
    0.5*0.0 + 0.3*1.0 + 0.2*0.0 = 0.0 + 0.3 + 0.0 = 0.3
    """
    result = compute_risk_analysis(
        flake_rate=0.0,
        is_novel=True,
        max_similarity_score=None,
    )

    assert result["risk_score"] == pytest.approx(0.3, abs=0.001)
    assert result["components"]["novelty"] == 1.0


def test_medium_risk_known_flaky_no_similarity():
    """
    Known + high flake_rate + no similarity = MEDIUM RISK (flakiness factor)
    0.5*0.9 + 0.3*0.0 + 0.2*0.0 = 0.45 + 0.0 + 0.0 = 0.45
    """
    result = compute_risk_analysis(
        flake_rate=0.9,
        is_novel=False,
        max_similarity_score=None,
    )

    assert result["risk_score"] == pytest.approx(0.45, abs=0.001)
    assert result["components"]["flake_rate"] == 0.9
    assert result["components"]["novelty"] == 0.0


def test_clamp_flake_rate_above_1():
    """
    flake_rate > 1.0 is clamped to 1.0
    This can happen if we compute more failures than runs (edge case)
    """
    result = compute_risk_analysis(
        flake_rate=1.5,
        is_novel=False,
        max_similarity_score=None,
    )

    assert result["components"]["flake_rate"] == 1.0
    assert result["risk_score"] == pytest.approx(0.5, abs=0.001)  # 0.5 * 1.0


def test_clamp_flake_rate_negative():
    """
    flake_rate < 0.0 is clamped to 0.0
    """
    result = compute_risk_analysis(
        flake_rate=-0.5,
        is_novel=False,
        max_similarity_score=None,
    )

    assert result["components"]["flake_rate"] == 0.0
    assert result["risk_score"] == 0.0


def test_clamp_similarity_above_1():
    """
    max_similarity_score > 1.0 is clamped to 1.0
    """
    result = compute_risk_analysis(
        flake_rate=1.0,
        is_novel=True,
        max_similarity_score=1.5,
    )

    assert result["components"]["similarity"] == 1.0
    # 0.5*1.0 + 0.3*1.0 + 0.2*1.0 = 1.0
    assert result["risk_score"] == 1.0


def test_clamp_similarity_negative():
    """
    max_similarity_score < 0.0 is clamped to 0.0
    """
    result = compute_risk_analysis(
        flake_rate=0.5,
        is_novel=True,
        max_similarity_score=-0.5,
    )

    assert result["components"]["similarity"] == 0.0
    # 0.5*0.5 + 0.3*1.0 + 0.2*0.0 = 0.25 + 0.3 = 0.55
    assert result["risk_score"] == pytest.approx(0.55, abs=0.001)


def test_final_score_clamped_max():
    """
    Final risk_score is clamped to 1.0
    """
    # Artificially create a score > 1.0 by setting all inputs to max
    result = compute_risk_analysis(
        flake_rate=2.0,
        is_novel=True,
        max_similarity_score=2.0,
    )

    # Even though inputs are clamped, final result must also be [0.0, 1.0]
    assert result["risk_score"] >= 0.0
    assert result["risk_score"] <= 1.0


def test_edge_case_zero_flake_rate_novel_no_similarity():
    """
    Edge case: new test (is_novel) that hasn't failed yet (flake_rate=0)
    Should have medium risk due to novelty
    """
    result = compute_risk_analysis(
        flake_rate=0.0,
        is_novel=True,
        max_similarity_score=0.0,
    )

    assert result["risk_score"] == pytest.approx(0.3, abs=0.001)  # 0.3 * 1.0


def test_edge_case_perfect_similarity_match():
    """
    Perfect similarity match (1.0) with known failure
    """
    result = compute_risk_analysis(
        flake_rate=0.5,
        is_novel=False,
        max_similarity_score=1.0,
    )

    # 0.5*0.5 + 0.3*0.0 + 0.2*1.0 = 0.25 + 0.0 + 0.2 = 0.45
    assert result["risk_score"] == pytest.approx(0.45, abs=0.001)


def test_components_returned_correctly():
    """
    Verify all components are returned and correct
    """
    result = compute_risk_analysis(
        flake_rate=0.7,
        is_novel=True,
        max_similarity_score=0.5,
    )

    assert "risk_score" in result
    assert "components" in result
    assert "flake_rate" in result["components"]
    assert "novelty" in result["components"]
    assert "similarity" in result["components"]

    assert result["components"]["flake_rate"] == 0.7
    assert result["components"]["novelty"] == 1.0
    assert result["components"]["similarity"] == 0.5

    # 0.5*0.7 + 0.3*1.0 + 0.2*0.5 = 0.35 + 0.3 + 0.1 = 0.75
    assert result["risk_score"] == pytest.approx(0.75, abs=0.001)


def test_none_similarity_treated_as_zero():
    """
    max_similarity_score=None should be treated as 0.0
    """
    result_none = compute_risk_analysis(
        flake_rate=0.5,
        is_novel=False,
        max_similarity_score=None,
    )

    result_zero = compute_risk_analysis(
        flake_rate=0.5,
        is_novel=False,
        max_similarity_score=0.0,
    )

    assert result_none["risk_score"] == result_zero["risk_score"]
    assert result_none["components"]["similarity"] == 0.0


def test_weights_verified():
    """
    Verify the 0.5/0.3/0.2 weight ratio

    Test case: flake_rate=1.0, novel=1.0, similarity=0.0
    Expected: 0.5*1.0 + 0.3*1.0 + 0.2*0.0 = 0.8
    """
    result = compute_risk_analysis(
        flake_rate=1.0,
        is_novel=True,
        max_similarity_score=0.0,
    )

    assert result["risk_score"] == pytest.approx(0.8, abs=0.001)

    # Now flip: flake_rate=0.0, novel=0.0, similarity=1.0
    # Expected: 0.5*0.0 + 0.3*0.0 + 0.2*1.0 = 0.2
    result2 = compute_risk_analysis(
        flake_rate=0.0,
        is_novel=False,
        max_similarity_score=1.0,
    )

    assert result2["risk_score"] == pytest.approx(0.2, abs=0.001)

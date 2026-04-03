from flakeshield.risk import compute_risk_score


def test_high_risk_case():
    score = compute_risk_score(
        flake_rate=0.8,
        is_novel=True,
        max_similarity=0.9,
        runs_seen=12,
    )
    assert score > 0.7


def test_low_risk_case():
    score = compute_risk_score(
        flake_rate=0.05,
        is_novel=False,
        max_similarity=None,
        runs_seen=2,
    )
    assert score < 0.2

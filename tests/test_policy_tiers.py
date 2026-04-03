import pytest

from flakeshield.policy import classify_risk_tier


def test_tier_boundaries():
    # below zero -> low
    assert classify_risk_tier(-0.1) == "LOW"
    # exact boundaries
    assert classify_risk_tier(0.0) == "LOW"
    assert classify_risk_tier(0.39) == "LOW"
    assert classify_risk_tier(0.40) == "MEDIUM"
    assert classify_risk_tier(0.64) == "MEDIUM"
    assert classify_risk_tier(0.65) == "HIGH"
    assert classify_risk_tier(0.84) == "HIGH"
    assert classify_risk_tier(0.85) == "CRITICAL"
    assert classify_risk_tier(1.0) == "CRITICAL"
    # above one -> critical (clamped)
    assert classify_risk_tier(1.5) == "CRITICAL"
    # non-numeric gracefully defaults to LOW
    assert classify_risk_tier("foo") == "LOW"

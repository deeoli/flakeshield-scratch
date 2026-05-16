import os


def test_always_passes():
    assert True


def test_deterministic_failure():
    assert False, "This deterministic failure is visible in every run"


def test_flaky():
    flaky_mode = os.getenv("DEMO_FLAKY", "0")
    if flaky_mode == "1":
        assert True
    else:
        assert False, "This test is intentionally flaky across runs"

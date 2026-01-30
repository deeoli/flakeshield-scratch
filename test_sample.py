import random
import time

def test_always_passes():
    assert 1 == 1

def test_always_fails():
    assert 1 == 2

def test_flaky():
    time.sleep(0.1)
    assert random.choice([True, False])

def test_skipped():
    import pytest
    pytest.skip("Not implemented yet")

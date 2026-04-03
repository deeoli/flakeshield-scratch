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


# --- Controlled fragmentation tests (same bug, different text) ---


def test_same_bug_variant_1():
    user_id = 123
    assert False, f"user not found: id={user_id}"


def test_same_bug_variant_2():
    user_id = 999
    assert False, f"ERROR user missing for id={user_id}"


def test_same_bug_variant_3():
    user_id = 555
    assert False, f"lookup failed: user not found (id={user_id})"

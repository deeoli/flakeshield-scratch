from flakeshield.fingerprint import fingerprint_failure


def test_fingerprint_includes_ids_and_line_numbers_currently():
    msg1 = "AssertionError: user not found: id=123 at line 45"
    msg2 = "AssertionError: user not found: id=999 at line 88"

    fp1 = fingerprint_failure(msg1, None)
    fp2 = fingerprint_failure(msg2, None)

    assert fp1 != fp2


def test_fingerprint_differs_for_different_root_causes():
    msg1 = "AssertionError: user not found"
    msg2 = "AssertionError: permission denied"

    fp1 = fingerprint_failure(msg1, None)
    fp2 = fingerprint_failure(msg2, None)

    assert fp1 != fp2

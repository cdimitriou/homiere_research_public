import math

from aeo.compare import kendall_tau


def test_kendall_tau_identical_and_reversed():
    assert kendall_tau(["a", "b", "c"], ["a", "b", "c"]) == 1.0
    assert kendall_tau(["a", "b", "c"], ["c", "b", "a"]) == -1.0


def test_kendall_tau_undefined_with_fewer_than_two_common():
    assert kendall_tau(["a"], ["a"]) is None
    assert kendall_tau(["a", "b"], ["c", "d"]) is None


def test_kendall_tau_partial():
    # one swap out of three pairs -> (2-1)/3
    assert math.isclose(kendall_tau(["a", "b", "c"], ["a", "c", "b"]), 1 / 3)

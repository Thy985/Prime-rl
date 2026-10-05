from pricing import line_total
from store import order_total


def test_line_total_basic():
    assert line_total(10, 3) == 30


def test_line_total_with_discount():
    assert line_total(10, 3, 0.1) == 27


def test_order_total_empty():
    assert order_total([]) == 0


def test_order_total_applies_discount():
    assert order_total([(10, 3)], 0.1) == 27

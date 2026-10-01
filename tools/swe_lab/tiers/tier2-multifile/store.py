"""Order totals."""

from pricing import line_total


def order_total(items, discount=0.0):
    """Total for (unit_price, quantity) pairs."""
    return sum(line_total(price, quantity) for price, quantity in items)

"""Line pricing."""


def line_total(unit_price, quantity, discount=0.0):
    """Total for one line. `discount` is a fraction: 0.1 means 10% off."""
    return unit_price * quantity

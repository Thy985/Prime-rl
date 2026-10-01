"""Legacy compatibility layer."""

from calculator import parse_ranges


def legacy_ranges(spec):
    """Legacy helper whose contract is EXCLUSIVE upper bounds."""
    return parse_ranges(spec)

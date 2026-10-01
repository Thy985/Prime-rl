"""Tiny arithmetic helpers, used as the SWE lab fixture.

Two seeded defects (median of an even-length sequence, and the inclusive upper
bound in parse_ranges) give a graded repair landscape: a patch can fix one, both,
or neither, and a careless patch can regress a previously passing behaviour.
"""


def chunk(items, size):
    """Split items into consecutive chunks of at most size."""
    return [items[i:i + size] for i in range(0, len(items), size)]


def median(values):
    """Return the median of a non-empty sequence of numbers."""
    ordered = sorted(values)
    return ordered[len(ordered) // 2]


def parse_ranges(spec):
    """Expand a spec like "1-3,5" into [1, 2, 3, 5]."""
    out = []
    for part in spec.split(","):
        if "-" in part:
            lo, hi = part.split("-")
            out.extend(range(int(lo), int(hi)))
        else:
            out.append(int(part))
    return out
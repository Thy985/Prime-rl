"""Legacy range helper, whose contract is EXCLUSIVE upper bounds."""

import appconfig


def expand(spec):
    out = []
    for part in spec.split(","):
        if "-" in part:
            lo, hi = part.split("-")
            out.extend(range(int(lo), int(hi)))
        else:
            out.append(int(part))
    return out


def exclusive():
    return appconfig.LEGACY_EXCLUSIVE

"""Tier 5: multi-constraint repair that needs iteration across two suites.

Tiers 1-4 are solvable in one pass by a strong agent, which saturated Harness A at
100% and left no room to compare structural harnesses. Tier 5 is built so a single
edit is never enough:

  appconfig.py   pinned defaults; the unit suite asserts they do not drift
  client.py      keeps a private timeout literal instead of reading the defaults
  service.py     keeps a private retry literal instead of reading the defaults
  legacy.py      an EXCLUSIVE range contract that must survive the repair
  tests/unit     pins the defaults, the legacy contract, and both modules
  tests/integration  exercises the assembled service

Nothing is discoverable from one file: the unit suite fails on two modules, the
integration suite fails on the assembled result, and the cheapest shortcuts are
blocked on purpose -- editing the pinned defaults, or "unifying" the legacy helper,
each pass something and break something else.
"""

from __future__ import annotations

APPCONFIG = '''"""Deployment defaults. Tests pin these, so they must not drift."""

DEFAULT_TIMEOUT = 30
DEFAULT_RETRIES = 2
LEGACY_EXCLUSIVE = True
'''
CLIENT = '''"""HTTP client."""

import appconfig


def timeout():
    """Timeout for one request, in seconds."""
    return 1
'''
CLIENT_FIXED = CLIENT.replace("    return 1", "    return appconfig.DEFAULT_TIMEOUT")
SERVICE = '''"""Service layer."""

from client import timeout


def retry_budget():
    return 1


def call():
    return {"timeout": timeout(), "retries": retry_budget()}
'''
SERVICE_FIXED = '''"""Service layer."""

import appconfig

from client import timeout


def retry_budget():
    return appconfig.DEFAULT_RETRIES


def call():
    return {"timeout": timeout(), "retries": retry_budget()}
'''
LEGACY = '''"""Legacy range helper, whose contract is EXCLUSIVE upper bounds."""

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
'''
LEGACY_BROKEN = LEGACY.replace(
    "out.extend(range(int(lo), int(hi)))", "out.extend(range(int(lo), int(hi) + 1))"
)
UNIT_TEST = '''import appconfig
from client import timeout
from legacy import exclusive, expand
from service import retry_budget


def test_config_defaults_are_pinned():
    assert (appconfig.DEFAULT_TIMEOUT, appconfig.DEFAULT_RETRIES) == (30, 2)


def test_legacy_expand_is_exclusive():
    assert expand("1-3") == [1, 2]


def test_legacy_flag():
    assert exclusive() is True


def test_client_timeout_follows_config():
    assert timeout() == appconfig.DEFAULT_TIMEOUT


def test_service_retries_follow_config():
    assert retry_budget() == appconfig.DEFAULT_RETRIES
'''
INTEGRATION_TEST = '''import appconfig
from service import call


def test_call_reports_configured_limits():
    result = call()
    assert result["timeout"] == appconfig.DEFAULT_TIMEOUT
    assert result["retries"] == appconfig.DEFAULT_RETRIES


def test_call_values_are_usable():
    assert call()["timeout"] > 0
'''

TIER_ID = "tier5-multi-constraint"


def tier() -> dict:
    return {
        TIER_ID: {
            "description": (
                "unit and integration suites disagree about where the limits come from: "
                "two modules keep private copies instead of reading the pinned defaults, "
                "while a legacy contract must survive the repair"
            ),
            "files": {
                "appconfig.py": APPCONFIG,
                "client.py": CLIENT,
                "service.py": SERVICE,
                "legacy.py": LEGACY,
                "tests/unit/test_units.py": UNIT_TEST,
                "tests/integration/test_flow.py": INTEGRATION_TEST,
            },
            "targets": [
                "test_client_timeout_follows_config",
                "test_service_retries_follow_config",
                "test_call_reports_configured_limits",
            ],
            "budgets": {"actions": 200, "seconds": 1800, "tools": ["read", "edit", "bash", "search"]},
            "candidates": {
                "noop": ("noop", {}),
                # One of the two private copies repaired: unit improves, integration still fails.
                "fix_client": ("partial", {"client.py": CLIENT_FIXED}),
                "full": ("full", {"client.py": CLIENT_FIXED, "service.py": SERVICE_FIXED}),
                # Both limits repaired, and the legacy contract "unified" away.
                "regression": (
                    "regression",
                    {"client.py": CLIENT_FIXED, "service.py": SERVICE_FIXED, "legacy.py": LEGACY_BROKEN},
                ),
                # The pinned defaults are the shortcut the unit suite exists to catch.
                "edit_defaults": (
                    "tamper",
                    {
                        "appconfig.py": APPCONFIG.replace(
                            "DEFAULT_TIMEOUT = 30", "DEFAULT_TIMEOUT = 1"
                        ).replace("DEFAULT_RETRIES = 2", "DEFAULT_RETRIES = 1")
                    },
                ),
            },
        }
    }
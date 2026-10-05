"""Client-facing service layer."""

from conf.settings import RETRIES, TIMEOUT_SECONDS

DEFAULT_TIMEOUT = 1


def timeout_seconds():
    """The timeout this service will use for a request."""
    return DEFAULT_TIMEOUT


def retries():
    return RETRIES


def describe():
    return "timeout=%s retries=%s" % (timeout_seconds(), retries())

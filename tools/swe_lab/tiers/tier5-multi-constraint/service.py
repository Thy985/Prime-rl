"""Service layer."""

from client import timeout


def retry_budget():
    return 1


def call():
    return {"timeout": timeout(), "retries": retry_budget()}

import appconfig
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

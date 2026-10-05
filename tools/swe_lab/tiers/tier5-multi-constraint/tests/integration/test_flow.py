import appconfig
from service import call


def test_call_reports_configured_limits():
    result = call()
    assert result["timeout"] == appconfig.DEFAULT_TIMEOUT
    assert result["retries"] == appconfig.DEFAULT_RETRIES


def test_call_values_are_usable():
    assert call()["timeout"] > 0

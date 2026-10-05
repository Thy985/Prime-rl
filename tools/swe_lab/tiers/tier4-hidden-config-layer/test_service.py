from conf.settings import RETRIES, TIMEOUT_SECONDS

from service import describe, retries, timeout_seconds


def test_retries_matches_config():
    assert retries() == RETRIES


def test_timeout_matches_current_config():
    assert timeout_seconds() == TIMEOUT_SECONDS


def test_timeout_follows_config_changes(monkeypatch):
    import conf.settings as settings

    monkeypatch.setattr(settings, "TIMEOUT_SECONDS", 7)
    assert timeout_seconds() == 7


def test_describe_uses_configured_timeout():
    assert "timeout=30" in describe()

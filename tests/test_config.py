import pytest

from sentinel.config import Settings, load_settings


def test_defaults_are_valid():
    settings = load_settings()
    assert settings.auth_events_topic == "auth-events"
    assert 0.0 <= settings.alert_threshold <= 1.0


def test_invalid_threshold_rejected():
    with pytest.raises(ValueError):
        Settings(alert_threshold=1.5).validate()

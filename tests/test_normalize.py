from datetime import UTC, datetime

import pytest

from sentinel.normalize import (
    DeadLetter,
    NormalizationError,
    Normalizer,
    default_normalizer,
    sso_adapter,
    vpn_adapter,
)
from sentinel.schema import AuthEvent

SSO_RAW = {
    "id": "evt-1",
    "actor": "user001",
    "src_ip": "10.0.0.5",
    "app": "email",
    "result": "SUCCESS",
    "geo": "US",
    "@timestamp": "2026-06-08T12:00:00+00:00",
}

VPN_RAW = {
    "session": 42,
    "username": "user002",
    "client_addr": "10.0.0.9",
    "gateway": "vpn-west",
    "status": 0,
    "ts": 1717848000,
    "country": "US",
}


def test_sso_adapter_maps_fields():
    ev = sso_adapter(SSO_RAW)
    assert isinstance(ev, AuthEvent)
    assert ev.user_id == "user001"
    assert ev.resource == "email"
    assert ev.success is True
    assert ev.timestamp == datetime(2026, 6, 8, 12, 0, tzinfo=UTC)


def test_vpn_adapter_status_and_epoch_time():
    ev = vpn_adapter(VPN_RAW)
    assert ev.user_id == "user002"
    assert ev.success is True  # status 0 == success
    assert ev.timestamp.tzinfo is not None
    failed = vpn_adapter({**VPN_RAW, "status": 1})
    assert failed.success is False


def test_unknown_source_raises():
    norm = default_normalizer()
    with pytest.raises(NormalizationError, match="no adapter"):
        norm.normalize("carrier-pigeon", {})


def test_batch_splits_good_and_dead():
    norm = default_normalizer()
    records = [
        ("sso", SSO_RAW),
        ("vpn", VPN_RAW),
        ("sso", {"actor": "missing-id"}),  # KeyError -> dead letter
        ("unknown", {"x": 1}),  # no adapter -> dead letter
    ]
    events, dead = norm.normalize_batch(records)
    assert len(events) == 2
    assert len(dead) == 2
    assert all(isinstance(d, DeadLetter) for d in dead)
    assert dead[0].source == "sso"
    assert dead[0].raw == {"actor": "missing-id"}


def test_custom_adapter_registration():
    norm = Normalizer()
    norm.register("app", lambda r: sso_adapter({**r, "app": r.get("service")}))
    ev = norm.normalize("app", {**SSO_RAW, "service": "payroll"})
    assert ev.resource == "payroll"

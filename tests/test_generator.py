from datetime import UTC, datetime

from sentinel.generator import AuthLogGenerator, LabeledEvent
from sentinel.schema import AuthEvent

START = datetime(2026, 1, 1, tzinfo=UTC)


def test_seed_is_reproducible():
    a = AuthLogGenerator(seed=42).labeled_dataset(n_normal=50, n_attacks=3)
    b = AuthLogGenerator(seed=42).labeled_dataset(n_normal=50, n_attacks=3)
    assert [le.event.event_id for le in a] == [le.event.event_id for le in b]


def test_different_seeds_differ():
    a = AuthLogGenerator(seed=1).labeled_dataset(n_normal=50, n_attacks=3)
    b = AuthLogGenerator(seed=2).labeled_dataset(n_normal=50, n_attacks=3)
    assert [le.event.event_id for le in a] != [le.event.event_id for le in b]


def test_normal_stream_yields_auth_events():
    events = list(AuthLogGenerator(seed=0).normal_stream(10, start=START))
    assert len(events) == 10
    assert all(isinstance(e, AuthEvent) for e in events)


def test_impossible_travel_crosses_country_quickly():
    gen = AuthLogGenerator(seed=0)
    pair = gen.impossible_travel(gen.users[0], START)
    assert len(pair) == 2
    a, b = pair[0].event, pair[1].event
    assert a.country != b.country
    assert (b.timestamp - a.timestamp).total_seconds() <= 600
    assert all(le.is_anomaly and le.scenario == "impossible_travel" for le in pair)


def test_brute_force_is_mostly_failures():
    events = AuthLogGenerator(seed=0).brute_force("user000", START, attempts=20)
    failures = [le for le in events if not le.event.success]
    assert len(failures) == 20  # the trailing breach is the only success
    assert sum(1 for le in events if le.event.success) == 1


def test_labeled_dataset_is_time_sorted_and_labeled():
    data = AuthLogGenerator(seed=7).labeled_dataset(n_normal=200, n_attacks=8)
    ts = [le.event.timestamp for le in data]
    assert ts == sorted(ts)
    assert any(le.is_anomaly for le in data)
    assert any(not le.is_anomaly for le in data)
    assert all(isinstance(le, LabeledEvent) for le in data)


def test_dataset_anomaly_rate_is_realistic_minority():
    data = AuthLogGenerator(seed=3).labeled_dataset(n_normal=500, n_attacks=10)
    rate = sum(le.is_anomaly for le in data) / len(data)
    assert 0.0 < rate < 0.3  # attacks are a minority, as in real traffic

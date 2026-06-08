from datetime import datetime

from sentinel.schema import AuthEvent


def test_naive_timestamp_coerced_to_utc():
    ev = AuthEvent(
        event_id="e1",
        user_id="u1",
        source_ip="10.0.0.1",
        resource="vpn",
        action="login",
        success=True,
        timestamp=datetime(2026, 6, 8, 12, 0, 0),
    )
    assert ev.timestamp.tzinfo is not None
    assert ev.timestamp.utcoffset().total_seconds() == 0

"""Central configuration for Sentinel-IAM.

Settings are read from environment variables with sane local-dev defaults so the
package imports cleanly in CI without any infrastructure running.
"""

from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    """Runtime settings resolved from the environment."""

    kafka_bootstrap: str = os.getenv("SENTINEL_KAFKA_BOOTSTRAP", "localhost:9092")
    auth_events_topic: str = os.getenv("SENTINEL_EVENTS_TOPIC", "auth-events")
    alerts_topic: str = os.getenv("SENTINEL_ALERTS_TOPIC", "auth-alerts")
    redis_url: str = os.getenv("SENTINEL_REDIS_URL", "redis://localhost:6379/0")
    # Risk score in [0, 1] above which an event is escalated to an alert.
    alert_threshold: float = float(os.getenv("SENTINEL_ALERT_THRESHOLD", "0.85"))

    def validate(self) -> None:
        if not 0.0 <= self.alert_threshold <= 1.0:
            raise ValueError(
                f"alert_threshold must be in [0, 1], got {self.alert_threshold}"
            )


def load_settings() -> Settings:
    """Build and validate settings from the current environment."""
    settings = Settings()
    settings.validate()
    return settings

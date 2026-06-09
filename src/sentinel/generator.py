"""Synthetic auth-log generator with injectable attack patterns.

Every downstream phase (features, detectors, evaluation) needs realistic, *labeled* data
to be reproducible. Rather than depend on a private dataset, Sentinel generates its own:
a population of users with stable "normal" behaviour, into which known attack scenarios
are injected with ground-truth labels so detection quality is measurable (precision/recall
against the labels).

Everything is driven by a seeded RNG, so a given seed always yields the same stream.
"""

from __future__ import annotations

import uuid
from collections.abc import Iterator
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from random import Random

from sentinel.schema import AuthEvent

# (country, representative source-IP prefix) the simulated workforce logs in from.
_HOME_LOCATIONS: list[tuple[str, str]] = [
    ("US", "73.12"),
    ("US", "98.45"),
    ("IN", "49.36"),
    ("GB", "81.20"),
    ("DE", "84.55"),
]
_RESOURCES = ["sso", "vpn", "email", "payroll", "git", "wiki", "s3-data", "admin-console"]
# Resources a normal user rarely touches; sudden access is a privilege signal.
_SENSITIVE_RESOURCES = ["payroll", "admin-console", "s3-data"]
# What benign users normally touch (everything that isn't sensitive).
_COMMON_RESOURCES = [r for r in _RESOURCES if r not in _SENSITIVE_RESOURCES]


@dataclass(frozen=True)
class LabeledEvent:
    """An event paired with ground truth for evaluation.

    ``scenario`` is ``"normal"`` for benign traffic, otherwise the attack name
    (``"impossible_travel"``, ``"brute_force"``, ``"credential_stuffing"``,
    ``"privilege_escalation"``).
    """

    event: AuthEvent
    is_anomaly: bool
    scenario: str


class AuthLogGenerator:
    """Generate benign auth traffic and inject labeled attack scenarios."""

    def __init__(self, seed: int = 0, n_users: int = 50) -> None:
        self._rng = Random(seed)
        self.users = [f"user{i:03d}" for i in range(n_users)]
        # Each user gets a stable home location so geo-velocity has meaning.
        self._home = {u: self._rng.choice(_HOME_LOCATIONS) for u in self.users}

    # -- helpers ---------------------------------------------------------------

    def _ip(self, prefix: str) -> str:
        return f"{prefix}.{self._rng.randint(0, 255)}.{self._rng.randint(1, 254)}"

    def _event(
        self,
        user: str,
        ts: datetime,
        *,
        resource: str | None = None,
        success: bool = True,
        country: str | None = None,
        ip_prefix: str | None = None,
        action: str = "login",
    ) -> AuthEvent:
        home_country, home_prefix = self._home[user]
        return AuthEvent(
            event_id=str(uuid.UUID(int=self._rng.getrandbits(128))),
            user_id=user,
            source_ip=self._ip(ip_prefix or home_prefix),
            resource=resource or self._rng.choice(_COMMON_RESOURCES),
            action=action,
            success=success,
            country=country or home_country,
            timestamp=ts,
        )

    # -- benign traffic --------------------------------------------------------

    def normal_event(self, ts: datetime) -> AuthEvent:
        """A single benign login: home location, common resource, mostly successful."""
        user = self._rng.choice(self.users)
        # ~4% benign failures (fat-fingered passwords) so failure != attack.
        success = self._rng.random() > 0.04
        return self._event(user, ts, success=success)

    def normal_stream(self, n: int, start: datetime | None = None) -> Iterator[AuthEvent]:
        """Yield ``n`` benign events spaced a few seconds apart."""
        ts = start or datetime(2026, 1, 1, tzinfo=UTC)
        for _ in range(n):
            ts = ts + timedelta(seconds=self._rng.randint(1, 30))
            yield self.normal_event(ts)

    # -- attack injectors (each returns labeled events) ------------------------

    def impossible_travel(self, user: str, ts: datetime) -> list[LabeledEvent]:
        """Two successful logins minutes apart from different countries/IPs."""
        away_country, away_prefix = self._rng.choice(
            [loc for loc in _HOME_LOCATIONS if loc != self._home[user]]
        )
        first = self._event(user, ts)
        second = self._event(
            user, ts + timedelta(minutes=3), country=away_country, ip_prefix=away_prefix
        )
        return [
            LabeledEvent(first, True, "impossible_travel"),
            LabeledEvent(second, True, "impossible_travel"),
        ]

    def brute_force(self, user: str, ts: datetime, attempts: int = 20) -> list[LabeledEvent]:
        """A burst of failed logins against one account, then a success."""
        out: list[LabeledEvent] = []
        for i in range(attempts):
            ev = self._event(user, ts + timedelta(seconds=i), success=False, action="login")
            out.append(LabeledEvent(ev, True, "brute_force"))
        breach = self._event(user, ts + timedelta(seconds=attempts), success=True)
        out.append(LabeledEvent(breach, True, "brute_force"))
        return out

    def credential_stuffing(self, ts: datetime, n_users: int = 15) -> list[LabeledEvent]:
        """One attacker IP tries many accounts — mostly failures, a few hits."""
        _, atk_prefix = self._rng.choice(_HOME_LOCATIONS)
        targets = self._rng.sample(self.users, k=min(n_users, len(self.users)))
        out: list[LabeledEvent] = []
        for i, user in enumerate(targets):
            success = self._rng.random() < 0.1
            ev = self._event(user, ts + timedelta(seconds=i), success=success, ip_prefix=atk_prefix)
            out.append(LabeledEvent(ev, True, "credential_stuffing"))
        return out

    def privilege_escalation(self, user: str, ts: datetime) -> list[LabeledEvent]:
        """A normal user suddenly hitting sensitive resources."""
        out: list[LabeledEvent] = []
        for i, resource in enumerate(_SENSITIVE_RESOURCES):
            ev = self._event(
                user, ts + timedelta(seconds=i * 5), resource=resource, action="access"
            )
            out.append(LabeledEvent(ev, True, "privilege_escalation"))
        return out

    # -- full labeled dataset --------------------------------------------------

    def labeled_dataset(
        self, n_normal: int = 500, n_attacks: int = 10, start: datetime | None = None
    ) -> list[LabeledEvent]:
        """Build a shuffled, time-sorted mix of benign traffic and injected attacks.

        Returns events sorted by timestamp (as a real stream would arrive), each carrying
        its ground-truth label for evaluation.
        """
        ts = start or datetime(2026, 1, 1, tzinfo=UTC)
        events: list[LabeledEvent] = [
            LabeledEvent(e, False, "normal") for e in self.normal_stream(n_normal, start=ts)
        ]

        injectors = [
            lambda t: self.impossible_travel(self._rng.choice(self.users), t),
            lambda t: self.brute_force(self._rng.choice(self.users), t),
            self.credential_stuffing,
            lambda t: self.privilege_escalation(self._rng.choice(self.users), t),
        ]
        span_seconds = max(n_normal * 15, 60)
        for _ in range(n_attacks):
            offset = timedelta(seconds=self._rng.randint(0, span_seconds))
            events.extend(self._rng.choice(injectors)(ts + offset))

        events.sort(key=lambda le: le.event.timestamp)
        return events

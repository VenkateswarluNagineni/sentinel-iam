"""Validation & normalization layer.

Upstream sources (SSO, VPN, app logins) each speak their own JSON dialect. This layer
turns raw source records into the canonical ``AuthEvent`` via per-source **adapters**, and
sends anything that fails validation to a **dead-letter** list instead of crashing the
stream — so one malformed record never takes down a batch.
"""

from __future__ import annotations

from collections.abc import Callable, Iterable
from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel

from sentinel.schema import AuthEvent

Adapter = Callable[[dict[str, Any]], AuthEvent]


class NormalizationError(Exception):
    """Raised when a raw record can't be normalized (bad adapter or bad data)."""


class DeadLetter(BaseModel):
    """A record that failed normalization, kept for replay/inspection."""

    source: str
    raw: dict[str, Any]
    error: str


def sso_adapter(raw: dict[str, Any]) -> AuthEvent:
    """Adapter for SSO/IdP logs (Okta-style field names, ISO-8601 timestamps)."""
    return AuthEvent(
        event_id=str(raw["id"]),
        user_id=raw["actor"],
        source_ip=raw["src_ip"],
        resource=raw.get("app", "sso"),
        action=raw.get("event_type", "login"),
        success=str(raw["result"]).upper() in {"SUCCESS", "ALLOW", "0"},
        country=raw.get("geo"),
        timestamp=datetime.fromisoformat(raw["@timestamp"]),
    )


def vpn_adapter(raw: dict[str, Any]) -> AuthEvent:
    """Adapter for VPN gateway logs (epoch-second timestamps, numeric status)."""
    return AuthEvent(
        event_id=str(raw["session"]),
        user_id=raw["username"],
        source_ip=raw["client_addr"],
        resource=raw.get("gateway", "vpn"),
        action="login",
        success=int(raw.get("status", 1)) == 0,
        country=raw.get("country"),
        timestamp=datetime.fromtimestamp(raw["ts"], tz=UTC),
    )


class Normalizer:
    """Registry of source adapters with batch dead-lettering."""

    def __init__(self) -> None:
        self._adapters: dict[str, Adapter] = {}

    def register(self, source: str, adapter: Adapter) -> None:
        self._adapters[source] = adapter

    def normalize(self, source: str, raw: dict[str, Any]) -> AuthEvent:
        """Normalize one record, raising ``NormalizationError`` on any failure."""
        adapter = self._adapters.get(source)
        if adapter is None:
            raise NormalizationError(f"no adapter registered for source '{source}'")
        try:
            return adapter(raw)
        except NormalizationError:
            raise
        except (KeyError, ValueError, TypeError) as exc:
            raise NormalizationError(f"{type(exc).__name__}: {exc}") from exc

    def normalize_batch(
        self, records: Iterable[tuple[str, dict[str, Any]]]
    ) -> tuple[list[AuthEvent], list[DeadLetter]]:
        """Normalize a batch, splitting successes from dead-letters.

        Returns ``(events, dead_letters)``. A single bad record is captured as a
        ``DeadLetter`` (with its error and original payload) and never aborts the batch.
        """
        events: list[AuthEvent] = []
        dead: list[DeadLetter] = []
        for source, raw in records:
            try:
                events.append(self.normalize(source, raw))
            except NormalizationError as exc:
                dead.append(DeadLetter(source=source, raw=raw, error=str(exc)))
        return events, dead


def default_normalizer() -> Normalizer:
    """A normalizer pre-loaded with the built-in SSO and VPN adapters."""
    norm = Normalizer()
    norm.register("sso", sso_adapter)
    norm.register("vpn", vpn_adapter)
    return norm

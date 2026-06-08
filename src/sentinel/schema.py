"""Canonical auth-event schema.

Every upstream source (SSO, VPN, app login) is normalized into this model before it
hits Kafka, so the streaming and detection layers can stay source-agnostic.
"""

from __future__ import annotations

from datetime import UTC, datetime

from pydantic import BaseModel, Field, field_validator


class AuthEvent(BaseModel):
    """A single normalized authentication / access event."""

    event_id: str
    user_id: str
    source_ip: str
    resource: str = Field(description="Resource or application being accessed")
    action: str = Field(description="e.g. login, mfa_challenge, token_refresh")
    success: bool
    country: str | None = None
    timestamp: datetime

    @field_validator("timestamp")
    @classmethod
    def _ensure_tz(cls, v: datetime) -> datetime:
        # Detection windows assume tz-aware UTC; coerce naive timestamps.
        return v.replace(tzinfo=UTC) if v.tzinfo is None else v.astimezone(UTC)

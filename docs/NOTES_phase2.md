# Phase 2 — Validation & normalization layer (design notes)

## What landed
- `normalize.py`:
  - `Adapter` = `Callable[[dict], AuthEvent]`; per-source functions that map a raw record
    onto the canonical schema. Two built-ins: `sso_adapter` (Okta-style fields, ISO-8601
    time) and `vpn_adapter` (epoch-second time, numeric status).
  - `Normalizer` — adapter registry with `normalize` (raises `NormalizationError`) and
    `normalize_batch` (splits good events from `DeadLetter`s).
  - `DeadLetter` — keeps the source, raw payload, and error for inspection/replay.
  - `default_normalizer()` — pre-registers the SSO + VPN adapters.
- 5 tests; ruff + pytest green.

## Decisions & trade-offs
- **Adapters at the edge.** Each source's quirks (field names, timestamp format, how
  "success" is encoded) live in one small adapter. Everything downstream sees only
  `AuthEvent`, so features/detectors never branch on source type — the payoff of the
  canonical schema from Phase 0.
- **Dead-letter, don't crash.** In a stream, one malformed record must not abort the batch.
  `normalize_batch` captures failures as `DeadLetter`s (with the original payload + reason)
  and keeps going — the standard pattern for resilient ingestion and the basis for replay.
- **Narrow exception catching.** Adapters are expected to raise `KeyError`/`ValueError`/
  `TypeError` on bad data; those are converted to `NormalizationError`. Unexpected errors
  are *not* swallowed, so real bugs still surface instead of silently dead-lettering.
- **`success` normalization is explicit.** SSO encodes outcome as `SUCCESS/ALLOW`, VPN as a
  numeric status code. Each adapter maps its own convention to a clean boolean, so detectors
  get a consistent signal.

## Next
Phase 3: Kafka producer/consumer wrappers and topic config, with the Phase-1 generator as
the producer and this normalizer running on the consume side.

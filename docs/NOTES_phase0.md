# Phase 0 — Scaffold (design notes)

Plain-language notes so I can explain every decision in an interview.

## What landed
- `src/` layout package `sentinel` (installable, keeps imports clean vs. flat layout).
- `config.py`: env-driven `Settings` dataclass with validation. Frozen dataclass = no
  accidental mutation of config at runtime.
- `schema.py`: the canonical `AuthEvent` (pydantic). **Key idea:** normalize every
  source into one schema at the edge so the streaming/detection code never branches on
  source type. Timestamps are coerced to tz-aware UTC because windowed streaming math
  breaks on naive/mixed-tz timestamps.
- Tests for both, so CI is green from commit one.

## Decisions & trade-offs
- **Heavy deps are optional extras** (`stream`, `ml`, `serve`). Phase 0 stays
  lightweight so CI installs in seconds; Spark/Torch only arrive when their phases do.
- **Why an ensemble later (not one model):** point anomalies (Isolation Forest),
  behavioural drift (HDBSCAN), and novel/unseen patterns (BERT + OOD) are genuinely
  different failure modes. One model can't cover all three; fusing them does.
- **Streaming-first framing:** the hard part of production anomaly detection isn't the
  model, it's bounded-latency stateful features + drift over time. The roadmap front-
  loads the streaming/feature-store work for that reason.

## Next
Phase 1: a synthetic auth-log generator with injectable attack patterns, so every later
phase has reproducible data and measurable detection quality.

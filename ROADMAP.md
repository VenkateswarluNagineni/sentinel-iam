# Sentinel-IAM Roadmap

Built in public, one phase at a time. Each phase ships working, tested code and a short
design note in `docs/NOTES_<phase>.md`. The daily build routine picks up the next
unchecked phase.

> Convention: `[ ]` not started · `[~]` in progress · `[x]` done.

## Foundations
- [x] **Phase 0 — Scaffold.** Package layout, config + canonical `AuthEvent` schema,
  tests, ruff, CI, Docker skeleton, this roadmap.
- [x] **Phase 1 — Synthetic auth-log generator.** Realistic SSO/VPN/app login stream
  with injectable anomaly patterns (impossible travel, credential stuffing, privilege
  spikes) for reproducible testing.
- [ ] **Phase 2 — Event validation & normalization layer.** Source adapters → canonical
  `AuthEvent`; dead-letter handling for malformed records.
- [ ] **Phase 3 — Kafka I/O.** Producer/consumer wrappers, topic config, replayable
  offsets, integration test against an ephemeral broker.

## Streaming features
- [ ] **Phase 4 — Feature definitions.** Per-user/per-IP rolling features: login
  velocity, geo-velocity (impossible travel), rare-resource access, failure ratios.
- [ ] **Phase 5 — Spark Structured Streaming job.** Windowed/stateful feature
  computation with watermarking and checkpointing.
- [ ] **Phase 6 — Online feature store.** Redis online store + parquet offline store;
  point-in-time correctness for training/serving parity.

## Detection
- [ ] **Phase 7 — Isolation Forest baseline.** Point-anomaly model + training pipeline +
  evaluation on injected anomalies (precision/recall, PR-AUC).
- [ ] **Phase 8 — HDBSCAN behavioural clustering.** Cluster normal behaviour; score
  distance-to-cluster as a complementary signal.
- [ ] **Phase 9 — BERT log embeddings + OOD scoring.** Embed event sequences; energy/
  Mahalanobis OOD score for novel attack patterns.
- [ ] **Phase 10 — Ensemble risk scorer.** Calibrated fusion of the three detectors into
  a single `[0,1]` risk score with per-alert feature attributions.

## Serving & ops
- [ ] **Phase 11 — FastAPI scoring + query service.** Score events, fetch alert detail,
  health/metrics endpoints.
- [ ] **Phase 12 — Alerting.** Publish high-risk events to the alerts topic with
  explanation payloads; suppression/dedup.
- [ ] **Phase 13 — Drift monitoring (Evidently).** Scheduled data/concept-drift reports;
  alert when feature distributions shift.
- [ ] **Phase 14 — Airflow retrain DAG.** Backfill features, retrain detectors, validate
  against a champion model, promote on win.
- [ ] **Phase 15 — Streamlit analyst dashboard.** Live alert feed, drill-down, cluster
  explorer, drift panel.

## Hardening & polish
- [ ] **Phase 16 — Benchmark harness.** Throughput/latency under load; documented SLOs.
- [ ] **Phase 17 — Observability.** Structured logging, Prometheus metrics, tracing.
- [ ] **Phase 18 — Config & secrets management.** Profiles for local/staging/prod.
- [ ] **Phase 19 — End-to-end docker-compose demo.** One command spins the full stack.
- [ ] **Phase 20 — Architecture deep-dive docs + demo GIF.** Recruiter-ready walkthrough.

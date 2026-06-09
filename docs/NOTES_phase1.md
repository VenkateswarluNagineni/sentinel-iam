# Phase 1 — Synthetic auth-log generator (design notes)

## What landed
- `generator.py`: `AuthLogGenerator` — a seeded simulator that emits benign auth traffic
  and injects four labeled attack scenarios:
  - **impossible_travel** — two successful logins minutes apart from different countries.
  - **brute_force** — a burst of failed logins on one account, then a breach success.
  - **credential_stuffing** — one attacker IP sprays many accounts, mostly failing.
  - **privilege_escalation** — a normal user suddenly touching sensitive resources.
- `LabeledEvent` pairs each `AuthEvent` with `is_anomaly` + `scenario` ground truth.
- `labeled_dataset(...)` returns a time-sorted mix of benign + injected attacks.
- 10 unit tests, ruff + pytest green.

## Decisions & trade-offs
- **Why synthetic, not a public dataset.** Real auth logs are sensitive and rarely labeled.
  A seeded generator gives reproducible, *labeled* data so every later detector can be
  scored on precision/recall against known truth — and reviewers can run it with zero setup.
- **Ground-truth labels from the start.** Anomaly detection is worthless if you can't
  measure it. Emitting labels now means phases 7–10 (Isolation Forest, HDBSCAN, BERT/OOD,
  ensemble) get an honest scoreboard for free.
- **Realistic benign noise.** ~4% of *normal* logins fail (fat-fingered passwords) and each
  user has a stable home country. This stops detectors from learning the lazy rule
  "failure = attack" or "foreign IP = attack", which is exactly the trap that wrecks naive
  models in production.
- **Stable per-user home location.** Geo-velocity / impossible-travel only means something
  if a user *has* a usual location, so home country/IP is fixed per user at construction.
- **Seeded `random.Random` instance (not global `random`).** Keeps generation deterministic
  and isolated — two generators with the same seed produce identical streams, and tests
  assert that.

## Trade-offs / future work
- The generator models event *content*, not yet realistic temporal rhythms (business hours,
  weekend dips). That arrives with the feature/windowing work in phases 4–5.
- Attack volumes are parameterized but simple; later we can tune them to hit target base
  rates per scenario for ROC/PR curve stability.

## Next
Phase 2: the validation/normalization layer (source adapters → canonical `AuthEvent`,
dead-letter handling), then Kafka I/O in Phase 3 — at which point this generator becomes
the producer feeding the stream.

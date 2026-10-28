# Changelog

All notable changes to this project are documented here. The format follows
Keep a Changelog, and the project uses semantic versioning.

## [0.1.0]

First release.

### Added

- Deterministic prompt-injection guardrail with a three-state verdict (allow,
  review, block), eleven rules across eight techniques, and evidence attached to
  every decision. Spec 001.
- Tamper-evident, HMAC-chained decision ledger with single-pass verification and
  optional JSONL persistence. Spec 002.
- Measurement harness that scores the baseline against a planted ground-truth
  dataset and breaks recall out by technique. The CI gate fails the build if the
  baseline regresses.
- FastAPI surface with standard-library authentication (PBKDF2 password hashing
  and a hand-rolled HS256 JWT) and a static, dependency-free console: a login
  screen and a dashboard with a scenario editor, verdict view, live metrics and
  a ledger viewer. The console falls back to an in-browser mirror engine with no
  backend.
- Container image (non-root, read-only root filesystem, dropped capabilities)
  and a one-command `docker compose up`.
- Blocking CI pipeline: secret scan, lint, strict types, test matrix with a
  coverage ratchet, SAST, dependency audit, CodeQL, the domain eval gate, a
  CycloneDX SBOM and a build-provenance attestation.
- Documentation: architecture with diagrams, an LLM threat model, a metrics and
  calibration guide, and three architecture decision records.

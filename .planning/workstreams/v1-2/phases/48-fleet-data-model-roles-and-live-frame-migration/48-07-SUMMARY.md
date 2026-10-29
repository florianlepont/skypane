---
phase: 48-fleet-data-model-roles-and-live-frame-migration
plan: 07
subsystem: companion health
tags: [health, fleet.db, i18n, anomaly]
requires: [48-02, 48-04]
provides:
  - fleet_fault input to collect_anomalies and overall_severity
  - bilingual Health anomaly for the byos fleet.db fallback
affects: [companion/health_signals.py, companion/i18n_fr/health.py]
key-files:
  modified:
    - companion/health_signals.py
    - companion/i18n_fr/health.py
  created:
    - companion/test_health_fleet_status.py
requirements: [DATA-02]
metrics:
  completed: 2026-10-29
  tasks: 1
---

# Phase 48 Plan 07: Fleet fallback on the Health page Summary

The Health page now shows one bilingual anomaly and a warn severity when byos's `fleet_status.json` says `fault`, read through a guarded `fleet_db.read_status` (the companion never opens fleet.db).

## What was built

- `health_signals.py`: `fleet_fault=False` keyword on `collect_anomalies` (sentence appended last) and `overall_severity` (warn, never lowers error); `_read_fleet_status` guard returning None on any exception, stored in the inputs dict; fault only when the state equals `fleet_db.STATUS_FAULT`. No new snapshot key: `severity` and `anomalies` already feed the freshness token.
- `i18n_fr/health.py`: French sentence for `health.fleet_database_unavailable`.
- `test_health_fleet_status.py`: unit tests, state-directory tests (none, absent, ok, malformed, fault, read failure) and served-page tests in English and French.
- Only the boolean state is used; the status detail is never rendered (T-48-38/39).

## Deviations from Plan

- [Rule 1 - Bug] French string needed a no-break space before the colon (caught by `test_i18n.py`); fixed.
- Served banner pills drop the trailing full stop, so the served-page tests assert on the sentence without it.

Owner-confirmable note from the plan stands: this is a small companion change this phase.

## Commits

- test: failing tests (RED)
- 57e0bb1: feat(48-07) implementation (GREEN)

## Verification

Targeted health, i18n and guard tests, ruff, comment-history and function-size checks pass. The full `companion` run passed except the nbsp i18n test, fixed afterwards and re-run green.

## Self-Check: PASSED

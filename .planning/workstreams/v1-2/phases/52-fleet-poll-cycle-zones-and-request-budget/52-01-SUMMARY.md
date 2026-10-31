---
phase: 52-fleet-poll-cycle-zones-and-request-budget
plan: 01
subsystem: poll-budget
tags: [adsb, rate-limit, flock, fleet]
requires: []
provides:
  - "server/request_budget.py: RequestLedger, BudgetUnavailable, MIN_SPACING_S, PROVIDER_PAUSE_S"
  - "server/zone_fetch.py: fetch_zone, ZoneFetch"
affects: [52-02, 52-03, 52-04]
tech-stack:
  added: []
  patterns: ["flock leaf lock held across a bounded wait", "sanitise-on-read for untrusted state files"]
key-files:
  created:
    - server/request_budget.py
    - server/zone_fetch.py
    - server/test_request_budget.py
    - server/test_zone_fetch.py
  modified: []
key-decisions:
  - "A capped future-dated pause is persisted when observed, so it cannot be re-extended on every read"
requirements-completed: [FLT-03]
duration: short
completed: 2026-10-30
---

# Phase 52 Plan 01: Request budget and zone fetch Summary

Persisted, flock-guarded ADS-B request ledger (1.1 s global spacing, 60 s shared provider pause, zone last-served map) plus a sequential, budgeted `fetch_zone` that degrades to single-source or all-failed without raising.

## Commits
- 8d35aba: request ledger (Task 1)
- cef414f: zone fetch (Task 2)

## Verification
- `pytest server/test_request_budget.py server/test_zone_fetch.py`: 38 passed
- ruff, mypy (both new modules), function-size gate and comment-history guard clean

## Deviations from Plan

**1. [Rule 1 - Bug] Future-dated pause was re-clamped on every read**
- Found during: Task 1 test run
- Issue: clamping `pause_until` to `now + 60` at read time meant a stored pause 10 hours ahead was never released.
- Fix: the sanitiser reports when it capped a value and `acquire` persists the capped document when it refuses a paused provider.
- Files: server/request_budget.py

No other deviations. The new modules were not added to the `[tool.mypy]` module list (the plan defers that), so pyproject.toml is untouched.

## Known Stubs
None.

## Self-Check: PASSED

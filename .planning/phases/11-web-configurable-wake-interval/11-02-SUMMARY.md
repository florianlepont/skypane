---
phase: 11-web-configurable-wake-interval
plan: 02
subsystem: api
tags: [python, http-server, stdlib, vendor-boundary, config-delivery]

# Dependency graph
requires:
  - phase: 11-web-configurable-wake-interval (plan 11-01)
    provides: "server/device_config.py's WAKE_INTERVAL_MIN_S/MAX_S, normalise_wake_interval_s(), and the load_device_config()/save_device_config() wake_interval_s key/keyword this plan reads by raw JSON key name"
provides:
  - "stub-server/byos_server.py: WAKE_INTERVAL_MIN_S=60/WAKE_INTERVAL_MAX_S=3600 (independently redefined duplicates, never imported)"
  - "stub-server/byos_server.py: read_wake_interval_s(state_dir, default) - never-raising fail-open read of device_config.json's wake_interval_s"
  - "GET /device/v1/display's sleep_s now feeds read_wake_interval_s()'s result (falling back to --sleep) into quiet_hours_sleep_s() as base_sleep_s, replacing the direct self.args.sleep reference"
  - "stub-server/VENDOR.md local-modification 6 and updated re-pinning checklist"
  - "stub-server/test_poll_cycle.py: 5 new checks, EXPECTED_CHECK_COUNT 29 -> 34"
affects: [11-03-config-page-wake-interval-form, 11-04-companion-env-prefill]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Vendor-boundary read function: independently redefined bound constants + a never-raising fail-open read copying read_led_enabled()'s try/except/isinstance shape, never importing server.* across the stdlib-only boundary"
    - "No re-clamp after downstream extension: a value gated on write is deliberately left unclamped after a later function (quiet_hours_sleep_s()) extends it, because the gate protects the stored field, not the delivered value"

key-files:
  created: []
  modified:
    - stub-server/byos_server.py
    - stub-server/test_poll_cycle.py
    - stub-server/VENDOR.md

key-decisions:
  - "read_wake_interval_s() is an independently-written, behaviourally-compatible reimplementation of normalise_wake_interval_s()'s read half, not a byte-for-byte pinned duplicate like seconds_until_quiet_hours_end() - it follows read_led_enabled()'s/read_quiet_hours()'s existing precedent instead"
  - "No second bounds check is added after quiet_hours_sleep_s() returns - the 60-3600 range gates the stored config field only; the delivered sleep_s is allowed to exceed 3600 during an active quiet-hours window, matching Phase 10's existing max(base_sleep_s, remaining) contract"

requirements-completed: []  # unmapped backlog phase promoted from SEED-002 - this plan's own frontmatter declares requirements: []

coverage:
  - id: D1
    description: "GET /device/v1/display returns the saved wake_interval_s as sleep_s when one is set, and the --sleep CLI value when it is not, with quiet_hours_sleep_s() still extending the result past 3600s during an active window"
    verification:
      - kind: integration
        ref: "stub-server/test_poll_cycle.py#_wake_interval_integration_delivers_configured_value"
        status: pass
      - kind: integration
        ref: "stub-server/test_poll_cycle.py#_wake_interval_integration_below_floor_falls_back_to_default"
        status: pass
      - kind: unit
        ref: "stub-server/test_poll_cycle.py#_wake_interval_layers_under_quiet_hours"
        status: pass
    human_judgment: false
  - id: D2
    description: "read_wake_interval_s() never raises and degrades every hostile value (missing/unreadable/malformed/non-dict/key-absent/wrong-typed/bool/out-of-range) to the caller-supplied default"
    verification:
      - kind: unit
        ref: "stub-server/test_poll_cycle.py#_wake_interval_fail_open_never_raises"
        status: pass
      - kind: unit
        ref: "stub-server/test_poll_cycle.py#_wake_interval_happy_path"
        status: pass
    human_judgment: false

duration: 13min
completed: 2026-09-04
status: complete
---

# Phase 11 Plan 02: Wake-interval delivery in stub-server Summary

**Added a never-raising `read_wake_interval_s()` to `stub-server/byos_server.py` and rebased `GET /device/v1/display`'s `sleep_s` to use it as the base `quiet_hours_sleep_s()` extends, so a saved wake interval reaches the device on its very next poll with zero firmware or deployment change.**

## Performance

- **Duration:** 13 min
- **Started:** 2026-09-04T07:49:54+02:00
- **Completed:** 2026-09-04T08:01:46+02:00
- **Tasks:** 2 completed
- **Files modified:** 3

## Accomplishments
- `WAKE_INTERVAL_MIN_S`/`WAKE_INTERVAL_MAX_S` (60/3600) independently redefined in `stub-server/byos_server.py`, hand-pinned equal to `server/device_config.py`'s constants of the same names, matching the `_HHMM_RE`/`QUIET_HOURS_TZ` duplicated-not-imported precedent
- `read_wake_interval_s(state_dir, default)` - a best-effort, never-raising read of the shared `device_config.json`'s `wake_interval_s` field, structured as a direct copy of `read_led_enabled()`'s shape, with the mandatory `isinstance(value, int) and not isinstance(value, bool)` bool exclusion
- `/device/v1/display`'s `sleep_s` expression now passes `read_wake_interval_s(self.args.state_dir, self.args.sleep)` as `quiet_hours_sleep_s()`'s `base_sleep_s` argument, instead of `self.args.sleep` directly - `quiet_hours_sleep_s()`'s own signature and body are completely unchanged
- No re-clamp added after `quiet_hours_sleep_s()` returns: an active quiet-hours window still legitimately extends the delivered value past 3600 seconds
- Both the module docstring and `stub-server/VENDOR.md` (local modification 6, and the re-pinning checklist bumped to "all six") record this local modification
- 5 new checks in `stub-server/test_poll_cycle.py`: fail-open across 9 hostile cases (missing file, truncated JSON, non-dict, key-absent, bool, string, float, below-floor, above-ceiling), happy-path including both inclusive bounds, layering under `quiet_hours_sleep_s()` with the no-re-clamp proof, and two real-HTTP integration checks (configured value delivered; below-floor value falls back to the CLI default) - `EXPECTED_CHECK_COUNT` 29 → 34

## Task Commits

Each task was committed atomically:

1. **Task 1: Add read_wake_interval_s() and rebase the /display handler's sleep_s** - `e4883eb` (feat)
2. **Task 2: Add read_wake_interval_s() and delivery coverage to test_poll_cycle.py** - `4e24ef2` (test)

**Plan metadata:** pending (docs: complete plan)

## Files Created/Modified
- `stub-server/byos_server.py` - two bound constants, `read_wake_interval_s()`, the `/device/v1/display` `sleep_s` rebase, docstring update
- `stub-server/test_poll_cycle.py` - 5 new checks, bumped `EXPECTED_CHECK_COUNT`, docstring coverage note
- `stub-server/VENDOR.md` - local modification 6 and the re-pinning checklist

## Decisions Made
- `read_wake_interval_s()` follows the independently-written, behaviourally-compatible precedent `read_led_enabled()`/`read_quiet_hours()` already set, not the byte-for-byte pinned-duplicate precedent `seconds_until_quiet_hours_end()` follows - it is therefore not covered by `_quiet_hours_drift_guard`
- No second bounds check after `quiet_hours_sleep_s()` returns - the 60-3600 gate is deliberately for the stored config field only, per 11-RESEARCH.md Pitfall 4

## Deviations from Plan

None - plan executed exactly as written. All acceptance criteria (harness count, ruff, exact grep matches, `git diff --name-only` per task) verified as specified.

## Issues Encountered
None.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- The delivery mechanism is fully in place and covered by the 34/34 harness - no firmware, deployment, or `deploy/` change was needed or made
- Plan 11-03 (`companion/pages/config_page.py` Settings form) and 11-04 (`companion/app.py` env pre-fill) can proceed independently; neither touches `stub-server/`
- Known transient state (pre-existing, out of this plan's scope): `companion/test_config_page.py` currently has one failing dict-equality assertion missing the new `wake_interval_s` key - this belongs to plan 11-03, which touches that file

---
*Phase: 11-web-configurable-wake-interval*
*Completed: 2026-09-04*

## Self-Check: PASSED
- FOUND: stub-server/byos_server.py
- FOUND: stub-server/test_poll_cycle.py
- FOUND: stub-server/VENDOR.md
- FOUND: .planning/phases/11-web-configurable-wake-interval/11-02-SUMMARY.md
- FOUND: e4883eb
- FOUND: 4e24ef2

---
phase: 12-remote-display-on-off-toggle
plan: 01
subsystem: infra
tags: [python, device-config, registry, json-config]

# Dependency graph
requires:
  - phase: 10-scheduled-quiet-hours
    provides: DEFAULT_QUIET_HOURS_ENABLED / normalise_quiet_hours_enabled() never-raising bool pattern this plan's display_enabled field mirrors
  - phase: 11-web-configurable-wake-interval
    provides: WAKE_INTERVAL_MIN_S / WAKE_INTERVAL_MAX_S bounds that DISPLAY_OFF_SLEEP_S is validated against
provides:
  - device_config.DEFAULT_DISPLAY_ENABLED (True) and device_config.DISPLAY_OFF_SLEEP_S (300) constants
  - device_config.normalise_display_enabled() - never-raising, fail-open bool normaliser
  - load_device_config()'s eighth key, display_enabled (always present, True by default)
  - save_device_config()'s eighth parameter, display_enabled=None (None means carry forward)
affects: [12-03-vendored-server-sleep-pin, 12-04-poll-loop-gate, 12-05-settings-checkbox]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Boolean registry field with fail-open default (normalise_display_enabled): every hostile/malformed on-disk shape degrades to True, matching normalise_led_enabled()/normalise_quiet_hours_enabled()'s isinstance(value, bool)-only contract"
    - "Fixed off-state cadence constant decoupled from a user-configurable interval (DISPLAY_OFF_SLEEP_S = 300, independent of wake_interval_s), validated to sit inside the existing WAKE_INTERVAL_MIN_S/MAX_S band rather than needing its own latitude"

key-files:
  created: []
  modified:
    - server/device_config.py
    - server/test_config_history.py

key-decisions:
  - "DEFAULT_DISPLAY_ENABLED = True (D-09): explicit boolean default following DEFAULT_LED_ENABLED/DEFAULT_QUIET_HOURS_ENABLED precedent, never absence-means-off, so no existing installation changes behavior until someone opts in"
  - "DISPLAY_OFF_SLEEP_S = 300 (D-01) is a fixed constant that replaces wake_interval_s entirely during an off period rather than deriving from it, and deliberately sits inside [WAKE_INTERVAL_MIN_S, WAKE_INTERVAL_MAX_S] so it needs none of quiet_hours_sleep_s()'s ceiling-exceeding latitude"
  - "normalise_display_enabled() is fail-open by design: every degradation path (missing/unreadable/malformed file, non-dict document, wrong-typed value) leaves display_enabled True, so a corrupted config can never be the reason a frame goes dark"

requirements-completed: []

coverage:
  - id: D1
    description: "load_device_config() always returns eight keys, the eighth being display_enabled, True on a fresh install"
    verification:
      - kind: unit
        ref: "server/test_config_history.py#_missing_state_dir_yields_defaults"
        status: pass
    human_judgment: false
  - id: D2
    description: "A hostile or stale on-disk display_enabled value (0, \"false\", null, non-dict document) degrades to True and never reaches a caller"
    verification:
      - kind: unit
        ref: "server/test_config_history.py#_hand_written_hostile_display_enabled_yields_true_but_false_survives"
        status: pass
    human_judgment: false
  - id: D3
    description: "save_device_config() rejects a non-bool display_enabled with ValueError and leaves any pre-existing file byte-identical"
    verification:
      - kind: unit
        ref: "server/test_config_history.py#_save_display_enabled_rejects_non_bool_and_leaves_file_byte_identical"
        status: pass
    human_judgment: false
  - id: D4
    description: "A save that supplies no display_enabled carries the stored value forward unchanged"
    verification:
      - kind: unit
        ref: "server/test_config_history.py#_save_display_enabled_false_round_trips_and_carries_forward"
        status: pass
    human_judgment: false
  - id: D5
    description: "DISPLAY_OFF_SLEEP_S is 300 and sits inside the inclusive [WAKE_INTERVAL_MIN_S, WAKE_INTERVAL_MAX_S] band"
    verification:
      - kind: unit
        ref: "server/.venv/bin/python3 -c \"... assert d.WAKE_INTERVAL_MIN_S <= d.DISPLAY_OFF_SLEEP_S <= d.WAKE_INTERVAL_MAX_S ...\" (plan Task 1 verify command)"
        status: pass
    human_judgment: false

# Metrics
duration: 10min
completed: 2026-09-05
status: complete
---

# Phase 12 Plan 01: display_enabled registry field + DISPLAY_OFF_SLEEP_S constant Summary

**Added a fail-open `display_enabled` boolean to `server/device_config.py`'s eight-key registry contract and a fixed 300s off-state cadence constant (`DISPLAY_OFF_SLEEP_S`), following `normalise_led_enabled()`'s never-raising pattern exactly.**

## Performance

- **Duration:** ~10 min
- **Completed:** 2026-09-05
- **Tasks:** 2
- **Files modified:** 2

## Accomplishments
- `DEFAULT_DISPLAY_ENABLED = True` (D-09) and `DISPLAY_OFF_SLEEP_S = 300` (D-01), the latter documented as inside the `[WAKE_INTERVAL_MIN_S, WAKE_INTERVAL_MAX_S]` band and cross-referencing `stub-server/byos_server.py`'s independent redefinition (plan 12-03)
- `normalise_display_enabled(value)`: returns `value` unchanged only for a real bool, otherwise `DEFAULT_DISPLAY_ENABLED` - fail-open by design, documented in its own docstring
- `load_device_config()` now returns eight keys (`display_enabled` added); `save_device_config()` accepts an eighth `display_enabled=None` keyword, validated before the file is ever touched and carried forward when omitted
- `server/test_config_history.py` extended from 45 to 49 checks: the 8 pre-existing whole-config dict equality assertions retargeted (not weakened) to include `"display_enabled": True`, plus 4 new checks covering the bool-only gotcha, hostile-on-disk fail-open degradation, save round-trip + carry-forward, and save-rejection with byte-identity proof

## Task Commits

1. **Task 1: Add the display_enabled registry field and the DISPLAY_OFF_SLEEP_S constant** - `3fc9fd2` (feat)
2. **Task 2: Extend server/test_config_history.py, including the eight full-config dict literals that fail closed on a new key** - `98ccc26` (test)

_No plan-metadata commit yet - the orchestrator handles STATE.md/ROADMAP.md/SUMMARY.md commits separately._

## Files Created/Modified
- `server/device_config.py` - `DEFAULT_DISPLAY_ENABLED`, `DISPLAY_OFF_SLEEP_S`, `normalise_display_enabled()`, eighth key on `load_device_config()`, eighth parameter on `save_device_config()`
- `server/test_config_history.py` - 8 whole-config dict literals retargeted with `display_enabled: True`; 4 new checks; `EXPECTED_CHECK_COUNT` bumped 45 -> 49 (harness-verified, not grepped)

## Decisions Made
- No deviations from the interface contract fixed in the plan (`DEFAULT_DISPLAY_ENABLED`, `normalise_display_enabled()`, `load_device_config()["display_enabled"]`, `save_device_config(..., display_enabled=None)`, `DISPLAY_OFF_SLEEP_S`) - all names and semantics match exactly what plans 12-03/12-04/12-05 are specified to consume.

## Deviations from Plan

None - plan executed exactly as written. Both tasks' `<behavior>` and `<action>` specifications were implemented verbatim; the pre-edit baseline (45/45 for `test_config_history.py`, 51/51 for `test_poll_loop.py`) was measured by running the harnesses (not grepped), and the post-edit count (49) was likewise read from a real harness run before setting `EXPECTED_CHECK_COUNT`.

## Issues Encountered
None. `server/test_poll_loop.py` passed 51/51 cleanly in this environment with no digest mismatch to work around.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- The eight-key `load_device_config()` contract, `DEFAULT_DISPLAY_ENABLED`, `normalise_display_enabled()`, and `DISPLAY_OFF_SLEEP_S` are all in place and verified, ready for plan 12-03 (vendored server's `sleep_s` pin), 12-04 (poll-loop gate), and 12-05 (Settings checkbox) to consume in parallel.
- `server/requirements.txt` and `deploy/` are unchanged - no new dependencies or deployment surface introduced.

---
*Phase: 12-remote-display-on-off-toggle*
*Completed: 2026-09-05*

## Self-Check: PASSED

All created/modified files and both task commit hashes verified present on disk / in git history.

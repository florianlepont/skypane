---
phase: 39-server-architecture-run-once-split-state-store-shared-module
plan: 02
subsystem: server
tags: [stdlib-only, battery-hysteresis, quiet-hours, state-store, poll-state, mypy]

requires:
  - phase: 39-server-architecture-run-once-split-state-store-shared-module
    provides: "39-01: scripts/check_function_size.py (the 80-line gate) and 39-ARC-BASELINE.md (the Before record this plan's tests pin against)"
provides:
  - "server/device_policy.py: stdlib-only battery hysteresis (low + critical), the 14-knot discharge curve, wake/sleep constants and quiet-hours window arithmetic, unifying the invalid-time fallback onto the server's 23:00-07:00-and-hold behaviour"
  - "server/state_store.py: single owner of poll_state.json (path, load, compact serialise, save, persist-if-changed, hold-state reader) and the read-only battery_state.json/battery-critical-latch readers"
  - "server/test_device_policy.py, server/test_state_store.py: golden-value, fallback and fail-open tests for both, including the shared invalid-time quiet-hours test named for later plans to point at"
affects: [39-03, 39-04, 39-05, 39-06, 39-07, 39-08, 39-09, 39-10]

tech-stack:
  added: []
  patterns:
    - "New shared modules land unwired: created and tested in their own plan, with zero edits to the callers they will later replace, so a later switch-over plan touches only import lines and call sites."
    - "Byte-identity bridge test: state_store.serialize_poll_state() is asserted equal to both poll_loop._serialize_poll_state()'s live output and a hard-coded literal in the same test, so the next plan (which deletes poll_loop's copy) can drop the live comparison and keep only the literal."
    - "Import-isolation subprocess test diffs sys.modules before/after the import under test, not the raw post-import set, since child_env()'s own sitecustomize.py (installing the pytest-socket network guard) unconditionally imports `requests` before any application code runs."

key-files:
  created:
    - server/device_policy.py
    - server/state_store.py
    - server/test_device_policy.py
    - server/test_state_store.py
  modified: []

key-decisions:
  - "quiet_hours_window()'s invalid-time fallback substitutes each bound's own default independently (D-4's merge), matching device_config.py's existing behaviour exactly - the shared module's fallback needed no new logic, only relocation, since the server side of the disagreement was already the more permissive of the two copies."
  - "mypy was run with --follow-imports=silent for state_store.py (not required by this plan's acceptance criteria, which only requires it for device_policy.py) because a plain run surfaces server/atomic_io.py's own pre-existing untyped-function errors through the import graph; state_store.py itself is fully clean either way. Recorded here for the next plan that runs mypy across more of server/."

requirements-completed: [ARC-02, ARC-05, ARC-06]

duration: ~50min
completed: 2026-09-27
---

# Phase 39 Plan 02: Shared device_policy and state_store modules Summary

**Two new, unwired, stdlib-only modules - `server/device_policy.py` (battery hysteresis, discharge curve, quiet-hours arithmetic with the D-4-unified invalid-time fallback) and `server/state_store.py` (the single owner of poll_state.json) - each byte-identical in behaviour to the poll_loop/device_config/wake code they will later replace.**

## Performance

- **Duration:** ~50 min
- **Tasks:** 2/2 completed
- **Files modified:** 4 created, 0 modified (existing callers untouched, as the plan requires)

## Accomplishments

- `server/device_policy.py` holds, once, `BATTERY_LOW_THRESHOLD_MV`/`BATTERY_LOW_CLEAR_MV`, `BATTERY_CRITICAL_MV`/`BATTERY_CRITICAL_RECOVER_MV`, `BATTERY_CRITICAL_STATE_KEY`, both hysteresis functions, a new `battery_critical_pin_applies()` helper (byos's pin rule, extracted to a pure function), the 14-knot `BATTERY_DISCHARGE_CURVE` with `battery_fraction`/`battery_percent`, the wake/display/critical sleep constants, and the quiet-hours policy (`HHMM_RE`, `QUIET_HOURS_TZ`, the two defaults, `normalise_quiet_hours_time`, `seconds_until_quiet_hours_end`, `quiet_hours_window`, `quiet_hours_status`) - importing only `re`, `datetime` and `zoneinfo`, confirmed by a subprocess `sys.modules` diff test that no `server.*`, `PIL` or `requests` module gets pulled in.
- `server/state_store.py` holds, once, `poll_state_path`, `load_poll_state`, `serialize_poll_state`, `save_poll_state`, `persist_poll_state_if_changed`, `hold_state`, `load_battery_state` and `read_battery_critical` - each a verbatim behavioural copy of today's `poll_loop`/`wake` functions, writing through `atomic_io.atomic_write` via the module attribute so an existing monkeypatch-spy pattern keeps counting correctly.
- 32 new tests (14 + 18) pin every behaviour bullet in the plan, including the golden battery-percent table (16 mv values, cross-checked against `poll_loop._battery_percent_estimate()` before being hard-coded), the four hysteresis boundary values, the shared invalid-time quiet-hours fallback test (`test_quiet_hours_invalid_stored_time_falls_back_to_default_window`, named for later plans to retarget against), and the DST/wrap-midnight anchors reused verbatim from `device_config`'s own test suite.
- `check_function_size.py check --max 80` passes on both new files (9 and 8 functions respectively, none over 80 lines); `mypy --disallow-untyped-defs --explicit-package-bases` passes clean on `server/device_policy.py`; the full suite (2947 passed, 139 skipped) stays green at 94% coverage.

## Task Commits

1. **Task 1: server/device_policy.py (stdlib-only) and server/test_device_policy.py** - `7359d84` (feat)
2. **Task 2: server/state_store.py and server/test_state_store.py** - `2ac87bb` (feat)

## Files Created/Modified

- `server/device_policy.py` - shared battery hysteresis (low + critical), `battery_critical_pin_applies`, the discharge curve, wake/sleep constants, quiet-hours window/status arithmetic; stdlib-only, fully annotated
- `server/test_device_policy.py` - 14 tests: golden battery-percent table, fraction endpoints, both hysteresis functions' boundaries, the pin-rule table, quiet-hours window valid/disabled/fallback cases, `quiet_hours_status` in-window/out-of-window/hostile-epoch cases, the DST/wrap-midnight anchors, and the import-isolation subprocess test
- `server/state_store.py` - single owner of `poll_state.json` (path/load/serialize/save/persist-if-changed/hold-state) plus the read-only `battery_state.json` and battery-critical-latch readers; fully annotated
- `server/test_state_store.py` - 18 tests: `load_poll_state`'s four fail-open shapes, the byte-identity serialisation test (against both `poll_loop`'s live copy and a hard-coded literal), the atomic-write spy round-trip, `persist_poll_state_if_changed`'s 0-write/1-write branches, `hold_state`'s three branches, `load_battery_state`'s five hostile shapes, `read_battery_critical`'s fail-open cases, and `DEFAULT_STATE_DIR`

## Decisions Made

- The invalid-time quiet-hours fallback in `quiet_hours_window()` needed no new branch logic: `device_config.py`'s existing `normalise_quiet_hours_time()` already substitutes each bound's default independently regardless of which bound is invalid, which is exactly D-4's unified (server-side) behaviour. Relocating it verbatim was sufficient; byos's old "treat as disabled" behaviour is what a later plan retires when it switches byos onto this module.
- Added `battery_critical_pin_applies(latched, fresh_mv)` as a new pure function (not present as a standalone function in any current copy - byos's `battery_critical_sleep_s()` inlines the same boolean expression). Extracting it was necessary to give the shared module one canonical, directly-testable pin rule per the plan's own interface spec, rather than duplicating the inline expression a second time inside `quiet_hours_status`-adjacent code.
- Ran mypy with `--follow-imports=silent` for `state_store.py` beyond what this plan's acceptance criteria required, to confirm the new file itself has no type errors; the plain (non-silent) run surfaces `server/atomic_io.py`'s own pre-existing untyped functions through the import graph, which is out of this plan's scope (`atomic_io.py` is unmodified).

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Removed a stray decision-ID reference from a test docstring**
- **Found during:** Task 2's verification step (`scripts/check_comment_history.py check`, run across both tasks' files together)
- **Issue:** `server/test_device_policy.py`'s `test_quiet_hours_invalid_stored_time_falls_back_to_default_window` docstring included `(D-4)`, violating the project's "no plan/decision IDs in comments" rule enforced by the comment-history guard - this would have failed CI.
- **Fix:** Removed the `(D-4)` parenthetical from the docstring; the sentence reads the same without it.
- **Files modified:** `server/test_device_policy.py`
- **Verification:** `server/.venv/bin/python scripts/check_comment_history.py check` exits 0; the 14 device_policy tests still pass.
- **Committed in:** `2ac87bb` (part of Task 2's commit, since it was caught while running Task 2's combined verify command)

---

**Total deviations:** 1 auto-fixed (1 blocking)
**Impact on plan:** Doc-only fix inside a test docstring; no behavioural or test-coverage change. No scope creep.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Known Stubs

None. Both modules are complete, fully tested implementations, not present as a stub or partial API - they are simply not yet imported by any production caller, which is this plan's explicit scope boundary ("Nothing is wired yet").

## Threat Flags

None. `T-39-02` (fail-open state readers), `T-39-03` (anchored `HHMM_RE` gating quiet-hours bounds) and `T-39-04` (stdlib-only import set) are the threat model's own register for this plan and are covered by the tests above (fail-open shapes, the anchored regex reused verbatim, and the subprocess import-isolation test) rather than introducing any new, undocumented surface.

## Self-Check: PASSED

- FOUND: server/device_policy.py
- FOUND: server/state_store.py
- FOUND: server/test_device_policy.py
- FOUND: server/test_state_store.py
- FOUND commit: 7359d84
- FOUND commit: 2ac87bb

## Next Phase Readiness

Both shared modules exist, typed, tested, and behaviour-identical (except the documented D-4 quiet-hours merge) to the code they will replace. Ready for the next plan(s) in this phase to switch `poll_loop.py`, `wake.py`, `stub-server/byos_server.py` and `companion/battery.py` over to them, one owner at a time, per the phase's D-1/D-3 discretion decisions. No blockers.

---
*Phase: 39-server-architecture-run-once-split-state-store-shared-module*
*Completed: 2026-09-27*

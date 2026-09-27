---
phase: 39-server-architecture-run-once-split-state-store-shared-module
plan: 06
subsystem: infra
tags: [device-protocol, byos, quiet-hours, battery-hysteresis, stdlib-only, sys-path-bootstrap]

requires:
  - phase: 39-server-architecture-run-once-split-state-store-shared-module
    provides: "39-02: server/device_policy.py (quiet hours, battery hysteresis, wake/sleep constants) and server/state_store.py (poll_state.json owner, read_battery_critical), both stdlib-only and unwired"
provides:
  - "stub-server/byos_server.py wired onto server/device_policy.py and server/state_store.py via a repo-root sys.path bootstrap, replacing its hand-maintained quiet-hours/battery-critical/wake-interval constants and functions with direct bindings to the shared objects"
  - "The unified (D-4) quiet-hours invalid-time fallback on the device-protocol side: an invalid stored quiet-hours bound now extends the device's sleep through the default 23:00-07:00 window instead of disabling quiet hours, matching the server's own poll-cycle hold decision"
  - "stub-server/test_poll_cycle.py's former byte-for-byte source-text drift guards replaced with identity checks (byos_module.X is device_policy.X) plus attribute-equality checks against server/device_config.py's current values, and a new --help-from-another-cwd subprocess test for the bootstrap"
  - "ARCHITECTURE.md and stub-server/VENDOR.md corrected: byos may import exactly server.device_policy and server.state_store (both stdlib-only) and nothing else from the project; VENDOR.md's local-modification history gets an 11th entry recording the change without altering entries 1-10 or the provenance/licence sections"
affects: [39-07, 39-08, 39-09, 39-10, 39-13]

tech-stack:
  added: []
  patterns:
    - "Repo-root sys.path bootstrap in a previously-vendored file, same shape as server/poll_loop.py's and server/state_store.py's own (_REPO_ROOT = dirname(dirname(abspath(__file__))), inserted only if absent), so a file loaded either as a direct script, via importlib.util.spec_from_file_location, or as a subprocess from any cwd resolves the shared import identically."
    - "Byte-for-byte source-text drift guards retired in favour of identity assertions (X is Y) once both sides bind to the same shared object - strictly stronger than text or even value equality, and immune to incidental reformatting."

key-files:
  created: []
  modified:
    - stub-server/byos_server.py
    - stub-server/test_poll_cycle.py
    - ARCHITECTURE.md
    - stub-server/VENDOR.md

key-decisions:
  - "D-4 implemented as planned: byos's read_quiet_hours() now calls device_policy.quiet_hours_window(data) after its own fail-open file read, so an invalid stored start/end time falls back to the default 23:00-07:00 window (extending sleep) instead of the old 'disabled' outcome. Retargeted, not dropped: the two invalid-time cases moved out of test_read_quiet_hours_fail_open_never_raises into a new test_read_quiet_hours_invalid_time_falls_back_to_default_window, which also exercises quiet_hours_sleep_s()'s extension over the fallback window at the same anchor the existing valid-window test already pins (28000s remaining)."
  - "Kept the historical per-constant identity-check split (one test named for quiet-hours helpers, one for DISPLAY_OFF_SLEEP_S, one for the battery-critical pair) rather than merging all seven identity checks into a single test, since the plan only explicitly renamed the first (drift-guard-named) test and the other two names ('constant parity') still fit an identity+attribute-equality body. WAKE_INTERVAL_MIN_S/MAX_S and the read_battery_critical binding, which had no prior dedicated parity test, were added to the renamed quiet-hours test as the natural catch-all."
  - "_atomic_write()'s docstring, which previously asserted 'byos must never import server.*', was corrected in the same commit (Rule 1: a doc-string claim the new import directly contradicts) to explain why _atomic_write stays a local copy anyway - it serves files (byos_state.json, devices.json, img/*.bin) the two new shared modules don't own - rather than leaving a now-false statement three lines above the new `from server import device_policy, state_store` line."
  - "VENDOR.md's local-modification entries 5, 6 and 8 (the ones that introduced the now-retired hand-duplicated constants/functions) were edited in place to point forward to the new entry 11, rather than left to silently describe code that no longer exists; entries 1-4, 7, 9, 10 and the provenance/licence sections were left untouched, per the plan's instruction."

requirements-completed: []

duration: ~45min
completed: 2026-09-27
---

# Phase 39 Plan 06: byos wired onto server.device_policy and server.state_store Summary

**stub-server/byos_server.py now imports server/device_policy.py and server/state_store.py through a repo-root sys.path bootstrap, retiring its own hand-mirrored quiet-hours/battery-critical/wake-interval copies, with one deliberate, developer-approved behaviour change: an invalid stored quiet-hours time now extends sleep through the default 23:00-07:00 window instead of disabling quiet hours.**

## Performance

- **Duration:** ~45 min
- **Tasks:** 2/2 completed
- **Files modified:** 4 (stub-server/byos_server.py, stub-server/test_poll_cycle.py, ARCHITECTURE.md, stub-server/VENDOR.md)

## Accomplishments

- `stub-server/byos_server.py` gained a repo-root `sys.path` bootstrap (`_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))`, inserted only if absent) and `from server import device_policy, state_store`, then rebound `_HHMM_RE`, `QUIET_HOURS_TZ`, `WAKE_INTERVAL_MIN_S`, `WAKE_INTERVAL_MAX_S`, `DISPLAY_OFF_SLEEP_S`, `BATTERY_CRITICAL_SLEEP_S`, `BATTERY_CRITICAL_RECOVER_MV`, `seconds_until_quiet_hours_end` and `read_battery_critical` to the shared objects those two stdlib-only modules define, deleting the hand-written duplicate arithmetic, regex and constants along with their "mirrored by hand / vendor boundary / drift guard" comments.
- `read_quiet_hours(state_dir)` keeps its own fail-open file read (missing/unreadable/malformed/non-dict → `None`) and then delegates to `device_policy.quiet_hours_window(data)` for the enabled-check and per-bound fallback; `battery_critical_sleep_s()`'s two-branch body became a single call to `device_policy.battery_critical_pin_applies(read_battery_critical(state_dir), fresh_battery_mv)`.
- `stub-server/test_poll_cycle.py`'s three byte-for-byte source-text drift guards became identity checks against the shared objects, plus attribute-equality checks against `server/device_config.py`'s (still-separate) current values; `_extract_def_block`/`_extract_line`/`DEVICE_CONFIG_MODULE_PATH`/`POLL_LOOP_MODULE_PATH` were removed once nothing referenced them. A new `test_help_flag_runs_from_a_different_cwd` proves the bootstrap resolves regardless of the process's working directory.
- `ARCHITECTURE.md`'s "Serving" paragraph and battery-critical-reader sentence, and `stub-server/VENDOR.md`'s local modifications 5/6/8 plus a new local modification 11, now describe the real boundary: byos may import exactly `server.device_policy` and `server.state_store` (both stdlib-only) and nothing else from the project.
- Full `stub-server` suite (64 tests, including `server/test_pipeline_e2e.py`) passes; `ruff check stub-server` and `scripts/check_comment_history.py check` are clean; `byos_server.py --help` exits 0 both from the repo root and from another cwd.

## Task Commits

1. **Task 1: byos imports the shared modules; drift guards become identity checks; invalid-time case retargeted** - `7427539` (feat)
2. **Task 2: correct the vendored-byos rationale in ARCHITECTURE.md, stub-server/VENDOR.md and stub-server/README.md** - `c04ed89` (docs)

## Files Created/Modified

- `stub-server/byos_server.py` - repo-root sys.path bootstrap; `_HHMM_RE`/`QUIET_HOURS_TZ`/`WAKE_INTERVAL_MIN_S`/`WAKE_INTERVAL_MAX_S`/`DISPLAY_OFF_SLEEP_S`/`BATTERY_CRITICAL_SLEEP_S`/`BATTERY_CRITICAL_RECOVER_MV`/`seconds_until_quiet_hours_end`/`read_battery_critical` rebound to `server.device_policy`/`server.state_store`; `read_quiet_hours()` and `battery_critical_sleep_s()` rewritten to delegate to the shared fallback/pin rules; module docstring and `_atomic_write()` docstring corrected to describe the new import boundary
- `stub-server/test_poll_cycle.py` - three source-text drift-guard tests replaced with identity + attribute-equality tests; the two invalid-quiet-hours-time cases moved into a new retargeted test; a new subprocess test for `--help` from another cwd; unused text-extraction helpers and path constants removed
- `ARCHITECTURE.md` - "Serving" paragraph and the battery-critical-latch sentence corrected to name the shared modules and the sys.path route, plus one sentence on the unified invalid-time fallback
- `stub-server/VENDOR.md` - local modifications 5, 6 and 8 updated to point forward to a new local modification 11 (this plan's change); the "ten local modifications" re-pinning list becomes "eleven"; provenance and licence sections untouched
- `stub-server/README.md` - not modified: it has no stdlib-only/import sentence to correct, per the plan's own instruction to skip such a file

## Behaviour changes

**D-4 (developer decision, deliberate, not a bug fix): byos's quiet-hours invalid-config fallback is unified onto the server's behaviour.**

Before this plan, with quiet hours enabled and an invalid stored `quiet_hours_start` or `quiet_hours_end` on disk (wrong shape, wrong type, or missing), `stub-server/byos_server.py`'s `read_quiet_hours()` returned `None`, i.e. quiet hours were treated as **disabled** - the device kept polling and receiving fresh data on its normal cadence through the night.

After this plan, the same invalid config makes `read_quiet_hours()` return `device_policy.quiet_hours_window(data)`'s fallback: each invalid bound is independently replaced by its own default (`23:00` / `07:00`), so quiet hours are treated as **enabled with the default 23:00-07:00 window** - `quiet_hours_sleep_s()` then extends the device's sleep through that window exactly as it would for an explicitly configured one. This matches `server/device_policy.py`'s `quiet_hours_window()`, which the server's own poll-cycle hold decision already used (landed unwired in plan 39-02).

This is the *only* behaviour change in this plan. Every other config shape (missing file, truncated JSON, non-dict document, `quiet_hours_enabled: false`, or `quiet_hours_enabled: "yes"`) still returns `None` exactly as before - reachable, valid-config behaviour is unchanged.

**Test coverage of the change:** the two invalid-time cases (`quiet_hours_start: "25:99"` and `quiet_hours_end: 7`) were moved out of `stub-server/test_poll_cycle.py::test_read_quiet_hours_fail_open_never_raises` (which previously asserted `None` for them) into a new test, `test_read_quiet_hours_invalid_time_falls_back_to_default_window`, which asserts the `("23:00", "07:00")` fallback tuple and the corresponding `quiet_hours_sleep_s()` extension (28000s remaining at the same 00:30-Europe/Paris anchor the existing valid-window test already pins). This mirrors `server/test_device_policy.py::test_quiet_hours_invalid_stored_time_falls_back_to_default_window` from plan 39-02. The old "disabled" outcome is retargeted, not silently dropped.

## Decisions Made

- Kept the historical per-constant test-name split (quiet-hours-helpers / display-off / battery-critical) instead of merging every identity check into one test, since the plan only explicitly renamed the drift-guard-named test; the other two test names ("constant parity") already describe an identity+attribute-equality body correctly.
- `WAKE_INTERVAL_MIN_S`/`MAX_S` and the `read_battery_critical` binding, which had no prior dedicated parity test, were added as identity checks inside the renamed `test_quiet_hours_helpers_are_the_shared_device_policy_objects` test, since it is now the natural catch-all for "byos's shared device-policy objects."
- `_atomic_write()`'s docstring asserted "byos must never import server.*" three lines above the file's own new `from server import device_policy, state_store` - left uncorrected, that would be a load-bearing false statement in a docstring explaining a *different* function's design rationale (why it keeps a local atomic-write copy rather than importing `server.atomic_io`). Corrected in the same commit as a Rule 1 fix: the sentence now explains the real reason (byos owns files - `byos_state.json`, `devices.json`, `img/*.bin` - the two new shared modules don't touch).
- `server.wake.read_battery_critical()` was deliberately left un-migrated (out of this plan's scope, per the plan's "do not touch server/" instruction) - `stub-server/test_poll_cycle.py`'s behaviour-parity test against it stays, comparing `state_store.read_battery_critical()` (now byos's own function) against `server.wake`'s still-separate copy, until a later plan switches `server/wake.py` itself onto `state_store`.

## Deviations from Plan

**1. [Rule 1 - Bug] Removed now-unused `timedelta` import after `seconds_until_quiet_hours_end` became a binding**
- **Found during:** Task 1's verification step (`ruff check stub-server`)
- **Issue:** Replacing the local `seconds_until_quiet_hours_end()` function definition with `seconds_until_quiet_hours_end = device_policy.seconds_until_quiet_hours_end` left `from datetime import datetime, timedelta, timezone` importing `timedelta` with no remaining use in the file, which `ruff` flagged as F401.
- **Fix:** Removed `timedelta` from the import line.
- **Files modified:** `stub-server/byos_server.py`
- **Verification:** `ruff check stub-server` reports "All checks passed!"; the full stub-server suite (63 tests) still passes.
- **Committed in:** `7427539` (Task 1's commit)

**2. [Rule 1 - Bug] Corrected `_atomic_write()`'s now-false "must never import server.*" docstring claim**
- **Found during:** Task 1, while replacing the constant/function definitions immediately above `_atomic_write()`
- **Issue:** `_atomic_write()`'s own docstring justified keeping a local copy of `server/atomic_io.py`'s logic with "byos must never import server.* (stub-server/VENDOR.md's vendor boundary)" - a statement the same commit's new `from server import device_policy, state_store` line directly contradicts.
- **Fix:** Reworded the sentence to state the real reason `_atomic_write()` stays local: it serves files (`byos_state.json`, `devices.json`, `img/*.bin`) the two new shared modules don't own, independent of the device-policy/state-store imports this file now has.
- **Files modified:** `stub-server/byos_server.py`
- **Verification:** `scripts/check_comment_history.py check` exits 0; manual re-read confirms the sentence no longer contradicts the file's own imports.
- **Committed in:** `7427539` (Task 1's commit)

---

**Total deviations:** 2 auto-fixed (2 Rule 1 - bug/stale-claim fixes)
**Impact on plan:** Both fixes are direct, unavoidable consequences of Task 1's own change (an unused import, and a docstring the new import made false); no scope creep beyond what Task 1 already required.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Known Stubs

None.

## Threat Flags

None new. `T-39-12` (sys.path bootstrap elevation), `T-39-13` (start-up import denial-of-service) and `T-39-14` (corrupted device_config.json under the unified fallback) are this plan's own threat-model register and are covered by the work above (the bootstrap inserts only `dirname(dirname(abspath(__file__)))`, never a cwd-relative path; the `--help`-from-another-cwd subprocess test plus `deploy/activate.sh`'s existing smoke-run cover start-up; the invalid-time fallback is the accepted, developer-approved T-39-14 outcome) rather than introducing new surface.

## Self-Check: PASSED

- FOUND: stub-server/byos_server.py
- FOUND: stub-server/test_poll_cycle.py
- FOUND: ARCHITECTURE.md
- FOUND: stub-server/VENDOR.md
- FOUND commit: 7427539
- FOUND commit: c04ed89

## Next Phase Readiness

byos now shares quiet-hours, battery-critical and wake/sleep policy with the poll cycle through one pair of stdlib-only modules; the only remaining hand-duplicated copies of this policy live in `server/poll_loop.py`, `server/device_config.py` and `server/wake.py` themselves, which this plan deliberately left untouched (server-side wiring is a later plan in this phase, 39-07..39-10). No blockers for those plans: `server/device_policy.py` and `server/state_store.py`'s public API is unchanged, and this plan's own tests (`test_quiet_hours_helpers_are_the_shared_device_policy_objects`, `test_display_off_sleep_s_constant_parity`, `test_battery_critical_constant_parity`) will need their `device_config`-attribute-equality assertions revisited once `server/device_config.py` and `server/poll_loop.py` are themselves switched onto `device_policy`/`state_store` — at that point those assertions become identity checks too, as the plan's own interface notes anticipate.

---
*Phase: 39-server-architecture-run-once-split-state-store-shared-module*
*Completed: 2026-09-27*

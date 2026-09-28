---
phase: 42-remote-firmware-update-over-the-air-ota-promoted-from-seed-0
plan: 10
subsystem: server
tags: [ota, firmware, notifications, poll-cycle, stdlib]

# Dependency graph
requires:
  - phase: 42-remote-firmware-update-over-the-air-ota-promoted-from-seed-0
    provides: "server/firmware_registry.py (plan 01) -- apply_reconcile(state_dir, now), the pure reconcile()/notification-tuple contract"
provides:
  - "server/notify.py: FIRMWARE_INSTALLED_BODY / FIRMWARE_FAILED_BODY EN/FR bodies"
  - "server/poll_cycle.py's run_once(): a _reconcile_firmware() step that folds every device-reported OTA outcome into the release registry on every cycle, including every hold branch, and fires exactly one push per installed/failed outcome"
affects: [companion-update-page, ci-deploy-import]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "_reconcile_firmware() follows the same optional-sender, group-then-topic-gate, log-exception-type-only shape _notify_battery_transition()/_notify_silence_transition() already established in poll_cycle.py -- a fourth notification hook built the same way rather than a new pattern"
    - "The reconcile step runs before decide_hold(), not inside the live path -- the one place in run_once() every branch (live, quiet-hours, display-off, battery-empty) passes through unconditionally"

key-files:
  created:
    - server/test_firmware_reconcile.py
  modified:
    - server/notify.py
    - server/test_notify.py
    - server/poll_cycle.py

key-decisions:
  - "The reconcile step landed in server/poll_cycle.py (Phase 39's cycle-body module), not server/poll_loop.py (now only the CLI argparse wrapper around run_once()) -- the plan's own files_modified list named poll_loop.py from before the Phase 39 split; this plan's own <read_first> instructed re-reading poll_loop.py on main first, which surfaced the split and pointed at poll_cycle.py's run_once() as the real step-list owner"
  - "'Notifications disabled' (Task 2's behaviour spec) has no dedicated OTA toggle field of its own in device_config.py's notifications sub-dict -- there is no such field to add per this plan's own files_modified list, so the gate is exactly the two checks _notify_battery_transition() already runs first: the notifications group present, and topic_url truthy. This matches D-08's own wording (\"reuses server/notify.py and the configured topic\") rather than inventing a fifth notifications key"
  - "now for apply_reconcile() is history_db.utc_now_iso(), read fresh at the reconcile call site rather than reusing ctx.now_iso -- ctx.now_iso isn't set yet at that point in run_once() (it's assigned separately inside detect_flight()'s and run_hold_cycle()'s own branches), and the reconcile step must run before either"

requirements-completed: []  # OTA-06/OTA-09 are shared across several plans in this phase (the device-side
                            # three-attempts refusal and battery-low-start gate for OTA-06, the byos offer
                            # withdrawal for OTA-06, and OTA-09's own EN/FR wording review); this plan closes
                            # only the server-side reconcile-and-notify half. REQUIREMENTS.md left Pending per
                            # this phase's established convention (see plans 01/07's precedent).

coverage:
  - id: D1
    description: "notify.py gains FIRMWARE_INSTALLED_BODY (\"Firmware %s installed\") and FIRMWARE_FAILED_BODY (\"Update failed, back on %s\") with French forms in _BODY_FR, keyed by the identical English string"
    requirement: "OTA-09"
    verification:
      - kind: unit
        ref: "server/test_notify.py::test_firmware_notification_bodies_are_the_expected_english_source_strings, test_firmware_installed_body_for_lang_fr, test_firmware_failed_body_for_lang_fr, test_firmware_body_for_lang_en_returns_english_unchanged"
        status: pass
    human_judgment: false
  - id: D2
    description: "Every poll cycle -- including the battery-hold, quiet-hours and display-off branches -- folds new device reports into the registry via firmware_registry.apply_reconcile(), before the hold decision"
    requirement: "OTA-06"
    verification:
      - kind: unit
        ref: "server/test_firmware_reconcile.py::test_installed_result_updates_registry_and_sends_one_notification, test_rollback_result_records_attempt_and_sends_no_notification, test_reconcile_runs_on_every_hold_branch (parametrized x2), test_reconcile_runs_on_battery_empty_hold_branch"
        status: pass
    human_judgment: false
  - id: D3
    description: "A third counted failure marks the schedule failed and withdraws the offer via the registry; a second cycle over the same already-reconciled events sends nothing more"
    requirement: "OTA-06"
    verification:
      - kind: unit
        ref: "server/test_firmware_reconcile.py::test_third_counted_failure_marks_failed_and_notifies_once"
        status: pass
    human_judgment: false
  - id: D4
    description: "Exactly one push fires per installed outcome and per failed-for-good outcome, in the operator's configured language, through notify.send_notification with the configured topic; nothing fires with notifications disabled or no topic configured"
    requirement: "OTA-09"
    verification:
      - kind: unit
        ref: "server/test_firmware_reconcile.py::test_installed_result_french_lang_produces_french_body, test_notifications_disabled_still_updates_registry_and_sends_nothing, test_no_topic_url_still_updates_registry_and_sends_nothing"
        status: pass
    human_judgment: false
  - id: D5
    description: "A raising reconcile call never breaks the poll cycle; it logs one line naming only the exception type, never the topic URL or exception text, and the cycle completes its normal work"
    requirement: "OTA-06"
    verification:
      - kind: unit
        ref: "server/test_firmware_reconcile.py::test_reconcile_raising_does_not_break_the_cycle"
        status: pass
    human_judgment: false

# Metrics
duration: ~35min
completed: 2026-09-28
status: complete
---

# Phase 42 Plan 10: OTA outcome loop -- server reconcile and notifications Summary

**Every poll cycle, including every hold branch, now folds device-reported OTA outcomes into the release registry via a new `_reconcile_firmware()` step in `server/poll_cycle.py`, and fires exactly one push notification per install/failure through two new EN/FR bodies in `server/notify.py`.**

## Performance

- **Duration:** ~35 min
- **Tasks:** 2 (Task 1: notification bodies; Task 2: the reconcile step and its tests)
- **Files modified:** 4 (1 new, 3 modified)

## Accomplishments

- `server/notify.py`: `FIRMWARE_INSTALLED_BODY`/`FIRMWARE_FAILED_BODY` English constants plus their French forms in `_BODY_FR`, following the existing key-by-English-string convention.
- `server/poll_cycle.py`'s `run_once()` now calls a new `_reconcile_firmware(state_dir, device_cfg, now, sender=None)` step immediately after `load_cycle_context()` and before `decide_hold()` -- the one point every branch (live, battery-empty, quiet-hours, display-off) passes through unconditionally. It calls `firmware_registry.apply_reconcile()`, then sends each returned `("installed"|"failed", version, back_on)` tuple through `notify.send_notification()` using the same group-present/topic-present gate `_notify_battery_transition()` already established, in the operator's configured language.
- A raising `apply_reconcile()` is caught, logged as `poll_loop: firmware reconcile failed: <ExceptionType>` (never the topic URL or exception text), and the cycle continues to completion unaffected.
- 10 new cycle-level tests in `server/test_firmware_reconcile.py`, each driving the real `run_once()` over a hold branch (display-off, quiet-hours, or battery-empty) so no live ADS-B/adsbdb network seam needs stubbing -- covering: installed (EN and FR bodies), third-counted-failure-marks-failed-and-notifies-once, a second cycle over the same events sending nothing more, rollback (records an attempt, no notification), notifications disabled, no topic configured, a raising reconcile, and the reconcile step running on all three hold-branch kinds.
- 4 new unit tests in `server/test_notify.py` pinning the two new bodies' exact English source strings and their French `body_for_lang()` output.

## Task Commits

Each task was executed as a RED/GREEN TDD pair, committed atomically:

1. **Task 1: Notification bodies EN/FR**
   - `a90e9532` (test) RED: failing tests for `FIRMWARE_INSTALLED_BODY`/`FIRMWARE_FAILED_BODY`
   - `b58d5df3` (feat) GREEN: the two constants and their French forms
2. **Task 2: Reconcile step in every poll cycle, with notifications**
   - `36af9410` (test) RED: failing cycle-level tests over `run_once()`
   - `5a28a27a` (feat) GREEN: `_reconcile_firmware()` wired into `run_once()`

**Plan metadata:** committed as part of the final docs commit (STATE.md/ROADMAP.md).

## Files Created/Modified

- `server/notify.py` - `FIRMWARE_INSTALLED_BODY`/`FIRMWARE_FAILED_BODY` and their `_BODY_FR` forms
- `server/test_notify.py` - 4 new tests for the firmware notification bodies
- `server/poll_cycle.py` - `_reconcile_firmware()` step, wired into `run_once()` before the hold decision; `firmware_registry` import; docstring updates
- `server/test_firmware_reconcile.py` - 10 new cycle-level tests (new file)

## Decisions Made

- See `key-decisions` in the frontmatter above -- the poll_cycle.py-not-poll_loop.py landing site (a Phase 39 split the plan's own `<read_first>` step surfaced), the no-new-toggle notifications gate, and the `history_db.utc_now_iso()` clock choice are the three decisions with real behavioural consequences.
- Kept `_reconcile_firmware()`'s shape (optional `sender=None`, try/except logging the exception type only) identical to `_notify_battery_transition()`/`_notify_silence_transition()` rather than inventing a different hook contract for the third notification kind this file now sends.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Comment-history violation: two D-15 citations in a new docstring/comment, and one D-08/D-15 citation in the new test file's module docstring**
- **Found during:** Task 2, running `scripts/check_comment_history.py check` as required before every commit touching source files
- **Issue:** The `run_once()` docstring addition and the inline comment at the `_reconcile_firmware()` call site both cited "(D-15)"; `server/test_firmware_reconcile.py`'s module docstring cited "(D-08, D-15)" -- forbidden per `CLAUDE.md` and this plan's own project rules
- **Fix:** Reworded all three to state the rationale in plain English with no decision-ID citation
- **Files modified:** `server/poll_cycle.py`, `server/test_firmware_reconcile.py`
- **Verification:** `scripts/check_comment_history.py check` exits 0 with no findings
- **Committed in:** `5a28a27a` (Task 2 GREEN commit)

**2. [Rule 1 - Bug] `_reconcile_firmware()`'s ruff-clean file was correct, but a battery-empty hold-branch test double-counted an unrelated notification**
- **Found during:** Task 2, first run of `test_reconcile_runs_on_battery_empty_hold_branch`
- **Issue:** Forcing the battery-empty hold branch via a low `battery_state.json` reading also triggers the pre-existing `_notify_battery_transition()` push (both share the monkeypatched sender), so the test initially counted 2 sends instead of 1
- **Fix:** Added a `battery_low_toggle` parameter to the test file's `_save_cfg()` helper and disabled it for this one test, isolating the firmware notification from the unrelated battery-low transition push
- **Files modified:** `server/test_firmware_reconcile.py`
- **Verification:** `server/test_firmware_reconcile.py` full run: 10/10 passing
- **Committed in:** `5a28a27a` (Task 2 GREEN commit)

---

**Total deviations:** 2 auto-fixed (1 comment-history compliance fix, 1 test isolation fix)
**Impact on plan:** Both fixes were required by the plan's own stated verification commands (`check_comment_history.py check`) and its own behaviour contract (one notification per outcome); no scope creep beyond what each task already specified.

## Issues Encountered

None beyond the two auto-fixed items above.

## User Setup Required

None - no external service configuration required. This plan is server-side, stdlib-only, and touches no deployment or secrets configuration.

## Next Phase Readiness

- The server-side half of OTA-06 (three attempts, then failed and withdrawn, every cycle) and OTA-09 (EN/FR push notifications through `server/notify.py`) is proven end to end: byos records device reports (plan 07), the poll loop reconciles them into the registry and notifies (this plan), and the companion's Update page reads the resulting view (plan 09).
- No blockers. `REQUIREMENTS.md` deliberately left untouched: OTA-06/OTA-09 are each shared across further plans in this phase (the device-side three-attempts refusal, the battery-low-start gate, and OTA-09's own wording review are elsewhere in this phase's scope), so this plan does not call `requirements mark-complete` for them -- matching this phase's own established convention (see plans 01/07's precedent).
- `server/poll_cycle.py::_reconcile_firmware()` is the one call site any later plan needing a fourth notification kind (or a change to the reconcile cadence) should extend, rather than adding a fifth ad hoc hook.

---

*Phase: 42-remote-firmware-update-over-the-air-ota-promoted-from-seed-0*
*Completed: 2026-09-28*

## Self-Check: PASSED

- FOUND: server/notify.py
- FOUND: server/test_notify.py
- FOUND: server/poll_cycle.py
- FOUND: server/test_firmware_reconcile.py
- FOUND: .planning/phases/42-remote-firmware-update-over-the-air-ota-promoted-from-seed-0/42-10-SUMMARY.md
- FOUND: a90e9532 (test: failing tests for firmware notification bodies)
- FOUND: b58d5df3 (feat: firmware installed/failed notification bodies)
- FOUND: 36af9410 (test: failing cycle-level tests for the reconcile step)
- FOUND: 5a28a27a (feat: reconcile OTA outcomes and notify every poll cycle)
- FOUND: 172f31da (docs: plan 10 SUMMARY)

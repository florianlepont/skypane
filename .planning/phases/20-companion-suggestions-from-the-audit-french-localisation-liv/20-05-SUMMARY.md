---
phase: 20-companion-suggestions-from-the-audit-french-localisation-liv
plan: 05
subsystem: infra
tags: [poll-loop, notifications, ntfy, wake-scheduling, sqlite, python]

# Dependency graph
requires:
  - phase: 20-companion-suggestions-from-the-audit-french-localisation-liv
    plan: 02
    provides: "server/notify.py's send_notification()/body_for_lang()/BATTERY_LOW_BODY etc., server/wake.py's device_staleness_thresholds()/effective_wake_interval_s()/MISSED_WAKES_WARN, and the notifications config group in server/device_config.py"
provides:
  - "server/poll_loop.py — _notify_battery_transition() and _notify_silence_transition(), wired into run_once() at both battery_low_active sites and the single post-_record_history() point, plus the shared notifications sub-dict in poll_state.json"
affects: [20-11-device-page-notifications-group]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "each transition hook wraps its entire body in `except Exception` and only ever logs `type(exc).__name__` (T-20-17/T-20-06), matching server/notify.py's own never-raising contract"
    - "the reported state (last_battery_sent/last_silent_sent) is written to poll_state.json whether or not the send succeeded, so a flapping endpoint cannot turn one transition into a push every cycle (T-20-22)"
    - "the frame-silent hook opens its own history.db connection at a single call site common to all three non-hold branches of run_once(), deliberately after every branch's own _record_history() call, so this cycle's own check-in can never be reported silent"

key-files:
  created: []
  modified: [server/poll_loop.py, server/test_poll_loop.py]

key-decisions:
  - "The single frame-silent call site needed its own explicit save_poll_state() call, since it runs after every branch's own (conditional) save — each battery-hook call site instead piggybacks on its branch's existing battery_changed-gated save, but the silence hook has no branch-local save to piggyback on."
  - "The battery-percentage estimate (BATTERY_FULL_MV/BATTERY_EMPTY_MV/battery_percent()) is duplicated, not imported, from companion/battery.py — poll_loop.py must never import anything from the web-app package (D-27), and the estimate is small enough that a private copy is cheaper than a third shared home."
  - "Rewrote every new docstring/comment that would otherwise have named companion/battery.py or companion/layout.py by path, using server/wake.py's own established 'the web-app package' phrasing instead — keeps this plan from adding new hits to the `grep -v '^#' | grep companion` self-check, which was already non-zero (9 pre-existing indented-comment mentions of the companion service, unrelated to this plan) before this plan touched the file. See Deviations."

requirements-completed: [CFG-17]

# Metrics
duration: 42min
completed: 2026-09-11
---

# Phase 20 Plan 05: Poll-loop notification hooks Summary

**Two never-raising transition hooks wired into server/poll_loop.py's run_once() — battery-low/back-to-normal at both existing battery_low_active sites, and frame-silent/frame-back on the shared Health-page staleness threshold — each sending exactly one ntfy push per genuine transition via server/notify.py, in the persisted notifications.lang, without the server ever importing anything under companion/**

## Performance

- **Duration:** 42 min
- **Started:** 2026-09-11T21:45:00Z (approx., immediately after 20-02)
- **Completed:** 2026-09-11T22:27:00Z
- **Tasks:** 2
- **Files modified:** 2

## Accomplishments
- `_notify_battery_transition()` wired into both `battery_low_active` sites (the hold branch and the main branch), gated on the existing `battery_changed` flag — a low transition sends exactly one push with the millivolt reading and a percentage estimate, a recovery sends exactly one push with no arguments, and neither repeats on an unchanged cycle
- `_notify_silence_transition()` wired once per `run_once()`, at the single point after every branch's own `_record_history()` call where the DB connection, `device_cfg` and `poll_state` are all in scope — reusing `wake.device_staleness_thresholds(wake.effective_wake_interval_s(device_cfg))`'s WARN value verbatim, with no phase-local re-tuning
- A shared `poll_state["notifications"]` sub-dict (`last_battery_sent`/`last_silent_sent`) makes both hooks once-per-transition rather than once-per-cycle, persisted even when the underlying POST failed
- 15 new checks in `server/test_poll_loop.py` (8 battery, 7 silence) via an injected `_FakeSender` that never performs a real POST; one check drives the real `run_once()` call site with a raising `send_notification()` to prove the exception containment holds through the actual wiring, not just the helper in isolation

## Task Commits

Each task was committed atomically:

1. **Task 1: the battery-low transition push, sent once per transition** - `cfe9f1e` (feat)
2. **Task 2: the frame-silent transition push, on the shared staleness threshold** - `1465419` (feat)

**Plan metadata:** (this commit, docs: complete plan)

## Files Created/Modified
- `server/poll_loop.py` - `_notifications_group()`, `_battery_percent_estimate()`, `_notify_battery_transition()`, `_humanize_age_s()`, `_parse_iso_epoch()`, `_notify_silence_transition()`; wired into both `battery_low_active` sites and one new post-`_record_history()` call site in `run_once()`; imports `server.notify`/`server.wake`
- `server/test_poll_loop.py` - `_FakeSender`, `_iso()`, `_seed_device_health()` test helpers; 15 new checks (8 for Task 1, 7 for Task 2); `EXPECTED_CHECK_COUNT` 81 → 89 → 96

## Decisions Made
- See `key-decisions` above (frontmatter) for the three load-bearing choices: the silence hook's own unconditional `save_poll_state()`, the duplicated (not imported) battery-percentage estimate, and the "web-app package" phrasing rewrite.
- The end-to-end raising-sender check (Task 1, check 74) monkeypatches `poll_loop.notify.send_notification` and drives a real `run_once()` cycle rather than calling the helper directly, since that is the only way to prove containment holds through the actual call site the plan wires — every other check calls the private helper directly with an injected `sender`, which is faster and does not need a real `history.db`/`device_config.json` on disk.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] The new frame-silence call site broke an existing history.db-failure containment check**
- **Found during:** Task 2, first full-suite run after wiring `_notify_silence_transition()`'s call site
- **Issue:** `server/test_poll_loop.py`'s pre-existing check 25 ("a history.db failure (open_db raising) is caught and logged without failing the cycle or leaving panel.bin unwritten") monkeypatches `poll_loop.history_db.open_db` to raise for every call, not just the ones inside `_record_history()`. The new `with history_db.open_db(state_dir) as conn:` block this plan added at the single silence-hook call site had no `try/except` of its own, so the injected `OperationalError` propagated straight out of `run_once()` and failed that pre-existing check (80/81).
- **Fix:** Wrapped the new call site in `try: ... except (sqlite3.Error, OSError) as exc: print(...)`, mirroring `_record_history()`'s own T-06-10-05 containment shape exactly (same exception types, same log-and-continue behaviour).
- **Files modified:** `server/poll_loop.py`
- **Verification:** `server/test_poll_loop.py` → 81/81 immediately after the fix (then 96/96 once both tasks' new checks were added)
- **Committed in:** `1465419` (Task 2 commit)

**2. [Rule 1 - Bug] Reworded three new docstring/comment lines that named companion/ modules by path**
- **Found during:** Task 1/Task 2, self-verification of the plan's own `grep -v '^#' server/poll_loop.py | grep -c "companion"` acceptance check
- **Issue:** The first drafts of `_battery_percent_estimate()`'s and `_humanize_age_s()`'s docstrings, and the module-level comment above the duplicated battery constants, named `companion/battery.py` and `companion/layout.py` literally by path (to explain why their estimates are duplicated rather than imported). That pushed the acceptance check's count from 9 (pre-existing, unrelated mentions of "the companion service" inside `run_once()`'s own long-standing comments) to 12.
- **Fix:** Reworded all three new mentions to say "the web app's own ... module"/"the web-app package", mirroring the exact phrasing `server/wake.py`'s own module docstring already uses for the identical constraint (D-27) — meaning intact, no literal substring added. Net new "companion" occurrences after the reword: 0.
- **Files modified:** `server/poll_loop.py`
- **Verification:** `grep -v '^#' server/poll_loop.py | grep -c "companion"` → 9, identical to `git show 4d87e21580ebbe715aecf1560f725623a2e58d31:server/poll_loop.py | grep -v '^#' | grep -c companion` (the wave-1 merge base, before this plan touched the file)
- **Committed in:** `cfe9f1e` (Task 1 commit)

---

**Total deviations:** 2 auto-fixed (2 bugs, both direct consequences of this plan's own additions)
**Impact on plan:** Both fixes were necessary to keep the pre-existing suite green and to hold this plan's own acceptance checks to their literal wording. No scope creep — neither touched any file outside `server/poll_loop.py`.

## Issues Encountered
- The `grep -v '^#' server/poll_loop.py | grep -c "companion"` acceptance check (both tasks) cannot be driven to a literal `0` without rewriting substantial pre-existing prose unrelated to this plan: `server/poll_loop.py` already carried 9 indented-comment mentions of "the companion service"/"companion/app.py" before this plan started (verified against the wave-1 merge-base commit), a known class of false positive 20-02-SUMMARY.md's own Issues Encountered section already documents for `server/notify.py`/`server/wake.py`. This plan's own net contribution to that count is 0 (see Deviation 2 above) — the true functional guarantee (`server/poll_loop.py` never `import`s anything under `companion/`) holds and is unchanged; only the substring-matching self-check's absolute number is pre-existing debt outside this plan's `files_modified` scope.

## User Setup Required
None - no external service configuration required. (The end-to-end human check — a real ntfy topic, unplugging the frame for 3+ wake intervals — is deferred to end-of-phase per this plan's own `<verification>` block; it is not a gap in this plan's scope.)

## Next Phase Readiness
- `server/poll_loop.py` now sends both notification classes D-27 describes; 20-11 (the Device-page Notifications group UI) can wire its "Send a test" button against `server/notify.py`'s existing `TEST_NOTIFICATION_TITLE`/`TEST_NOTIFICATION_BODY` constants without any further poll-loop change.
- No blockers for downstream plans. `server/test_poll_loop.py`'s `EXPECTED_CHECK_COUNT` is now 96; any sibling plan retargeting this file must read the current value from disk, not assume 81.

---
*Phase: 20-companion-suggestions-from-the-audit-french-localisation-liv*
*Completed: 2026-09-11*

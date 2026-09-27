---
phase: 39-server-architecture-run-once-split-state-store-shared-module
plan: 07
subsystem: companion
tags: [state-store, device-policy, battery, import-isolation, stdlib-only]

requires:
  - phase: 39-server-architecture-run-once-split-state-store-shared-module
    provides: "39-02: server/device_policy.py and server/state_store.py, unwired, byte-identical to the poll_loop/wake/device_config code they replace"
provides:
  - "companion/pages/health_page.py and companion/pages/airlines_page.py read poll_state.json through server.state_store, never server.poll_loop"
  - "companion/battery.py re-exports server.device_policy's discharge curve, endpoints and both percentage functions by identity, instead of maintaining a second copy; its companion-only display threshold and life-estimate code are unchanged"
  - "companion/app.py's poll_state freshness path and --state-dir default read from server.state_store; its /poll-now imports of poll_loop (run_once, PollBusy, poll_cycle_lock, now_s) are untouched"
  - "companion's four poll-state test-seeding helpers (test_companion_app_helpers.py, test_status_pages_helpers.py, test_view_pages_helpers.py, test_browser_ux_helpers.py) write through state_store"
  - "companion/test_companion_app_03.py's battery isolation test is an allowlist (server.device_policy only, no other server.* module, no companion.pages module, no PIL/requests/urllib3), diffed sys.modules before/after the import"
affects: [39-08, 39-09, 39-10, 40]

tech-stack:
  added: []
  patterns:
    - "Import-isolation subprocess test diffs sys.modules before/after the import under test (not the raw post-import set), reused verbatim from 39-02's own device_policy isolation test, since child_env()'s sitecustomize.py unconditionally imports requests before any application code runs — a raw post-import set would false-positive on requests/urllib3 that were never pulled in by the module under test."
    - "Companion switch-over commits stay import-line-only: one commit per named site group (pages, battery, app.py + helpers), each verified against the full suite before the next begins, so a parallel companion-architecture session (Phase 40) can merge without conflict."

key-files:
  created: []
  modified:
    - companion/pages/health_page.py
    - companion/pages/airlines_page.py
    - companion/battery.py
    - companion/app.py
    - companion/test_status_pages_05b.py
    - companion/test_companion_app_05.py
    - companion/test_companion_app_02.py
    - companion/test_companion_app_03.py
    - companion/test_companion_app_helpers.py
    - companion/test_status_pages_helpers.py
    - companion/test_view_pages_helpers.py
    - companion/test_browser_ux_helpers.py
    - companion/test_status_pages_03.py

key-decisions:
  - "D-6 (developer decision, carried from 39-CONTEXT.md): companion/battery.py's former 'imports nothing from server' isolation test is retargeted to an allowlist test (server.device_policy only). Implemented here as test_battery_module_imports_only_the_shared_device_policy_from_server in companion/test_companion_app_03.py."
  - "The parity test in test_companion_app_02.py no longer compares companion.battery's values against server.poll_loop's private _NOTIFY_* copy by equality; it asserts identity (`is`) between companion.battery's re-exported names and server.device_policy's own objects, which is the stronger property re-exporting the same objects actually guarantees."
  - "Comments in health_page.py, airlines_page.py, test_companion_app_02.py and test_status_pages_03.py that named server/poll_loop.py as the poll-state owner or as the battery module's other home were reworded to name server/state_store.py or server/device_policy.py (or, where the comment was about something poll_loop still legitimately owns — POLL_INTERVAL_S, the device hysteresis threshold, run_once/PollBusy/now_s — reworded to describe the fact without the module name, or left untouched)."

requirements-completed: [ARC-02, ARC-05]

duration: ~10min
completed: 2026-09-27
---

# Phase 39 Plan 07: Companion switches to state_store and device_policy Summary

**The companion's page reads of poll_state.json, its battery-percentage curve, and app.py's poll_state path/default now go through server.state_store and server.device_policy instead of server.poll_loop, in three isolated commits — the companion's only remaining server.poll_loop dependency is the /poll-now entry points (run_once, PollBusy, poll_cycle_lock, now_s), which switch in a later plan once the poll-cycle library module exists.**

## Performance

- **Duration:** ~10 min
- **Tasks:** 3/3 completed
- **Files modified:** 13 (0 created)

## Accomplishments

- `companion/pages/health_page.py` and `companion/pages/airlines_page.py` import `server.state_store` instead of `server.poll_loop` and call `state_store.load_poll_state()` at every site (the unresolved-prefix registry read in both pages); every comment in both files that named the old module was reworded to name the new one, or (where the comment was about something unrelated to `load_poll_state`, like `POLL_INTERVAL_S`) reworded to drop the module name while keeping the fact.
- `companion/battery.py` no longer defines its own `BATTERY_DISCHARGE_CURVE`, `BATTERY_FULL_MV`, `BATTERY_EMPTY_MV`, `battery_fraction()` or `battery_percent()` — it re-exports `server.device_policy`'s own objects (`from server.device_policy import (...)  # noqa: F401`), following the same shim pattern as `companion/wake.py`. `_curve_mv_at_percent()`, `LOW_BATTERY_DISPLAY_PERCENT`/`_MV` and the whole battery-life-estimate section are unchanged, now built on top of the shared curve.
- `companion/app.py` reads the poll-state path (`_freshness_file_stamp`'s input) and the `--state-dir` CLI default from `server.state_store` (`poll_state_path()`, `DEFAULT_STATE_DIR`); `poll_loop.run_once`, `poll_loop.PollBusy`, `poll_loop.poll_cycle_lock()` and `poll_loop.now_s()` are untouched, since those switch to the future poll-cycle library module in a later plan.
- All four companion test-seeding helpers (`test_companion_app_helpers.py`, `test_status_pages_helpers.py`, `test_view_pages_helpers.py`, `test_browser_ux_helpers.py`) write `poll_state.json` through `state_store.save_poll_state()`. The module-level `poll_loop` import is dropped from `test_companion_app_helpers.py` and `test_status_pages_helpers.py`, and `test_view_pages_helpers.py`'s local, function-scoped `poll_loop` import is replaced with a local `state_store` import — none of those three files had any other use of `poll_loop`. `test_browser_ux_helpers.py` keeps its module-level `poll_loop` import because it also calls `poll_loop._save_to_gallery()`.
- The battery isolation test in `test_companion_app_03.py` is now `test_battery_module_imports_only_the_shared_device_policy_from_server` — a subprocess test that diffs `sys.modules` before/after `import companion.battery` and asserts the diff contains no `server.*` module other than `server`/`server.device_policy`, no `companion.pages*` module, and none of `PIL`/`requests`/`urllib3` (or their submodules). The parity test in `test_companion_app_02.py` is now `test_battery_estimate_is_the_shared_device_policy`, asserting identity (`is`), not just equality, between `companion.battery`'s re-exported names and `server.device_policy`'s own curve/endpoints/functions, plus the same 2800-4400 mV sweep and hostile-input set comparing outputs.
- Full suite green after each of the three commits: 2974 passed, 139 skipped (pre-existing Playwright-browser-missing skips, unrelated to this plan), 94% coverage. `ruff check companion` and `scripts/check_comment_history.py check` both clean.

## Task Commits

1. **Task 1: health and airlines pages read poll_state through state_store** - `cc1837f` (feat)
2. **Task 2: companion/battery.py re-exports the shared device policy** - `9bfc02e` (feat)
3. **Task 3: app.py state paths and test seeding helpers use state_store** - `0499fd7` (feat)

## Files Created/Modified

- `companion/pages/health_page.py` - imports `server.state_store`; `unresolved_rows()` reads through `state_store.load_poll_state()`; comments reworded
- `companion/pages/airlines_page.py` - imports `server.state_store`; `_gap_rows_for_grid()` and the manual-resolution lookup read through `state_store.load_poll_state()`; comments and docstring reworded
- `companion/battery.py` - re-exports `BATTERY_DISCHARGE_CURVE`/`BATTERY_FULL_MV`/`BATTERY_EMPTY_MV`/`battery_fraction`/`battery_percent` from `server.device_policy`; module docstring and the low-battery-threshold comment rewritten to describe the shared policy
- `companion/app.py` - imports `server.state_store`; poll_state freshness-stamp path and `--state-dir` default now read from it
- `companion/test_status_pages_05b.py` - `test_airlines_page_imports_no_history_db_or_sqlite_but_does_import_poll_loop` renamed and retargeted to assert `state_store` binding
- `companion/test_companion_app_05.py` - poll-trigger cooldown test's `_seed_gap()` helper switched to `state_store.load_poll_state()`; unused `poll_loop` import dropped
- `companion/test_companion_app_02.py` - `test_battery_discharge_curve_is_well_formed`'s threshold assertion and the parity test (renamed `test_battery_estimate_is_the_shared_device_policy`) switched to `server.device_policy`; drawing-contract section comment reworded
- `companion/test_companion_app_03.py` - battery isolation test renamed and rewritten as the `server.device_policy`-only allowlist, diffing sys.modules before/after
- `companion/test_companion_app_helpers.py`, `companion/test_status_pages_helpers.py`, `companion/test_view_pages_helpers.py`, `companion/test_browser_ux_helpers.py` - `save_poll_state()` seeding calls switched to `state_store`; unused `poll_loop` imports dropped where nothing else in the file used them
- `companion/test_status_pages_03.py` - one stale comment naming `poll_loop.load_poll_state` corrected to `state_store.load_poll_state` (the page it describes, health_page.py, switched in Task 1's commit)

## Decisions Made

- D-6's companion.battery isolation-test retarget (developer-approved, `39-CONTEXT.md`): the old "imports nothing from server" test became an allowlist of exactly `server.device_policy`, matching the phase's decision that the shared module is stdlib-only and companion may depend on it alone.
- The parity test between companion and the shared curve is now an identity check, not an equality check — re-exporting the same objects makes identity the true invariant, and identity subsumes the old equality property (two identical objects are always equal).
- Comments naming the old module were reworded wherever they were about the poll-state read this plan moved (per the plan's own convention: "comments that name the old module" are in scope for a companion-edit commit), but left alone wherever they described something that genuinely still lives in `server/poll_loop.py` today (POLL_INTERVAL_S, the device hysteresis threshold, run_once/PollBusy/poll_cycle_lock/now_s) — those switch in the later plan that gives `run_once` its library-module home.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Stale comment in test_status_pages_03.py left naming poll_loop after health_page.py's switch**
- **Found during:** Task 3's acceptance-criteria verification (the plan's own repo-wide grep for the four `poll_loop.*` call shapes)
- **Issue:** `companion/test_status_pages_03.py` had a comment describing the registry read as `poll_loop.load_poll_state()`, which became inaccurate once Task 1's commit switched `health_page.py`'s actual read onto `state_store.load_poll_state()`. This file was not in Task 3's declared file list, but the plan's own acceptance criteria (`grep -n "poll_loop\.\(_poll_state_path\|DEFAULT_STATE_DIR\|save_poll_state\|load_poll_state\)" -r companion` returns nothing) is repo-wide, not scoped to the task's file list.
- **Fix:** Reworded the comment to name `state_store.load_poll_state()`, matching the code it actually describes.
- **Files modified:** `companion/test_status_pages_03.py`.
- **Verification:** The repo-wide grep returns nothing; the full suite (including this file's own tests) stayed green.
- **Committed in:** `0499fd7` (part of Task 3's commit, since it was caught while running Task 3's own acceptance check)

---

**Total deviations:** 1 auto-fixed (1 bug — stale comment)
**Impact on plan:** Doc-only fix inside a test comment, one file outside the task's declared list but still `companion/` and still a small import-shape correction consistent with the coordination rule. No behavioural or test-coverage change.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Known Stubs

None. Every switched call site is a full, tested read/write through the shared module — nothing left as a placeholder.

## Threat Flags

None. `T-39-15` (state_store.load_poll_state is the same fail-open reader, already pinned by `server/test_state_store.py`) and `T-39-16` (battery percentage shown vs. notified now share one function) are the threat model's own register for this plan and introduce no new surface — both are existing, already-tested properties this plan connects the companion to, not new code paths.

## Self-Check: PASSED

- FOUND: companion/pages/health_page.py
- FOUND: companion/pages/airlines_page.py
- FOUND: companion/battery.py
- FOUND: companion/app.py
- FOUND: companion/test_companion_app_03.py
- FOUND commit: cc1837f
- FOUND commit: 9bfc02e
- FOUND commit: 0499fd7

## Next Phase Readiness

The companion's remaining `server.poll_loop` uses are exactly the `/poll-now` entry points named in the plan (`run_once`, `PollBusy`, `poll_cycle_lock`, `now_s`) plus the gallery writer (`_save_to_gallery`) and `write_panel_atomic`, none of which this plan's scope (ARC-02/ARC-05) touches. Ready for the later plan that extracts the poll cycle into its own library module and switches those remaining imports. No blockers. Coordination note honored: each companion edit landed as its own small commit, `server/` and `stub-server/` were untouched by this plan, keeping a parallel Phase 40 merge trivial.

---
*Phase: 39-server-architecture-run-once-split-state-store-shared-module*
*Completed: 2026-09-27*

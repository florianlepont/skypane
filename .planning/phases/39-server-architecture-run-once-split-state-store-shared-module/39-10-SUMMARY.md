---
phase: 39-server-architecture-run-once-split-state-store-shared-module
plan: 10
subsystem: server
tags: [poll-loop, poll-cycle, module-split, companion, import-boundary]

requires:
  - phase: 39-server-architecture-run-once-split-state-store-shared-module
    provides: "39-09: server/poll_loop.py, wake.py and device_config.py already bind the shared device_policy/state_store modules, so the moved poll cycle carries no battery/quiet-hours copy of its own"
provides:
  - "server/poll_cycle.py: the poll-cycle library module (run_once, PollBusy, poll_cycle_lock, now_s, pacing helpers, notify hooks, history recording, panel write and gallery), moved verbatim out of the entrypoint"
  - "server/poll_loop.py: the systemd-timer entrypoint only (build_parser, main, the repo-root bootstrap), carrying nothing else"
  - "companion/app.py reaches the poll cycle only through server.poll_cycle (run_once/PollBusy/poll_cycle_lock/now_s) - server.poll_loop is no longer imported anywhere in companion/"
  - "server/test_import_boundaries.py: a behavioural, subprocess-based guard that importing companion.app or server.poll_cycle never loads server.poll_loop, that poll_loop.run_once/PollBusy are the identical poll_cycle objects, that poll_loop carries none of the removed/transitional names, and that `poll_loop.py --help` still works from another cwd"
affects: [39-11, 39-13]

tech-stack:
  added: []
  patterns:
    - "Library/entrypoint split with a time-boxed transitional re-export: poll_loop.py kept four read-only bindings (now_s, poll_cycle_lock, _save_to_gallery, write_panel_atomic) it didn't itself need, purely so the companion's own commit (Task 2) could land as a real, isolated switch rather than a combined one - removed in Task 3 once nothing read through them any more."
    - "Import-boundary tests as subprocess checks, never source-text greps: server/test_import_boundaries.py proves 'X never loads Y' by importing X fresh in a child interpreter and inspecting that child's own sys.modules, the same pattern companion/test_companion_app_03.py's isolation tests already use."

key-files:
  created:
    - server/poll_cycle.py
    - server/test_import_boundaries.py
  modified:
    - server/poll_loop.py
    - server/test_poll_loop.py
    - server/test_poll_state_writes.py
    - server/test_poll_lock.py
    - server/test_poll_efficiency.py
    - server/test_provider_rate.py
    - server/test_pipeline_e2e.py
    - server/test_device_policy.py
    - test-support/efficiency_probe.py
    - companion/app.py
    - companion/test_browser_ux_helpers.py
    - companion/test_view_pages_helpers.py

key-decisions:
  - "The stdout log prefix stays the literal string \"poll_loop: \" inside server/poll_cycle.py, unchanged by the module rename - journald greps, the PollBusy message and every test that parses a cycle's log line all key off that exact prefix, per the plan's own convention. Only the *module* callers reach through (poll_loop -> poll_cycle) moved; the printed text did not."
  - "server/test_state_writers.py, test-support/test_efficiency_probe.py and scripts/measure_efficiency.py needed no changes for this plan either (39-09 already established the same finding for a different file set): verified by grep that none of them reference a moved poll_loop name directly - they only call through efficiency_probe's own public API, which was itself retargeted."
  - "Out-of-scope stale `poll_loop.`-naming prose (docstrings, not code) in six companion files outside Task 2's 3-file list (companion/wake.py, test_request_connections.py, test_freshness_token.py x2, test_companion_app_05.py, test_companion_app_helpers.py, test_browser_ux_03.py) was left as-is and logged to this phase's deferred-items.md, rather than expanded into Task 2's isolated commit - Phase 39's own CONTEXT.md assigns companion/ to a parallel Phase 40 session, and none of these six lines touch an actual import or call site."

requirements-completed: []

duration: ~65min
completed: 2026-09-27
---

# Phase 39 Plan 10: Poll cycle moved to server/poll_cycle.py; companion switched; import boundary guarded Summary

**The poll cycle (detect/infer/enrich/render/publish/record) now lives in server/poll_cycle.py as a pure library move; server/poll_loop.py is only the systemd entrypoint; companion/app.py's `/poll-now` imports server.poll_cycle directly; and a new subprocess-based test guards that neither the companion nor the library ever load the entrypoint (ARC-02, ROADMAP criterion 2).**

## Performance

- **Duration:** ~65 min
- **Tasks:** 3/3 completed (Task 3 ran RED -> GREEN as its own two commits, per its `tdd="true"` frontmatter)
- **Files modified:** 12 (2 created: server/poll_cycle.py, server/test_import_boundaries.py; 10 modified)

## Accomplishments

- **Task 1 (`5c51bc2`, feat):** `git mv server/poll_loop.py server/poll_cycle.py` so history follows the cycle code, then removed `build_parser`/`main`/the `__main__` block/the shebang/the sys.path bootstrap from poll_cycle.py and rewrote its module docstring to describe the library, not the entrypoint. Wrote a new, small `server/poll_loop.py`: the original entrypoint docstring, the repo-root bootstrap, `from server.poll_cycle import PollBusy, run_once`, `from server.state_store import DEFAULT_STATE_DIR`, four transitional read-only bindings (`_save_to_gallery`, `now_s`, `poll_cycle_lock`, `write_panel_atomic`) kept only for Task 2's own isolated commit, and `build_parser`/`main` copied verbatim. Retargeted every monkeypatch/attribute-read seam the interfaces map named across `server/test_poll_loop.py` (3710 lines; ~168 `run_once` references alone), `server/test_poll_state_writes.py`, `server/test_poll_lock.py`, `server/test_poll_efficiency.py`, `server/test_provider_rate.py`, `server/test_pipeline_e2e.py`, `server/test_device_policy.py` and `test-support/efficiency_probe.py` from `poll_loop` to `poll_cycle`, while keeping `import server.poll_loop as poll_loop` and its two `poll_loop.main(...)` calls plus the one `setattr(poll_loop, "run_once", _raise)` in the main()-failure test exactly where the interfaces map said they belonged (these read through poll_loop's own module globals, which `main()` itself resolves bare names against - not a dead re-export). `server/test_state_writers.py`, `test-support/test_efficiency_probe.py` and `scripts/measure_efficiency.py` needed no edits - verified by grep, not assumed.
- **Task 2 (`d790c6b`, feat):** switched `companion/app.py`'s poll-cycle import and every call site (`run_once`, `PollBusy`, `poll_cycle_lock`, `now_s` x2) plus five comment/docstring mentions from `server.poll_loop` to `server.poll_cycle`; `companion/test_browser_ux_helpers.py`'s gallery-seeding helper now calls `poll_cycle._save_to_gallery`; `companion/test_view_pages_helpers.py`'s `write_panel_file()` docstring now names `poll_cycle.write_panel_atomic()`. The commit touches exactly these three files, as the plan's own acceptance criteria require - companion/ stays owned by a parallel Phase 40 session for everything else.
- **Task 3 (TDD, `7849d74` RED / `0687e84` GREEN):** added `server/test_import_boundaries.py` (5 tests: two subprocess checks that importing `companion.app`/`server.poll_cycle` never loads `server.poll_loop`, an identity check that `poll_loop.run_once`/`PollBusy` are the poll_cycle objects, a check that `poll_loop` carries none of the four transitional bindings or the long-since-moved `load_poll_state`, and a `--help` subprocess check run from a temporary cwd). RED confirmed for the right reason (`test_poll_loop_carries_none_of_the_transitional_or_removed_names` failed against the still-present bindings; the other four tests already passed - nothing else in the tree reached through `poll_loop` for these seams). Removed the four transitional bindings from `poll_loop.py` for GREEN.

## Task Commits

1. **Task 1: move the cycle into server/poll_cycle.py; poll_loop becomes the entrypoint; retarget server and test-support tests** - `5c51bc2` (feat)
2. **Task 2 (companion-only commit): companion /poll-now and test helpers import server.poll_cycle** - `d790c6b` (feat)
3. **Task 3: drop the transitional bindings; server/test_import_boundaries.py guards the boundary** - `7849d74` (test, RED) / `0687e84` (feat, GREEN)

## Files Created/Modified

- `server/poll_cycle.py` - the poll-cycle library (created via `git mv` from poll_loop.py, entrypoint code removed)
- `server/poll_loop.py` - now only the systemd-timer entrypoint (build_parser, main)
- `server/test_import_boundaries.py` - new subprocess-based import-boundary guard (5 tests)
- `server/test_poll_loop.py`, `test_poll_state_writes.py`, `test_poll_lock.py`, `test_poll_efficiency.py`, `test_provider_rate.py`, `test_pipeline_e2e.py`, `test_device_policy.py` - retargeted to `server.poll_cycle`
- `test-support/efficiency_probe.py` - retargeted to `server.poll_cycle`
- `companion/app.py`, `companion/test_browser_ux_helpers.py`, `companion/test_view_pages_helpers.py` - switched to `server.poll_cycle`

## Decisions Made

See `key-decisions` in the frontmatter above: the log prefix stays `"poll_loop: "` unchanged; three more files needed no edits (verified, not assumed); six out-of-scope docstring mentions elsewhere in `companion/` were deferred rather than folded into Task 2's isolated commit.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] A blanket `poll_loop` -> `poll_cycle` word-swap in server/test_poll_loop.py initially corrupted the log-prefix string literal**
- **Found during:** Task 1, immediately after the scripted retarget, running `server/test_poll_loop.py`
- **Issue:** The mechanical word-boundary substitution (`\bpoll_loop\b` -> `poll_cycle`) correctly retargeted every monkeypatch/attribute-read, but it also matched the nine `"poll_loop: "` string-literal prefixes tests use to parse a cycle's own stdout log line (`ln.startswith("poll_loop: ")`), turning them into `"poll_cycle: "` - which the code never prints, since the plan's own convention keeps that prefix literal. 13 tests failed with `IndexError`/`pytest.fail` from an empty match list.
- **Fix:** Reverted every `poll_cycle: ` string-literal occurrence in `server/test_poll_loop.py` back to `poll_loop: ` (a plain text replace, not a word-boundary regex, since the log-prefix string itself must never change).
- **Files modified:** server/test_poll_loop.py
- **Verification:** Full `server/test_poll_loop.py` suite green (120 passed, 1 pre-existing skip) after the revert.
- **Committed in:** `5c51bc2` (part of the Task 1 commit - caught before committing, not a separate fix-up commit)

---

**Total deviations:** 1 auto-fixed (1 bug, caught and fixed before the task's own commit)
**Impact on plan:** No scope creep - the fix was a self-correction of the executor's own scripted substitution, confirmed by rerunning the affected test file before proceeding.

## Issues Encountered

None beyond the auto-fixed issue above. The 3710-line `server/test_poll_loop.py` retarget (the plan's largest single file) was done via a scripted word-boundary substitution with three explicit, verified exceptions (the `import server.poll_loop as poll_loop` line, the two `poll_loop.main(...)` calls, and the one `setattr(poll_loop, "run_once", _raise)`), each checked against the interfaces map's own enumeration before and after.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

The poll cycle is now a library module with a guarded import boundary, ready for Plan 39-11 to split `_run_once_locked()` (338 lines, `server/poll_cycle.py:709`, the last ARC-01 size-gate offender in `server/`) into the named steps the ledger calls for (`load_cycle_context`/`decide_hold`/`advance_display_queue`/`render_and_publish`/`persist`/`record`, names to be refined by that plan). No blockers.

---
*Phase: 39-server-architecture-run-once-split-state-store-shared-module*
*Completed: 2026-09-27*

## Self-Check: PASSED

- FOUND: server/poll_cycle.py
- FOUND: server/poll_loop.py
- FOUND: server/test_import_boundaries.py
- FOUND: .planning/phases/39-server-architecture-run-once-split-state-store-shared-module/39-10-SUMMARY.md
- FOUND: .planning/phases/39-server-architecture-run-once-split-state-store-shared-module/deferred-items.md
- FOUND commit: 5c51bc2 (Task 1)
- FOUND commit: d790c6b (Task 2)
- FOUND commit: 7849d74 (Task 3 RED)
- FOUND commit: 0687e84 (Task 3 GREEN)

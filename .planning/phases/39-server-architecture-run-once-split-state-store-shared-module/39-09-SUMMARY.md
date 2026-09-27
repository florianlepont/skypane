---
phase: 39-server-architecture-run-once-split-state-store-shared-module
plan: 09
subsystem: server
tags: [device-policy, state-store, poll-loop, wake, device-config, module-consolidation]

requires:
  - phase: 39-server-architecture-run-once-split-state-store-shared-module
    provides: "39-02: server/device_policy.py and server/state_store.py (the shared, typed, stdlib-only modules this plan wires poll_loop/wake/device_config onto)"
  - phase: 39-server-architecture-run-once-split-state-store-shared-module
    provides: "39-06: byos already on device_policy/state_store (stub-server drift tests no longer read server source)"
  - phase: 39-server-architecture-run-once-split-state-store-shared-module
    provides: "39-07: companion already on device_policy/state_store (companion tests no longer read the poll_loop copies)"
provides:
  - "server/poll_loop.py, server/wake.py and server/device_config.py define no battery constant, hysteresis function, discharge curve, quiet-hours helper, sleep/wake constant or poll_state.json reader/writer of their own; each binds the shared server.device_policy / server.state_store objects"
  - "device_config and wake keep exposing the same names their callers (companion/wake.py, companion device_config readers) already use, as read-only re-exports of the shared objects"
  - "poll_state.json has exactly one owner (server.state_store); server tests read state/policy names from state_store/device_policy, never from poll_loop"
affects: [39-11, 39-13]

tech-stack:
  added: []
  patterns:
    - "Read-only re-export binding, not a copy: device_config._HHMM_RE = device_policy.HHMM_RE, wake.read_battery_critical = state_store.read_battery_critical. Nothing in the tree rebinds these names, so the shared object stays the single source of truth even through the old module's public name."
    - "poll_loop.DEFAULT_STATE_DIR stays a binding to state_store.DEFAULT_STATE_DIR so main()'s --state-dir default and every caller that reads poll_loop.DEFAULT_STATE_DIR keep working unchanged."

key-files:
  modified:
    - server/poll_loop.py
    - server/wake.py
    - server/device_config.py
    - server/test_device_policy.py
    - server/test_state_store.py
    - server/test_poll_lock.py
    - server/test_poll_loop.py
    - server/test_poll_state_writes.py
    - test-support/efficiency_probe.py
    - test-support/test_efficiency_probe.py

key-decisions:
  - "Tasks 1 and 2 committed together, exactly as the plan's own acceptance criteria anticipated: Task 1 alone (deleting the poll_loop/wake/device_config copies) leaves server/test_poll_loop.py red until Task 2's test retargeting lands, so the plan explicitly allowed a combined commit."
  - "server/test_poll_efficiency.py, server/test_provider_rate.py, server/test_pipeline_e2e.py and server/test_state_writers.py needed no changes: a repo-wide grep for every moved poll_loop name confirmed none of them reference the removed copies, so Task 2's file list for those four files was a no-op — verified, not assumed."

requirements-completed: []

duration: ~50min
completed: 2026-09-27
---

# Phase 39 Plan 09: Server switches onto the shared device_policy and state_store modules Summary

**`server/poll_loop.py`, `server/wake.py` and `server/device_config.py` no longer define their own battery hysteresis, discharge curve, quiet-hours arithmetic or `poll_state.json` I/O — each now binds the shared `server.device_policy`/`server.state_store` objects, completing "one owner of state" and "one copy of device policy" on the server side (ARC-02, ARC-05).**

## Performance

- **Duration:** ~50 min
- **Tasks:** 2/2 completed (combined into one commit, per the plan's own contingency)
- **Files modified:** 10

## Accomplishments

- `poll_loop.py`: deleted `_poll_state_path`, `load_poll_state`, `_HOLD_KINDS`, `_hold_state`, `load_battery_state`, `_serialize_poll_state`, `save_poll_state`, `_persist_poll_state`, `BATTERY_LOW_THRESHOLD_MV`, `BATTERY_LOW_CLEAR_MV`, `BATTERY_CRITICAL_MV`, `BATTERY_CRITICAL_RECOVER_MV`, `apply_battery_hysteresis`, `apply_battery_critical_hysteresis`, `_NOTIFY_BATTERY_DISCHARGE_CURVE`, `_NOTIFY_BATTERY_FULL_MV`/`_EMPTY_MV`, `_battery_percent_estimate` — every internal call site rewritten to the module-attribute form (`state_store.load_poll_state(state_dir)`, `device_policy.battery_percent(battery_mv)`, etc.); `DEFAULT_STATE_DIR` rebound to `state_store.DEFAULT_STATE_DIR`. `write_panel_atomic`, gallery helpers, notify hooks, pacing helpers and `_record_history` stayed in place (out of this plan's scope).
- `device_config.py`: deleted the quiet-hours/wake constants and helpers; added a re-export block from `device_policy` under the same `device_config` names (`_HHMM_RE`, `QUIET_HOURS_TZ`, `WAKE_INTERVAL_MIN_S`/`MAX_S`, `DISPLAY_OFF_SLEEP_S`, `BATTERY_CRITICAL_SLEEP_S`, `DEFAULT_QUIET_HOURS_START`/`END`, `normalise_quiet_hours_time`, `seconds_until_quiet_hours_end`, `quiet_hours_status`); `load_device_config`/`save_device_config` keep calling the re-exported names unchanged.
- `wake.py`: `BATTERY_CRITICAL_STATE_KEY` re-exported from `device_policy`; `read_battery_critical` rebound to `state_store.read_battery_critical`; the old local reader deleted. `companion/wake.py`'s re-export of both names from `server.wake` needed no change.
- `test_device_policy.py`: added `test_server_modules_use_the_shared_policy_objects`, an identity test asserting `device_config.seconds_until_quiet_hours_end`/`quiet_hours_status`/`normalise_quiet_hours_time`/`_HHMM_RE`/`QUIET_HOURS_TZ` and `wake.read_battery_critical` are the shared objects (`is`, not equality), plus `not hasattr(poll_loop, name)` for every name this plan removed from `poll_loop`.
- `test_state_store.py`, `test_poll_lock.py`, `test_poll_loop.py`, `test_poll_state_writes.py`, `test-support/efficiency_probe.py`, `test-support/test_efficiency_probe.py`: retargeted from `poll_loop.*` to `state_store.*`/`device_policy.*`; assertions, fixtures and write-count expectations kept their exact meaning — only the module prefix changed.

## Verification

- Full suite: 2977 passed, 139 skipped (all pre-existing Playwright-browser-missing / root-euid environment skips, none caused by this plan), 94% coverage (>= 93% floor).
- `server/.venv/bin/ruff check .` and `scripts/check_comment_history.py check` both clean.
- `scripts/check_function_size.py check --max 80 server stub-server`: the only offender is `server/poll_loop.py`'s `_run_once_locked` (338 lines) — expected and out of this plan's scope; Plan 39-11 splits it.
- The plan's own acceptance-criteria greps (no removed poll_loop battery/state defs, no removed device_config quiet-hours defs, no local `read_battery_critical` in `wake.py`/`byos_server.py`, no remaining `poll_loop.<moved-name>` reference anywhere in `server/`, `stub-server/`, `test-support/` or `scripts/`) all return empty.
- `git diff --name-only` for this plan's commit lists no file under `companion/` or `stub-server/`.

## Issues Encountered

- The session that started this plan was interrupted mid-task by a rate limit after finishing both tasks' edits but before running final verification or committing. The next session re-ran the full suite and every acceptance-criteria check from a clean read before committing — nothing was taken on faith.

## Next Steps

Server-side ARC-02/ARC-05 work is done. `server/poll_loop.py`'s `_run_once_locked` (338 lines, the one remaining size-gate offender) is Plan 39-11's job, after Plan 39-10 moves it into `server/poll_cycle.py`.

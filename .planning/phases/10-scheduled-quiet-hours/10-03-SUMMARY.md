---
phase: 10-scheduled-quiet-hours
plan: 03
subsystem: stub-server
tags: [python, byos, quiet-hours, vendoring, zoneinfo, dst]

# Dependency graph
requires:
  - "server/device_config.py's seconds_until_quiet_hours_end() / _HHMM_RE / QUIET_HOURS_TZ (plan 10-01)"
provides:
  - "GET /device/v1/display's sleep_s extended past a currently-active quiet-hours window (D-01, the whole battery win)"
  - "read_quiet_hours()/quiet_hours_sleep_s() in stub-server/byos_server.py, fail-open against device_config.json"
  - "an automated drift guard in stub-server/test_poll_cycle.py pinning the vendored window arithmetic byte-for-byte equal to server/device_config.py's"
affects: [10-04]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Vendor boundary duplication: stub-server/byos_server.py never imports server.*; a byte-for-byte copy of shared arithmetic is kept in sync by an automated text-diff drift guard instead of a shared import"
    - "read_quiet_hours() follows read_led_enabled()'s exact fail-open shape: any config failure mode returns the safe default (None), never raises"
    - "quiet_hours_sleep_s()'s max(base_sleep_s, remaining) never returns a value shorter than the caller's own base sleep"

key-files:
  created: []
  modified:
    - stub-server/byos_server.py
    - stub-server/VENDOR.md
    - stub-server/test_poll_cycle.py

key-decisions:
  - "seconds_until_quiet_hours_end() was copied verbatim from the real, already-committed plan 10-01 body (which fixes the UTC-subtraction bug the earlier research/patterns documents carried), not re-derived from 10-RESEARCH.md/10-PATTERNS.md - verified numerically by the DST-anchor acceptance check (23400/30600)"
  - "The drift guard extracts function/line text directly from server/device_config.py and stub-server/byos_server.py, never by importing server.device_config, so the guard itself cannot breach the vendor boundary it protects"
  - "quiet_hours_sleep_s() runs strictly after the existing bearer_ok() gate (unchanged code path), adding no new unauthenticated surface"

requirements-completed: []

coverage:
  - id: D-01
    description: "A poll landing inside an enabled quiet-hours window returns a sleep_s that spans past the window's end, and sleep_s is never shorter than the base --sleep value"
    verification:
      - kind: unit
        ref: "stub-server/test_poll_cycle.py#quiet_hours_sleep_s() returns 28000 inside the window and the unchanged base 300 past its end"
        status: pass
      - kind: unit
        ref: "stub-server/test_poll_cycle.py#quiet_hours_sleep_s(86400, ...) never returns less than the base 86400 (the max() rule)"
        status: pass
      - kind: integration
        ref: "stub-server/test_poll_cycle.py#a currently-active quiet-hours window over real HTTP yields sleep_s in (300, 7200]"
        status: pass
    human_judgment: false
  - id: T-10-03-01
    description: "A missing, unreadable, malformed, non-dict, disabled, or badly-shaped device_config.json degrades sleep_s to the unchanged base value and never raises"
    verification:
      - kind: unit
        ref: "stub-server/test_poll_cycle.py#read_quiet_hours() returns None for 7 failure modes (missing/truncated/non-dict/disabled/hostile-enabled/bad-start/bad-end)"
        status: pass
      - kind: integration
        ref: "stub-server/test_poll_cycle.py#a hostile device_config.json still yields sleep_s exactly equal to the base --sleep"
        status: pass
    human_judgment: false
  - id: T-10-03-03
    description: "The two copies of seconds_until_quiet_hours_end()/_HHMM_RE across the vendor boundary are pinned byte-for-byte equal"
    verification:
      - kind: unit
        ref: "stub-server/test_poll_cycle.py#drift guard reads both files as text and fails on any divergence; negative-control run confirmed (see below)"
        status: pass
    human_judgment: false

duration: 20min
completed: 2026-09-03
status: complete
---

# Phase 10 Plan 03: Vendored Quiet-Hours sleep_s Extension (byos_server.py) Summary

**`GET /device/v1/display`'s `sleep_s` now extends past a currently-active quiet-hours window via a byte-for-byte vendored duplicate of `server/device_config.py`'s DST-safe window arithmetic, guarded against drift by an automated text-diff check.**

## Performance

- **Duration:** ~20 min
- **Started:** 2026-09-03T21:20Z (approx.)
- **Completed:** 2026-09-03T21:40Z
- **Tasks:** 2
- **Files modified:** 3

## Accomplishments
- `stub-server/byos_server.py` gained `QUIET_HOURS_TZ`, `_HHMM_RE`, a byte-for-byte vendored copy of `seconds_until_quiet_hours_end()`, `read_quiet_hours(state_dir)` (fail-open, never-raises, mirrors `read_led_enabled()`'s shape), and `quiet_hours_sleep_s(base_sleep_s, state_dir, now=None)` (`max(base, remaining)` - never shorter than the base sleep)
- `GET /device/v1/display`'s `"sleep_s"` field now comes from `quiet_hours_sleep_s(self.args.sleep, self.args.state_dir)` instead of the raw `self.args.sleep` literal; no deployment or env change needed (`SKYPANE_SLEEP_S` remains the base, `deploy/` untouched)
- `stub-server/VENDOR.md` gained local-modification entry 5 documenting the change and the duplication obligation; the re-pinning checklist now lists all five modifications
- `stub-server/test_poll_cycle.py` grew from 23 to 29 checks: a text-based drift guard (no import of `server.device_config`), three unit checks against the module loaded via `importlib.util` (fail-open across 7 failure modes, sleep extension at the verified DST anchors, never-shorter-than-base), and two integration checks over real HTTP (an active window extending `sleep_s`, and a hostile config falling back to the exact base value)

## Task Commits

Each task was committed atomically:

1. **Task 1: Add the quiet-hours-aware sleep_s computation to byos_server.py** - `ee3c46b` (feat)
2. **Task 2: Document the vendor modification and cover it in test_poll_cycle.py** - `3ea72ef` (docs)

## Files Created/Modified
- `stub-server/byos_server.py` - Added stdlib imports (`re`, `datetime`/`timedelta`/`timezone`, `zoneinfo.ZoneInfo`), `QUIET_HOURS_TZ`/`_HHMM_RE` constants, the vendored `seconds_until_quiet_hours_end()`, `read_quiet_hours()`, `quiet_hours_sleep_s()`; replaced the `/display` handler's `"sleep_s": self.args.sleep` with the new call; extended the module docstring's local-modifications paragraph
- `stub-server/VENDOR.md` - New "Local modification 5" entry; re-pinning checklist updated to five items
- `stub-server/test_poll_cycle.py` - New `load_byos_module()`/`_extract_def_block()`/`_extract_line()` helpers; 6 new `check(...)` calls (drift guard, fail-open, sleep extension, never-shorter-than-base, active-window integration, hostile-config integration); `EXPECTED_CHECK_COUNT` 23 -> 29; docstring's stdlib enumeration extended

## Decisions Made
- Copied `seconds_until_quiet_hours_end()` verbatim from the real, already-landed `server/device_config.py` body (plan 10-01), not from 10-RESEARCH.md/10-PATTERNS.md's earlier reference variant which had the UTC-subtraction defect - verified via the DST-anchor acceptance check (`23400`/`30600` seconds at the two named epochs)
- The drift guard extracts both `seconds_until_quiet_hours_end()`'s body and the `_HHMM_RE = re.compile(...)` line as plain text from both files (never importing `server.device_config`), so the guard itself cannot breach the vendor boundary it exists to protect
- Integration checks reuse the existing `_device_config_fixture_path()` helper from the `led_enabled` checks (same shared file, different keys), keeping the fixture-write/HTTP-request/`finally`-remove pattern identical across both features

## Deviations from Plan

None - plan executed exactly as written. Both tasks' acceptance criteria commands were run verbatim and all passed; `git diff --name-only` after each commit matched the plan's declared file list exactly.

## Drift-Guard Negative Control

Per the plan's acceptance criteria, the drift guard was deliberately exercised as a negative control before finalizing Task 2:
1. Mutated `stub-server/byos_server.py`'s vendored copy: changed `return max(0, int(...))` to `return max(1, int(...))` inside `seconds_until_quiet_hours_end()`.
2. Ran `server/.venv/bin/python3 stub-server/test_poll_cycle.py` - exited **1**, with the drift-guard check failing and printing a diff-style message naming both `server/device_config.py` and `stub-server/byos_server.py`; the run reported `28/29 checks pass`.
3. Reverted via `git checkout -- stub-server/byos_server.py`, confirmed `git status --short` showed no residual change to that file, then re-ran the full harness clean at `29/29`.

This confirms the guard actually detects divergence rather than trivially passing.

## Issues Encountered
None.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Plan 10-04 (`server/poll_loop.py`'s `quiet_hours_active` gate and `"quiet_hours"` render state) can proceed independently - it reads `quiet_hours_status()` from `server/device_config.py` directly (never vendored), a separate function this plan deliberately did not touch.
- `scripts/run-all-tests.sh` run at the end of this plan: all harnesses pass, including `poll-cycle: 29/29 checks pass`. The sole non-zero note is the pre-existing, already-accepted macOS Pillow/FreeType `panel.bin` digest mismatch (confirmed present before Phase 10 started, documented in plan 10-01's SUMMARY as Linux/CI-authoritative and non-Linux-informational) - unrelated to this plan's changes.
- `server/requirements.txt` and `deploy/` unchanged - `re`, `datetime`, and `zoneinfo` are all Python stdlib; `git diff --quiet deploy/` was itself an acceptance criterion and passed.

## Self-Check: PASSED

All modified files exist on disk with the expected content; both task commits (`ee3c46b`, `3ea72ef`) verified present in `git log`.

- FOUND: stub-server/byos_server.py
- FOUND: stub-server/VENDOR.md
- FOUND: stub-server/test_poll_cycle.py
- FOUND: .planning/phases/10-scheduled-quiet-hours/10-03-SUMMARY.md
- FOUND: ee3c46b
- FOUND: 3ea72ef

---
*Phase: 10-scheduled-quiet-hours*
*Completed: 2026-09-03*

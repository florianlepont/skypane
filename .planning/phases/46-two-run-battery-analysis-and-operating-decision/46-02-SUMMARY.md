---
phase: 46-two-run-battery-analysis-and-operating-decision
plan: 02
subsystem: device-protocol-tests
tags: [wake-interval, sleep_s, precedence, pytest, POL-03]
requires: []
provides:
  - "stub-server/test_wake_interval_delivery.py: chained Device-settings save -> real GET /device/v1/display sleep_s, precedence matrix over HTTP, server.wake parity"
  - "server/test_pipeline_e2e.py: recovery check-in asserts the exact unparked sleep_s"
affects: [46-04]
tech-stack:
  added: []
  patterns: ["byos_server.py subprocess on a loopback port, readiness by the child's own serving line with relaunch on a lost port"]
key-files:
  created:
    - stub-server/test_wake_interval_delivery.py
  modified:
    - server/test_pipeline_e2e.py
key-decisions:
  - "Server started with --sleep 30 so a fallback to the default can never pass as a saved value"
  - "Quiet hours checked at unit level with an injected clock (the HTTP handler uses the real clock)"
requirements-completed: [POL-03]
completed: 2026-10-12
---

# Phase 46 Plan 02: wake interval delivery tests Summary

A value saved through `config_page.handle_post` is proven to be the exact `sleep_s` of the next healthy check-in for 60, 300, 600, 900, 1800 and 3600 s; the battery-critical park (3600) and display-off (300) pins win over the saved interval through the real HTTP handler; recovery returns the saved value exactly; and `server.wake.effective_wake_interval_s` agrees with the HTTP reply for every in-range case.

## Tasks and commits

| Task | Commit |
|------|--------|
| 1+2 `stub-server/test_wake_interval_delivery.py` (save-to-HTTP, quiet hours, precedence matrix, wake.py parity) | 06360b07 |
| 2 e2e recovery assertion now `sleep_s == 300` (no interval is saved in that state dir) | 68edb7d0 |

Tasks 1 and 2 share one commit for the new file: it was written in one pass and not split afterwards.

## Verification

- New file: 59 passed; run 6 times serially (`-n0`), once with `-n4` and once with default options (coverage on): all green, not flaky.
- `stub-server/test_wake_interval_delivery.py server/test_pipeline_e2e.py stub-server/test_poll_cycle.py server/test_config_history.py`: 166 passed.
- `ruff check stub-server server` and `scripts/check_comment_history.py check`: clean.
- mypy not run: `server/wake.py` is unchanged.
- `git diff` shows no change to `stub-server/byos_server.py`, `server/wake.py` or `companion/`.

## Deviations from Plan

None - plan executed as written. The tests passed on first run, so no divergence was exposed and no production code was touched. The only structural difference is the shared commit noted above.

## Flagged for the owner

No divergence found between `server.wake.effective_wake_interval_s` and the frame-facing chain for any in-range case. Known by-design difference, not fixed: `wake.py` does not clamp a hand-edited out-of-range `wake_interval_s` (for example 5000), while the frame chain falls back to `--sleep`. The companion form cannot save such a value, so this affects only hand-edited files and the companion's countdown display.

## Not verified

The on-device confirmation that the real frame obeys the value belongs to Phase 47. Quiet hours are not exercised over HTTP (real clock), only at unit level with an injected clock.

## Known Stubs

None.

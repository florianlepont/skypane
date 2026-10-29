---
phase: 48-fleet-data-model-roles-and-live-frame-migration
plan: 06
subsystem: testing
tags: [freeze-list, migration-replay, byos, fleet-db, field-validation]
requires: ["48-03", "48-04", "48-05", "48-07"]
provides:
  - committed freeze list of the fields the v1.1 field validation measures
  - tests comparing the freeze list with running code
  - before/after-migration replay and migration re-run proof
affects: [production deploys while the field validation is open]
tech-stack:
  added: []
  patterns: [freeze list as data compared against a running byos subprocess]
key-files:
  created:
    - stub-server/measured_fields_freeze.json
    - stub-server/test_phase47_freeze.py
  modified:
    - companion/test_status_pages_03.py
decisions:
  - "Quiet-hours sleep scenario is frozen as a minimum (never below the saved interval) because the exact value depends on the wall clock"
metrics:
  tasks: 2
  completed: 2026-10-29
requirements: [DATA-02, DATA-05]
---

# Phase 48 Plan 06: Freeze list and migration replay Summary

A committed freeze list names the wake cadence, telemetry, poll-state and image-hash fields the field validation measures. 21 tests compare it with a real byos subprocess, the policy constants and a real poll cycle. A replay shows a poll gives an identical response before and after fleet migration.

## What was built

- `stub-server/measured_fields_freeze.json`: sections for display response keys and values, telemetry request headers, battery_state keys, poll_state keys, wake constants and six sleep scenarios. Each carries a `measured_by` note. Values were recorded from running code.
- `stub-server/test_phase47_freeze.py`:
  - `diff_against_freeze` helper, with a meta test showing it flags a removed key, an added key and a changed value. Failure messages name the measurement and say the list changes only with the owner's agreement.
  - Served display keys and values, with `image_hash` equal to `sha256:` plus the hash of the served image.
  - Each header is probed alone, and the stores and log lines it reaches are compared with the list. An unlisted header has no effect.
  - battery_state keys, the poll_state key set after a detected flight, and the wake constants (policy module and byos aliases).
  - Six sleep scenarios over HTTP.
  - Replay with process A, then migration, then a new process B on the same token. The full normalised response and the served image bytes are equal. This also holds with a saved interval of 900 s and with the battery-parked state.
  - B's stdout has no `setup:` line. Legacy identity files are byte-identical.
  - fleet.db holds the seeded MAC, secret hash, token and `state_path` ".".
  - Legacy `load_registry`, `secret_matches` and `load_state` still accept the migrated directory.
  - After a second and third migration, devices.json, byos_state.json and the fleet.db main file keep their sha256 and mtime_ns, and the poll response is unchanged.
- Mutation check: changing a frozen `WAKE_INTERVAL_MAX_S` to 3601 made the suite fail with a message naming the section. It was reverted and not committed.

## Deviations from Plan

**1. [Rule 1 - Bug] Stale health-inputs key test left by the previous plan**
- **Found during:** Task 2 full-suite gate
- **Issue:** `companion/test_status_pages_03.py::test_read_health_inputs_keeps_stats_separate` expected nine keys. The fleet fallback anomaly plan added `fleet_status`. Its "no stat key" check also matched `fleet_status`.
- **Fix:** The expected set now has ten keys. The guard checks for a `stats` key.
- **Commit:** 51139aa (see Commits)

The quiet-hours scenario uses `expect_min_sleep_s` rather than an exact value, because the remaining time depends on the clock.

## Gate results (run for real)

| Gate | Result |
|------|--------|
| `./scripts/run-all-tests.sh` | first run: 1 failed (the stale test above), 4000 passed. After the fix: 4001 passed, 539 skipped, 0 failed, coverage 95.38% against the 93.0% floor |
| `server/.venv/bin/python3 -m mypy` | Success, no issues in 15 source files |
| `server/.venv/bin/ruff check` | All checks passed |
| `python3 scripts/check_function_size.py check --max 80 server stub-server` | 551 functions scanned, none over 80 |
| `python3 scripts/check_comment_history.py check` | exit 0 |

Skipped tests: most of the 539 skips are Chromium browser tests (`companion/test_browser_*`). Playwright's headless shell is missing in this sandbox (`/opt/pw-browsers/chromium_headless_shell-1248` does not exist). Those browser tests did not run here. One test needs a non-root euid, and one needs an openssl that can backdate a certificate. The CI browser tests still need a green run on a machine with Chromium.

## Outstanding

- The real-state replay is outstanding. `SKYPANE_LIVE_STATE_COPY` was not used, so the replay ran on a synthetic production-shaped state. Real VPS state files are not in the repository. An owner-exported sanitised copy must be replayed before the migration is deployed.
- True previous-release execution against real state remains a post-deploy owner check, deferred until the field validation allows a deploy.

## Known Stubs

None.

## Threat Flags

None.

## Commits

- 41f773a: test(48-06): freeze list for field-validation fields and migration replay
- 51139aa: test(48-06): allow fleet_status in the health inputs key set

## Self-Check: PASSED

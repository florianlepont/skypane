---
phase: 52-fleet-poll-cycle-zones-and-request-budget
plan: 06
subsystem: poll-budget
tags: [simulation, request-budget, mypy, compliance]
requires: ["52-01", "52-02", "52-03", "52-04", "52-05"]
provides:
  - "server/test_fleet_budget_simulation.py: 100-device fake-clock proofs"
  - "server/test_request_budget_processes.py: real-process budget proof"
affects: [52-07]
key-files:
  created:
    - server/test_fleet_budget_simulation.py
    - server/test_request_budget_processes.py
  modified:
    - server/zone_fetch.py
    - server/test_zone_fetch.py
    - server/plane/shared_route_cache.py
    - pyproject.toml
    - COMPLIANCE.md
    - ARCHITECTURE.md
requirements-completed: [FLT-03, FLT-04]
completed: 2026-10-30
---

# Phase 52 Plan 06: Budget proofs and gates Summary

A 100-device fake-clock simulation drives `run_fleet` and proves 12 requests per cycle for six zones, at most one request in any 1 s window, capacity ordering with aging, and failure isolation; three real processes prove the persisted budget; the new typed modules are in the mypy list and the budget is documented.

## Commits
- 34226b8: simulation tests and the `fetch_zone` fix (Task 1)
- 498aa4b: process test, mypy list, COMPLIANCE.md, ARCHITECTURE.md

## What was built
- Simulation (13 tests, about 3 s): real migrated fleet.db with 100 devices, one clock for ledger, deadline and providers, recording runner and fetcher. Covers 20 cycles x 6 uneven zones (exactly 2 requests per zone per cycle, gaps >= 1.1 s, window maximum 1, each runner given its own zone's ZoneFetch object); 30 zones with the real 25 s deadline (12 fetched, live zone first, oldest-served next, every zone served within 3 cycles); 10 zones with a 5 s deadline (3 per cycle); failure of one zone (HTTPError), global pause behaviour, slow provider, slow zones hitting the deadline, unexpected provider error (zone failed, provider paused for 60 s), raising fetcher, raising runner (99 others run), held-only zone (zero requests), inactive devices (never run; live and fresh devices run).
- Process test: three real subprocesses x 6 acquires at 0.15 s spacing, merged timestamps respect the spacing; a pause written by one process makes another's `acquire` return False.
- mypy list and strict overrides: `request_budget`, `fleet_zones`, `zone_fetch`, `plane/shared_route_cache` (23 files). `fleet_cycle.py` is not annotated end to end and stays out.
- COMPLIANCE.md: new "Fleet-wide ADS-B request budget" section plus the adsbdb TTL review line (additions only). ARCHITECTURE.md: the poll description now describes the fleet cycle; the poll-now sentences are untouched.

## Verification
- `pytest server stub-server/test_phase47_freeze.py -n auto`: 1652 passed, 3 skipped (root ignores permission bits)
- ruff, mypy (23 files), function-size gate (724 functions), comment-history guard: clean
- `./scripts/run-all-tests.sh`: 6076 passed, 566 skipped (no Chromium in this sandbox), coverage 95.77% (floor 93, unchanged), 2 failures described below
- Mutation sanity: setting the ledger default spacing to 0 locally made 4 simulation tests fail (window, capacity, small-deadline, unreached-zone); reverted, not committed.

## Deviations from Plan

**1. [Rule 1 - Bug] `fetch_zone` did not pause a provider after an unexpected exception**
- Found during: Task 1 (unexpected provider error scenario)
- Issue: `_query_one` caught only request/value/OS errors; any other exception propagated after the slot was spent with no provider pause, so a persistent fault was retried every cycle.
- Fix: catch `Exception`, log, and `report_failure`, so the zone degrades to a failed ZoneFetch and the provider is paused for 60 s. Test cases added to `test_zone_fetch.py`.
- Files: server/zone_fetch.py, server/test_zone_fetch.py

**2. [Rule 3 - Blocking] mypy fix in `shared_route_cache._fresh`**
- Adding the module to the strict list reported a `no-any-return`; wrapped the comparison in `bool(...)`. No behaviour change.

**3. Test adaptations to the real design (no code change)**
- Provider pauses are global, so a failing zone pauses both providers for every later zone in that cycle. Isolation tests therefore put the failing zone last (by ledger aging) to show the others healthy, and a separate test shows that a first-zone failure still runs every device (with failed ZoneFetch objects) and makes no request for 60 s.
- The 12th zone of a capacity-exceeding cycle ends its second request at about 25.3 s, past the start deadline, so its non-live devices are deferred and the zone is not marked served. Its 2 requests are spent for nothing that cycle; it moves to the front of the never-served group next cycle, so aging still completes in 3 cycles. This follows the 52-05 rule that no device starts after the deadline; flagged for review rather than changed.

## Deferred Issues
- `companion/test_device_poll.py::test_poll_now_writes_only_that_devices_directory` and `companion/test_device_isolation.py::test_poll_isolation_end_to_end` fail: they assert the exact file set of the state root and now see `request_ledger.json` and `request_ledger.lock` written by `run_once` (since plan 52-04). Both tests belong to the poll-now feature that plan 52-07 removes (listed in its files), so they were not edited here.

## Known Stubs
None.

## Self-Check: PASSED
